"""Opt-in synthetic Phase 6 staging data. Never invoked during startup."""

import argparse
import json
import os
import sys
from datetime import timedelta
from io import BytesIO
from uuid import uuid4

from pypdf import PdfReader, PdfWriter

from app import store
from app.access import password_hash
from app.authoring import Draft, create, publish_snapshot, validate_publication
from app.db import get_engine
from app.demo import KEYS, QUESTIONS
from app.demo_fixtures import fixture
from app.pdf_files import inspect_pdf, path_for
from app.results import release
from app.settings import validate_deployment
from app.store import one, rows

STUDENTS = 60
TEACHER = "pilot_lecturer"


def document_bytes(name):
    if name != "indexing-guide":
        return fixture(name)
    source = PdfReader(BytesIO(fixture(name)))
    writer = PdfWriter()
    for i in range(120):
        writer.add_page(source.pages[i % len(source.pages)])
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def create_references(db, course, files):
    versions = []
    for name in ("indexing-guide", "transactions-guide", "normalization-guide", "scan"):
        key = uuid4()
        path = path_for(key)
        files.append(path)
        path.write_bytes(document_bytes(name))
        pages = inspect_pdf(path)
        document = one(
            db,
            "INSERT INTO reference_document(course_id,folder) "
            "VALUES (:c,'Synthetic DBMS guides') RETURNING id",
            c=course,
        )
        version = one(
            db,
            """INSERT INTO reference_version
            (document_id,number,storage_key,filename,title,size,pages)
            VALUES (:d,1,:k,:f,:t,:s,:p) RETURNING id""",
            d=document["id"],
            k=key,
            f=name + ".pdf",
            t=name.replace("-", " ").title(),
            s=path.stat().st_size,
            p=pages,
        )["id"]
        rows(db, "INSERT INTO reference_job(version_id) VALUES (:v)", v=version)
        versions.append(version)
    return versions


def seed(password):
    validate_deployment()
    if os.getenv("OPENBOOK_ENV") != "staging":
        raise ValueError("Pilot seeding requires isolated HTTPS staging")
    files = []
    try:
        with get_engine().begin() as db:
            rows(db, "SELECT pg_advisory_xact_lock(28300601)")
            rows(
                db,
                """CREATE TABLE IF NOT EXISTS openbook_pilot_v6
                (singleton boolean PRIMARY KEY CHECK(singleton),
                 manifest jsonb NOT NULL)""",
            )
            prior = one(db, "SELECT manifest FROM openbook_pilot_v6")
            if prior:
                return prior["manifest"]
            if one(db, "SELECT id FROM account LIMIT 1"):
                raise ValueError("Pilot seed requires a database without accounts")
            if not 16 <= len(password) <= 128:
                raise ValueError("Generate a local 16–128 character pilot password")
            teacher = one(
                db,
                """INSERT INTO account(username,role,password_hash)
                VALUES (:u,'lecturer',:p) RETURNING id""",
                u=TEACHER,
                p=password_hash(password),
            )["id"]
            students = [
                one(
                    db,
                    """INSERT INTO account(username,role,password_hash)
                    VALUES (:n,'student',:p) RETURNING id""",
                    n=f"pilot_student_{i:02}",
                    p=password_hash(password),
                )["id"]
                for i in range(1, STUDENTS + 1)
            ]
            course = one(
                db,
                "INSERT INTO course(name,owner_id) VALUES (:n,:u) RETURNING id",
                n="Phase 6 pilot – Database Management Systems",
                u=teacher,
            )["id"]
            for student in students:
                rows(db, "INSERT INTO enrollment VALUES (:c,:s)", c=course, s=student)
            versions = create_references(db, course, files)
            now = store.now()
            exams = {}
            for label, cohort in (
                ("load30-a", students[:30:2]),
                ("load30-b", students[1:30:2]),
                ("load60-a", students[::2]),
                ("load60-b", students[1::2]),
                ("rehearsal", students[:6]),
                ("released", students[:9]),
                ("unreleased", students[5:14]),
            ):
                historic = label in {"released", "unreleased"}
                opening = now - (
                    timedelta(days=2) if historic else timedelta(minutes=1)
                )
                closing = opening + (
                    timedelta(hours=1) if historic else timedelta(days=7)
                )
                refs = versions[2:] if label.endswith("-b") else versions[:2]
                questions = [
                    dict(stem=stem, options=[a, b], topics=[topic], correct=key)
                    for group, keys in zip(QUESTIONS, KEYS, strict=True)
                    for (topic, stem, a, b), key in zip(group, keys, strict=True)
                ]
                draft = Draft(
                    title=f"DBMS pilot {label}",
                    instructions="Choose one response.",
                    rules="Use only the permitted DBMS guides.",
                    duration=60,
                    opens_at=opening,
                    closes_at=closing,
                    students=cohort,
                    reference_versions=refs,
                    questions=questions,
                    calculator=True,
                )
                validate_publication(draft, opening - timedelta(seconds=1))
                exam = create(course, draft, db, teacher)
                eid = exam["id"]
                publish_snapshot(db, eid, exam, draft)
                exams[label] = eid
                if historic:
                    add_historical(db, eid, cohort, refs[0], draft)
                    if label == "released":
                        release(eid, db, teacher)
            manifest = dict(course=course, exams=exams, versions=versions)
            rows(
                db,
                "INSERT INTO openbook_pilot_v6 VALUES(true,cast(:m as jsonb))",
                m=json.dumps(manifest),
            )
    except BaseException:
        for path in files:
            path.unlink(missing_ok=True)
        raise
    return manifest


def add_historical(db, eid, students, version, draft):
    for i, student in enumerate(students[:5]):
        responses = (
            {}
            if i == 0
            else {
                "0": {"answer": draft.questions[0].correct, "flagged": True},
                "1": {"answer": 1 - draft.questions[1].correct, "flagged": False},
            }
        )
        rows(
            db,
            """INSERT INTO exam_attempt(exam_id,version,student_id,started_at,deadline,
                responses,scratchpad,finalized_at,final_reason)
                VALUES(:e,1,:s,:o,:c,cast(:r as jsonb),:pad,:t,:reason)""",
            e=eid,
            s=student,
            o=draft.opens_at,
            c=draft.closes_at,
            r=json.dumps(responses),
            pad="Synthetic transaction notes",
            t=draft.closes_at if i == 0 else draft.opens_at + timedelta(minutes=20),
            reason="expired" if i == 0 else "submitted",
        )
        rows(
            db,
            """INSERT INTO exam_page_mark
            (exam_id,revision,student_id,version_id,page,name,pinned)
            VALUES(:e,1,:s,:v,1,'Review index selection',true)""",
            e=eid,
            s=student,
            v=version,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic-staging", required=True, action="store_true")
    parser.parse_args()
    print(json.dumps(seed(sys.stdin.readline().rstrip("\r\n")), sort_keys=True))
