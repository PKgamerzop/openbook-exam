from datetime import timedelta

from fastapi import APIRouter, HTTPException

from app import store
from app.access import DB, Student
from app.store import one, rows

router = APIRouter(prefix="/api/student/exams")
ASSIGNED = """SELECT v.* FROM exam e
    JOIN exam_version v ON (v.exam_id,v.number)=(e.id,e.published_number)
    JOIN exam_assignment a ON (a.exam_id,a.version)=(v.exam_id,v.number)
    WHERE a.student_id=:s"""


def summary(version, time):
    draft = version["snapshot"]
    status = (
        "upcoming"
        if time < version["opens_at"]
        else ("open" if time < version["closes_at"] else "closed")
    )
    return {
        **{
            k: draft[k]
            for k in (
                "title",
                "instructions",
                "rules",
                "calculator",
                "opens_at",
                "closes_at",
                "duration",
            )
        },
        **(
            {"pre_release": draft.get("pre_release", False)}
            if draft.get("reference_versions")
            else {}
        ),
        "id": version["exam_id"],
        "availability": status,
    }


@router.get("")
def exams(db: DB, uid: Student):
    return [
        summary(v, store.now())
        for v in rows(db, ASSIGNED + " ORDER BY v.opens_at", s=uid)
    ]


def assigned(db, eid, uid):
    version = one(db, ASSIGNED + " AND e.id=:e", s=uid, e=eid)
    if not version:
        raise HTTPException(404, "Exam unavailable")
    return version


@router.get("/{eid}")
def details(eid: int, db: DB, uid: Student):
    return summary(assigned(db, eid, uid), store.now())


@router.post("/{eid}/start")
def start(eid: int, db: DB, uid: Student):
    assigned(db, eid, uid)
    one(db, "SELECT id FROM exam WHERE id=:e FOR UPDATE", e=eid)
    version = assigned(db, eid, uid)
    time = store.now()
    if not version["opens_at"] <= time < version["closes_at"]:
        raise HTTPException(409, "Outside the scheduled window")
    snapshot = version["snapshot"]
    deadline = min(version["closes_at"], time + timedelta(minutes=snapshot["duration"]))
    attempt = one(
        db,
        """INSERT INTO exam_attempt(exam_id,version,student_id,
        started_at,deadline) VALUES (:e,:n,:s,:t,:d)
        ON CONFLICT (exam_id,student_id) DO NOTHING RETURNING id,started_at,deadline""",
        e=eid,
        n=version["number"],
        s=uid,
        t=time,
        d=deadline,
    )
    if not attempt:
        attempt = one(
            db,
            """SELECT id,started_at,deadline FROM exam_attempt
            WHERE exam_id=:e AND student_id=:s""",
            e=eid,
            s=uid,
        )
    if time >= attempt["deadline"]:
        raise HTTPException(409, "Attempt duration has elapsed")
    return {
        **attempt,
        "questions": [
            {"stem": q["stem"], "options": q["options"]} for q in snapshot["questions"]
        ],
    }
