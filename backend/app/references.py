import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app import store
from app.access import DB, Lecturer, Student
from app.attempts import assigned
from app.courses import Name, owned_course
from app.pdf_files import inspect_pdf, path_for
from app.store import one, rows

router = APIRouter(prefix="/api")
COURSE = "/lecturer/courses/{cid}/references"
EXAM = "/student/exams/{eid}/references"
METADATA = """SELECT v.id,v.document_id,v.number,v.filename,v.title,v.size,v.pages,
    v.created_at,v.status,d.folder,d.topics FROM reference_version v
    JOIN reference_document d ON d.id=v.document_id"""


class Organization(BaseModel):
    folder: Name
    topics: list[Name] = Field(max_length=30)


@router.get(COURSE)
def library(cid: int, uid: Lecturer, db: DB):
    owned_course(db, uid, cid)
    return list(
        rows(db, METADATA + " WHERE d.course_id=:c ORDER BY d.id,v.number DESC", c=cid)
    )


@router.put(COURSE + "/documents/{did}")
def organize(cid: int, did: int, data: Organization, uid: Lecturer, db: DB):
    owned_course(db, uid, cid)
    if not one(
        db,
        """UPDATE reference_document SET folder=:f,topics=:t
        WHERE course_id=:c AND id=:d RETURNING id""",
        c=cid,
        d=did,
        f=data.folder,
        t=data.topics,
    ):
        raise HTTPException(404, "Document unavailable")
    return {"saved": True}


@router.post(COURSE)
async def upload(
    cid: int,
    request: Request,
    uid: Lecturer,
    db: DB,
    filename: Name,
    title: Name,
    folder: Name = "General",
    document_id: int | None = None,
):
    owned_course(db, uid, cid)
    limit = int(os.getenv("OPENBOOK_PDF_MAX_BYTES", "20971520"))
    key = uuid4()
    path = path_for(key)
    size = 0
    try:
        with path.open("xb") as output:
            async for chunk in request.stream():
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, "PDF exceeds the upload limit")
                output.write(chunk)
        try:
            pages = await run_in_threadpool(inspect_pdf, path)
        except ValueError:
            raise HTTPException(422, "Invalid, encrypted or oversized PDF") from None
        if document_id is None:
            document_id = one(
                db,
                """INSERT INTO reference_document(course_id,folder)
                VALUES (:c,:f) RETURNING id""",
                c=cid,
                f=folder,
            )["id"]
        elif not one(
            db,
            """SELECT id FROM reference_document WHERE id=:d AND course_id=:c
                              FOR UPDATE""",
            d=document_id,
            c=cid,
        ):
            raise HTTPException(404, "Document unavailable")
        version = one(
            db,
            """INSERT INTO reference_version
            (document_id,number,storage_key,filename,title,size,pages)
            SELECT :d,coalesce(max(number),0)+1,:k,:f,:t,:s,:p
            FROM reference_version WHERE document_id=:d RETURNING id,number""",
            d=document_id,
            k=key,
            f=filename,
            t=title,
            s=size,
            p=pages,
        )
        rows(db, "INSERT INTO reference_job(version_id) VALUES (:v)", v=version["id"])
        db.commit()
        return dict(version)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


@router.post(COURSE + "/{vid}/retry")
def retry(cid: int, vid: int, db: DB, uid: Lecturer):
    owned_course(db, uid, cid)
    if not one(
        db,
        """UPDATE reference_version v SET status='processing'
        FROM reference_document d WHERE v.document_id=d.id AND d.course_id=:c
        AND v.id=:v AND v.status='failed' RETURNING v.id""",
        c=cid,
        v=vid,
    ):
        raise HTTPException(409, "No failed job available")
    rows(db, "INSERT INTO reference_job(version_id) VALUES (:v)", v=vid)
    return {"status": "processing"}


def deliver(record, request):
    if not record:
        raise HTTPException(404, "PDF unavailable")
    path = path_for(record["storage_key"])
    if not path.is_file():
        raise HTTPException(404, "PDF unavailable")
    header = request.headers.get("range", "")
    if "," in header or len(header) > 128:
        raise HTTPException(
            416,
            "Use one byte range",
            headers={"Content-Range": f"bytes */{path.stat().st_size}"},
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@router.get(COURSE + "/{vid}/file")
def preview(cid: int, vid: int, request: Request, uid: Lecturer, db: DB):
    owned_course(db, uid, cid)
    return deliver(
        one(
            db,
            """SELECT storage_key FROM reference_version v JOIN
        reference_document d ON d.id=v.document_id WHERE v.id=:v AND d.course_id=:c""",
            c=cid,
            v=vid,
        ),
        request,
    )


def permitted(db, eid, uid):
    version = assigned(db, eid, uid)
    time = store.now()
    if time < version["opens_at"] and version["snapshot"].get("pre_release", False):
        return version["number"]
    if version["opens_at"] <= time < version["closes_at"] and one(
        db,
        """SELECT id FROM exam_attempt WHERE exam_id=:e AND version=:n AND student_id=:s
            AND started_at<=:t AND deadline>:t""",
        e=eid,
        n=version["number"],
        s=uid,
        t=time,
    ):
        return version["number"]
    raise HTTPException(
        403,
        "References are unavailable outside the authorized access window",
    )


BINDING = """ JOIN exam_reference r ON r.version_id=v.id
    WHERE r.exam_id=:e AND r.revision=:n"""


@router.get(EXAM)
def resources(eid: int, uid: Student, db: DB):
    revision = permitted(db, eid, uid)
    return list(
        rows(db, METADATA + BINDING + " ORDER BY v.title,v.id", e=eid, n=revision)
    )


@router.get(EXAM + "/search")
def search(
    eid: int,
    uid: Student,
    db: DB,
    q: str = Query(max_length=160),
    offset: int = Query(0, ge=0, le=10000),
):
    revision = permitted(db, eid, uid)
    if not q.strip():
        return []
    return list(
        rows(
            db,
            """SELECT v.id,v.document_id,v.number,v.title,p.page,
        left(ts_headline('simple',p.content,query,
        'StartSel="", StopSel="", MaxWords=24, MinWords=8'),320) AS snippet
        FROM reference_version v JOIN reference_page p ON p.version_id=v.id
        CROSS JOIN plainto_tsquery('simple',:q) query"""
            + BINDING
            + """ AND v.status='searchable' AND p.vector @@ query
        ORDER BY ts_rank(p.vector,query) DESC,v.id,p.page LIMIT 30 OFFSET :offset""",
            e=eid,
            n=revision,
            q=q,
            offset=offset,
        )
    )


@router.get(EXAM + "/{vid}/file")
def student_file(eid: int, vid: int, request: Request, uid: Student, db: DB):
    revision = permitted(db, eid, uid)
    return deliver(
        one(
            db,
            "SELECT v.storage_key FROM reference_version v" + BINDING + " AND v.id=:v",
            e=eid,
            n=revision,
            v=vid,
        ),
        request,
    )
