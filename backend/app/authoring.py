from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, model_validator

from app import store
from app.access import DB, Lecturer
from app.courses import Name, owned_course
from app.store import one, rows

router = APIRouter(prefix="/api/lecturer")
Content = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class Question(BaseModel):
    stem: Content
    options: list[Content] = Field(min_length=2, max_length=20)
    correct: int = Field(ge=0)
    explanation: str = Field(default="", max_length=4000)
    topics: list[Name] = Field(min_length=1, max_length=30)
    objectives: list[Name] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def valid_key(self):
        if self.correct >= len(self.options):
            raise ValueError("Select one existing correct option")
        return self


class Draft(BaseModel):
    title: Name
    points_per_correct: Literal[1] = 1
    instructions: str = Field(default="", max_length=10000)
    rules: str = Field(default="", max_length=10000)
    reference_versions: list[int] = Field(default_factory=list, max_length=200)
    pre_release: bool = False
    allow_reference_export: bool = False
    calculator: bool = False
    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None
    duration: int | None = Field(default=None, gt=0, le=10080)
    students: list[int] = Field(default_factory=list, max_length=5000)
    questions: list[Question] = Field(default_factory=list, max_length=300)


class Update(BaseModel):
    edit_number: int
    draft: Draft


class Publication(BaseModel):
    edit_number: int


def owned(db, uid, eid):
    exam = one(
        db,
        """SELECT e.* FROM exam e JOIN course c ON c.id=e.course_id
        WHERE e.id=:e AND c.owner_id=:u FOR UPDATE OF e""",
        e=eid,
        u=uid,
    )
    if not exam:
        raise HTTPException(404, "Exam unavailable")
    return exam


def editable(db, exam, number):
    if number != exam["edit_number"]:
        raise HTTPException(409, "The exam changed. Reload before editing.")
    if exam["published_number"]:
        version = one(
            db,
            """SELECT opens_at FROM exam_version
            WHERE exam_id=:e AND number=:n""",
            e=exam["id"],
            n=exam["published_number"],
        )
        if store.now() >= version["opens_at"]:
            raise HTTPException(409, "The published exam has opened")


def eligible(db, cid, draft):
    if draft.reference_versions:
        found = one(
            db,
            """SELECT count(*) AS n FROM reference_version v
            JOIN reference_document d ON v.document_id=d.id
            WHERE d.course_id=:c AND v.id=ANY(:ids)""",
            c=cid,
            ids=draft.reference_versions,
        )
        if found["n"] != len(draft.reference_versions):
            raise HTTPException(
                422, "Choose distinct reference versions from this course"
            )
    selected = set(draft.students)
    roster = {
        r["student_id"]
        for r in rows(db, "SELECT student_id FROM enrollment WHERE course_id=:c", c=cid)
    }
    if selected - roster or len(selected) != len(draft.students):
        raise HTTPException(422, "Choose distinct enrolled students")


@router.get("/courses/{cid}/exams")
def listing(cid: int, db: DB, uid: Lecturer):
    owned_course(db, uid, cid)
    return list(
        rows(
            db,
            """SELECT id,draft->>'title' AS title,published_number
        FROM exam WHERE course_id=:c ORDER BY id DESC""",
            c=cid,
        )
    )


@router.post("/courses/{cid}/exams")
def create(cid: int, data: Draft, db: DB, uid: Lecturer):
    owned_course(db, uid, cid)
    eligible(db, cid, data)
    labels(db, cid, data)
    return one(
        db,
        """INSERT INTO exam(course_id,draft) VALUES (:c,cast(:d as jsonb))
               RETURNING *""",
        c=cid,
        d=data.model_dump_json(),
    )


def labels(db, cid, draft):
    values = {
        (kind, name)
        for q in draft.questions
        for kind, names in [("topic", q.topics), ("objective", q.objectives)]
        for name in names
    }
    for kind, name in sorted(values):
        rows(
            db,
            """INSERT INTO classification(course_id,kind,name) VALUES (:c,:k,:n)
             ON CONFLICT DO NOTHING RETURNING 1""",
            c=cid,
            k=kind,
            n=name,
        )


@router.get("/exams/{eid}")
def read(eid: int, db: DB, uid: Lecturer):
    exam = owned(db, uid, eid)
    version = one(
        db,
        "SELECT opens_at,snapshot FROM exam_version WHERE exam_id=:e AND number=:n",
        e=eid,
        n=exam["published_number"],
    )
    return {
        **exam,
        "published": version["snapshot"] if version else None,
        "frozen": bool(version and store.now() >= version["opens_at"]),
    }


@router.put("/exams/{eid}")
def save(eid: int, data: Update, db: DB, uid: Lecturer):
    exam = owned(db, uid, eid)
    eligible(db, exam["course_id"], data.draft)
    labels(db, exam["course_id"], data.draft)
    editable(db, exam, data.edit_number)
    return one(
        db,
        """UPDATE exam SET draft=cast(:d as jsonb),edit_number=edit_number+1
               WHERE id=:e RETURNING *""",
        d=data.draft.model_dump_json(),
        e=eid,
    )


def validate_publication(draft: Draft, time: datetime):
    if not (
        draft.questions
        and draft.students
        and draft.instructions.strip()
        and draft.rules.strip()
        and draft.duration
    ):
        raise HTTPException(
            422, "Add questions, assignments, instructions, rules and duration"
        )
    if not (
        draft.opens_at and draft.closes_at and time < draft.opens_at < draft.closes_at
    ):
        raise HTTPException(422, "Opening must be in the future and precede closing")


@router.post("/exams/{eid}/publish")
def publish(eid: int, data: Publication, db: DB, uid: Lecturer):
    exam = owned(db, uid, eid)
    draft = Draft.model_validate(exam["draft"])
    eligible(db, exam["course_id"], draft)
    editable(db, exam, data.edit_number)
    validate_publication(draft, store.now())
    return publish_snapshot(db, eid, exam, draft)


def publish_snapshot(db, eid, exam, draft):
    number = (exam["published_number"] or 0) + 1
    rows(
        db,
        """INSERT INTO exam_version VALUES (:e,:n,:o,:c,cast(:d as jsonb))
         RETURNING 1""",
        e=eid,
        n=number,
        o=draft.opens_at,
        c=draft.closes_at,
        d=draft.model_dump_json(),
    )
    rows(
        db,
        """INSERT INTO exam_assignment SELECT :e,:n,unnest(cast(:s as integer[]))
         RETURNING 1""",
        e=eid,
        n=number,
        s=draft.students,
    )
    rows(
        db,
        """INSERT INTO exam_reference(exam_id,revision,version_id)
        SELECT :e,:n,unnest(cast(:ids as integer[]))""",
        e=eid,
        n=number,
        ids=draft.reference_versions,
    )
    return one(
        db,
        """UPDATE exam SET published_number=:n,edit_number=edit_number+1
        WHERE id=:e RETURNING *""",
        n=number,
        e=eid,
    )
