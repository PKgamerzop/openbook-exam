"""Student-owned state serialized on the attempt row."""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import store
from app.access import DB, Student
from app.store import one

router = APIRouter(prefix="/api/student/exams/{eid}/attempt")


class Revision(BaseModel):
    revision: int = Field(ge=0)


class QuestionSave(Revision):
    answer: int | None
    flagged: bool


class ScratchSave(Revision):
    scratchpad: str = Field(max_length=12000, pattern=r"^[^\x00]*$")


def locked(db, eid, uid):
    attempt = one(
        db,
        """SELECT a.*,v.snapshot FROM exam_attempt a
        JOIN exam_version v ON (v.exam_id,v.number)=(a.exam_id,a.version)
        WHERE a.exam_id=:e AND a.student_id=:s FOR UPDATE OF a""",
        e=eid,
        s=uid,
    )
    if not attempt:
        raise HTTPException(404, "Attempt unavailable")
    return attempt


def expire(db, attempt, time):
    if attempt["finalized_at"] is None and time >= attempt["deadline"]:
        return one(
            db,
            """UPDATE exam_attempt SET finalized_at=deadline, final_reason='expired'
            WHERE id=:id RETURNING *""",
            id=attempt["id"],
        )
    return attempt


def payload(attempt, time):
    return {
        **{
            key: attempt[key]
            for key in (
                "id",
                "deadline",
                "responses",
                "scratchpad",
                "finalized_at",
                "final_reason",
            )
        },
        "revision": attempt["state_revision"],
        "server_time": time,
    }


def conflict(attempt, revision):
    if attempt["finalized_at"] is not None:
        return JSONResponse({"detail": "Attempt is finalized"}, status_code=409)
    if attempt["state_revision"] != revision:
        return JSONResponse(
            {"detail": "Attempt changed in another request. Reload saved work."},
            status_code=409,
        )
    return None


@router.get("")
def state(eid: int, db: DB, uid: Student):
    attempt = locked(db, eid, uid)
    time = store.now()
    current = expire(db, attempt, time)
    return payload(current, time) | {
        "questions": [
            {k: q[k] for k in ("stem", "options")}
            for q in attempt["snapshot"]["questions"]
        ]
    }


@router.put("/questions/{position}")
def save(eid: int, position: int, data: QuestionSave, db: DB, uid: Student):
    attempt = locked(db, eid, uid)
    time = store.now()
    if problem := conflict(expire(db, attempt, time), data.revision):
        return problem
    questions = attempt["snapshot"]["questions"]
    if not 0 <= position < len(questions) or (
        data.answer is not None
        and not 0 <= data.answer < len(questions[position]["options"])
    ):
        raise HTTPException(422, "Question or option unavailable")
    updated = one(
        db,
        """UPDATE exam_attempt SET responses=responses ||
        cast(:entry AS jsonb),state_revision=state_revision+1
        WHERE id=:id RETURNING *""",
        id=attempt["id"],
        entry=json.dumps({str(position): data.model_dump(exclude={"revision"})}),
    )
    return payload(updated, time)


@router.put("/scratchpad")
def scratch(eid: int, data: ScratchSave, db: DB, uid: Student):
    attempt = locked(db, eid, uid)
    time = store.now()
    if problem := conflict(expire(db, attempt, time), data.revision):
        return problem
    updated = one(
        db,
        """UPDATE exam_attempt SET scratchpad=:text,
        state_revision=state_revision+1 WHERE id=:id RETURNING *""",
        text=data.scratchpad,
        id=attempt["id"],
    )
    return payload(updated, time)


@router.post("/submit")
def submit(eid: int, data: Revision, db: DB, uid: Student):
    attempt = locked(db, eid, uid)
    time = store.now()
    attempt = expire(db, attempt, time)
    if attempt["finalized_at"] is not None:
        return payload(attempt, time)
    if problem := conflict(attempt, data.revision):
        return problem
    updated = one(
        db,
        """UPDATE exam_attempt SET finalized_at=:t,final_reason='submitted'
        WHERE id=:id RETURNING *""",
        t=time,
        id=attempt["id"],
    )
    return payload(updated, time)
