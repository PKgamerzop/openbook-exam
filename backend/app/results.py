"""Owned lecturer reporting and version-gated student feedback."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app import store
from app.access import DB, Lecturer, Student
from app.attempts import assigned
from app.authoring import owned
from app.store import one, rows

router = APIRouter(prefix="/api")
LECTURER = "/lecturer/exams/{eid}/results"
STUDENT = "/student/exams/{eid}/result"

COHORT = """
    FROM exam_assignment s
    LEFT JOIN exam_attempt a ON (a.exam_id,a.version,a.student_id)=
        (s.exam_id,s.version,s.student_id)
    LEFT JOIN attempt_grade g ON g.attempt_id=a.id
    WHERE s.exam_id=:e AND s.version=:v
"""


def exam_version(db, eid, uid):
    exam = owned(db, uid, eid)
    version = one(
        db,
        """SELECT * FROM exam_version WHERE exam_id=:e AND number=:v""",
        e=eid,
        v=exam["published_number"],
    )
    if not version:
        raise HTTPException(409, "Publish an examination before reviewing results")
    return version


def counts(db, eid, version):
    return dict(
        one(
            db,
            """SELECT count(*) AS assigned,count(a.id) AS started,
        count(a.finalized_at) AS finalized,count(g.attempt_id) AS graded,
        count(*) FILTER(WHERE a.final_reason='submitted') AS submitted,
        count(*) FILTER(WHERE a.final_reason='expired') AS expired,
        avg(g.score)::float AS average,min(g.score) AS lowest,max(g.score) AS highest
        """
            + COHORT,
            e=eid,
            v=version,
        )
    )


def release_block(version, totals):
    if store.now() < version["closes_at"]:
        return "The examination must close before results can be released."
    if (
        totals["finalized"] != totals["started"]
        or totals["graded"] != totals["finalized"]
    ):
        return (
            "Wait for expiry processing and complete grades for all started attempts."
        )
    return None


def release_record(db, eid, version):
    return one(
        db,
        """SELECT released_at,actor_id FROM exam_result_release
        WHERE exam_id=:e AND version=:v""",
        e=eid,
        v=version,
    )


def analytics(db, eid, version):
    questions = version["snapshot"]["questions"]
    by_position = {
        s["position"]: dict(s)
        for s in rows(
            db,
            """
        SELECT (item->>'position')::int AS position,
            count(*) FILTER(WHERE item->>'outcome'='correct') AS correct,
            count(*) FILTER(WHERE item->>'outcome'='incorrect') AS incorrect,
            count(*) FILTER(WHERE item->>'outcome'='unanswered') AS unanswered
        FROM exam_attempt a JOIN attempt_grade g ON g.attempt_id=a.id
        CROSS JOIN LATERAL jsonb_array_elements(g.assessment) item
        WHERE a.exam_id=:e AND a.version=:v GROUP BY 1
        """,
            e=eid,
            v=version["number"],
        )
    }
    stats = []
    groups = {"topics": {}, "objectives": {}}
    for i, q in enumerate(questions):
        result = by_position.get(
            i, dict(position=i, correct=0, incorrect=0, unanswered=0)
        )
        total = sum(result[k] for k in ("correct", "incorrect", "unanswered"))
        stats.append(result | dict(stem=q["stem"], total=total))
        for key, group in groups.items():
            for name in set(q.get(key, [])):
                tally = group.setdefault(name, dict(name=name, correct=0, total=0))
                tally["correct"] += result["correct"]
                tally["total"] += total
    distribution = list(
        rows(
            db,
            """SELECT g.score,count(*) AS students FROM attempt_grade g
        JOIN exam_attempt a ON a.id=g.attempt_id WHERE a.exam_id=:e AND a.version=:v
        GROUP BY g.score ORDER BY g.score""",
            e=eid,
            v=version["number"],
        )
    )
    return dict(
        questions=stats,
        distribution=distribution,
        **{k: [v[n] for n in sorted(v)] for k, v in groups.items()},
    )


@router.get(LECTURER)
def overview(eid: int, db: DB, uid: Lecturer, offset: int = Query(0, ge=0, le=5000)):
    version = exam_version(db, eid, uid)
    n = version["number"]
    totals = counts(db, eid, n)
    learners = list(
        rows(
            db,
            """
        SELECT u.username,a.id AS attempt_id,a.final_reason,
            g.score,g.maximum,g.graded_at
        FROM exam_assignment s JOIN account u ON u.id=s.student_id
        LEFT JOIN exam_attempt a ON (a.exam_id,a.version,a.student_id)=
            (s.exam_id,s.version,s.student_id)
        LEFT JOIN attempt_grade g ON g.attempt_id=a.id
        WHERE s.exam_id=:e AND s.version=:v ORDER BY u.username,u.id LIMIT 30 OFFSET :o
        """,
            e=eid,
            v=n,
            o=offset,
        )
    )
    return dict(
        title=version["snapshot"]["title"],
        version=n,
        totals=totals,
        students=learners,
        release=release_record(db, eid, n),
        release_block=release_block(version, totals),
        **analytics(db, eid, version),
    )


def feedback(grade, question_set):
    return dict(
        score=grade["score"],
        maximum=grade["maximum"],
        correct=grade["score"],
        incorrect=grade["incorrect"],
        unanswered=grade["unanswered"],
        graded_at=grade["graded_at"],
        percentage=round(100 * grade["score"] / grade["maximum"], 2),
        questions=[
            {
                **entry,
                **{k: q[k] for k in ("stem", "options", "correct")},
                "explanation": q.get("explanation"),
            }
            for entry, q in zip(grade["assessment"], question_set, strict=True)
        ],
    )


@router.get(LECTURER + "/attempts/{aid}")
def lecturer_attempt(eid: int, aid: int, db: DB, uid: Lecturer):
    version = exam_version(db, eid, uid)
    grade = one(
        db,
        """SELECT g.* FROM exam_attempt a JOIN attempt_grade g ON g.attempt_id=a.id
        WHERE a.id=:a AND a.exam_id=:e AND a.version=:v""",
        a=aid,
        e=eid,
        v=version["number"],
    )
    if not grade:
        raise HTTPException(404, "Graded attempt unavailable")
    return feedback(grade, version["snapshot"]["questions"])


@router.post(LECTURER + "/release")
def release(eid: int, db: DB, uid: Lecturer):
    version = exam_version(db, eid, uid)
    n = version["number"]
    if existing := release_record(db, eid, n):
        return existing
    if reason := release_block(version, counts(db, eid, n)):
        raise HTTPException(409, reason)
    return one(
        db,
        """INSERT INTO exam_result_release(exam_id,version,actor_id,released_at)
        VALUES(:e,:v,:u,:t) RETURNING released_at,actor_id""",
        e=eid,
        v=n,
        u=uid,
        t=store.now(),
    )


class QuestionFeedback(BaseModel):
    position: int
    stem: str
    options: list[str]
    correct: int
    selected: int | None
    outcome: Literal["correct", "incorrect", "unanswered"]
    explanation: str | None = None


class AssessmentFeedback(BaseModel):
    score: int
    maximum: int
    correct: int
    incorrect: int
    unanswered: int
    graded_at: datetime
    percentage: float
    questions: list[QuestionFeedback]


class StudentResult(BaseModel):
    status: Literal["not_started", "in_progress", "submitted", "expired"]
    released: bool
    feedback: AssessmentFeedback | None = None


@router.get(STUDENT, response_model=StudentResult, response_model_exclude_unset=True)
def student_result(eid: int, db: DB, uid: Student):
    version = assigned(db, eid, uid)
    n = version["number"]
    attempt = one(
        db,
        """SELECT id,final_reason FROM exam_attempt
        WHERE exam_id=:e AND version=:v AND student_id=:s""",
        e=eid,
        v=n,
        s=uid,
    )
    status = attempt["final_reason"] or "in_progress" if attempt else "not_started"
    released = bool(release_record(db, eid, n))
    response = dict(status=status, released=released)
    if released and attempt and attempt["final_reason"]:
        grade = one(
            db, "SELECT * FROM attempt_grade WHERE attempt_id=:a", a=attempt["id"]
        )
        if grade:
            response["feedback"] = feedback(grade, version["snapshot"]["questions"])
    return response
