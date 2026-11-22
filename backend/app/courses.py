from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from app.access import DB, Lecturer
from app.store import one, rows

router = APIRouter(prefix="/api/courses")
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)
]


class CourseName(BaseModel):
    name: Name


class Enrollment(BaseModel):
    username: Name


def owned_course(db, uid, cid):
    course = one(
        db, "SELECT id,name FROM course WHERE owner_id=:u AND id=:c", u=uid, c=cid
    )
    if not course:
        raise HTTPException(404, "Course unavailable")
    return course


@router.get("")
def courses(db: DB, uid: Lecturer):
    return list(
        rows(db, "SELECT id,name FROM course WHERE owner_id=:u ORDER BY name", u=uid)
    )


@router.post("")
def create(data: CourseName, db: DB, uid: Lecturer):
    return one(
        db,
        """INSERT INTO course (name, owner_id) VALUES (:n,:u)
               ON CONFLICT (owner_id,name) DO UPDATE SET name=excluded.name
               RETURNING id,name""",
        n=data.name,
        u=uid,
    )


@router.get("/{cid}")
def details(cid: int, db: DB, uid: Lecturer):
    course = owned_course(db, uid, cid)
    return {
        **course,
        "students": list(
            rows(
                db,
                """SELECT a.id,a.username FROM account a
        JOIN enrollment e ON e.student_id=a.id WHERE course_id=:c ORDER BY username""",
                c=cid,
            )
        ),
        "labels": list(
            rows(
                db,
                """SELECT kind,name FROM classification
        WHERE course_id=:c ORDER BY name""",
                c=cid,
            )
        ),
    }


@router.post("/{cid}/enroll")
def enroll(cid: int, data: Enrollment, db: DB, uid: Lecturer):
    owned_course(db, uid, cid)
    person = one(
        db,
        "SELECT id FROM account WHERE username=:n AND role='student'",
        n=data.username,
    )
    if not person:
        raise HTTPException(422, "Unknown student username")
    rows(
        db,
        """INSERT INTO enrollment VALUES (:c,:s)
         ON CONFLICT DO NOTHING RETURNING 1""",
        c=cid,
        s=person["id"],
    )
    return {"student_id": person["id"]}
