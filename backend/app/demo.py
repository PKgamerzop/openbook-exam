"""Development-only DBMS seed. Invoke from the repository's backend directory."""

import argparse
import os
import sys
from datetime import timedelta
from getpass import getpass
from uuid import uuid4

from app import store
from app.access import password_hash
from app.authoring import Draft, create, publish_snapshot, validate_publication
from app.db import get_engine
from app.demo_fixtures import NOTES, fixture
from app.pdf_files import inspect_pdf, path_for
from app.reference_worker import process_one
from app.store import one, rows

COURSE = "Database Management Systems · Computer Science Engineering — Semester 5"
USERS = ["demo_lecturer", *(f"demo_student_{i:02}" for i in range(1, 7))]
TITLES = [
    "DBMS Open-Book Exam A — Indexing and Transactions",
    "DBMS Open-Book Exam B — Query Optimization and Normalization",
]
QUESTIONS = [
    [
        (
            "B-tree indexes",
            "A ticket lookup specifies one unique ID. Which operation exploits a "
            "B-tree?",
            "Descend through separators to the leaf",
            "Scan all data pages",
        ),
        (
            "Range queries",
            "A report needs consecutive indexed ticket numbers. After locating the "
            "first leaf, what next?",
            "Rebuild the root",
            "Scan ordered leaves to the upper bound",
        ),
        (
            "Transaction isolation",
            "Two reports in one transaction must read the same committed snapshot. "
            "Which property matters?",
            "Stable snapshot visibility",
            "Larger disk blocks",
        ),
        (
            "Deadlocks",
            "Two transfers each wait on the other's lock. Which intervention lets "
            "one finish?",
            "Wait for both to commit",
            "Roll back one transfer",
        ),
        (
            "Concurrent updates",
            "Two clerks increment the same balance. How can the system prevent a "
            "lost update?",
            "Serialize the conflicting updates",
            "Copy the initial value into both clients",
        ),
    ],
    [
        (
            "Join strategies",
            "A small table fits in memory and joins a stream on equality. Which "
            "strategy fits?",
            "Build a hash table on the small input",
            "Sort the output after every row",
        ),
        (
            "Query plans",
            "A filter returns fifty times its row estimate. What should the "
            "engineer inspect?",
            "Column statistics and selectivity",
            "The result column names",
        ),
        (
            "Execution cost",
            "A hash build spills to disk. Which additional cost belongs in the "
            "estimate?",
            "Only the number of output columns",
            "Partition writes and reads",
        ),
        (
            "Functional dependencies",
            "Each bench has one room. Which dependency follows?",
            "Bench determines room",
            "Room determines bench",
        ),
        (
            "Normalization",
            "Room names recur on every reservation for a bench. Which change avoids "
            "inconsistent edits?",
            "Duplicate room names in another column",
            "Store bench locations once and reference bench keys",
        ),
    ],
]
KEYS = [[0, 1, 0, 1, 0], [0, 0, 1, 0, 1]]


def seed(password_provider):
    engine = get_engine()
    if (
        engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or engine.url.database not in {"openbook", "openbook_demo"}
        or os.getenv("OPENBOOK_LOCAL_HTTP") != "1"
    ):
        raise ValueError(
            "Use a loopback openbook or openbook_demo development database with "
            "local HTTP enabled"
        )
    paths = []
    try:
        with engine.begin() as db:
            rows(db, "SELECT pg_advisory_xact_lock(28300103)")
            # Local seed marker is created only in the development database.
            rows(
                db,
                """CREATE TABLE IF NOT EXISTS openbook_demo_v3
                (singleton boolean PRIMARY KEY CHECK(singleton),
                 course_id integer REFERENCES course,
                 exams integer[] NOT NULL, versions integer[] NOT NULL)""",
            )
            marker = one(db, "SELECT * FROM openbook_demo_v3")
            if not marker:
                if one(
                    db, "SELECT id FROM account WHERE username=ANY(:names)", names=USERS
                ):
                    raise ValueError(
                        "Demo usernames already exist outside this dataset"
                    )
                password = password_provider()
                if not 12 <= len(password) <= 128:
                    raise ValueError("Choose a 12-128 character local demo password")
                people = [
                    one(
                        db,
                        """INSERT INTO account(username,role,password_hash)
                        VALUES (:u,:r,:p)
                    RETURNING id""",
                        u=name,
                        r="student" if i else "lecturer",
                        p=password_hash(password),
                    )["id"]
                    for i, name in enumerate(USERS)
                ]
                cid = one(
                    db,
                    "INSERT INTO course(name,owner_id) VALUES (:n,:u) RETURNING id",
                    n=COURSE,
                    u=people[0],
                )["id"]
                for sid in people[1:]:
                    rows(db, "INSERT INTO enrollment VALUES (:c,:s)", c=cid, s=sid)
                versions = []
                for name in [*NOTES, "scan"]:
                    key = uuid4()
                    path = path_for(key)
                    path.write_bytes(fixture(name))
                    paths.append(path)
                    count = inspect_pdf(path)
                    doc = one(
                        db,
                        """INSERT INTO reference_document(course_id,folder,topics)
                        VALUES (:c,'Engineering guides',:t) RETURNING id""",
                        c=cid,
                        t=[name.split("-")[0]],
                    )
                    vid = one(
                        db,
                        """INSERT INTO reference_version
                        (document_id,number,storage_key,filename,title,size,pages)
                        VALUES (:d,1,:k,:f,:t,:s,:p) RETURNING id""",
                        d=doc["id"],
                        k=key,
                        f=name + ".pdf",
                        t=name.replace("-", " ").title(),
                        s=path.stat().st_size,
                        p=count,
                    )["id"]
                    rows(db, "INSERT INTO reference_job(version_id) VALUES (:v)", v=vid)
                    versions.append(vid)
                exams = []
                time = store.now()
                for i, title in enumerate(TITLES):
                    opens = time + timedelta(hours=24 if i else -1)
                    draft = Draft(
                        title=title,
                        instructions="Choose one response per scenario.",
                        rules="Use the listed engineering guides.",
                        duration=120,
                        opens_at=opens,
                        closes_at=opens + timedelta(days=2),
                        pre_release=bool(i),
                        students=[people[j] for j in ([3, 4, 5] if i else [1, 2, 5])],
                        reference_versions=versions[i * 2 : i * 2 + 2],
                        questions=[
                            dict(stem=stem, options=[a, b], topics=[topic], correct=key)
                            for (topic, stem, a, b), key in zip(
                                QUESTIONS[i], KEYS[i], strict=True
                            )
                        ],
                    )
                    validate_publication(draft, opens - timedelta(seconds=1))
                    exam = create(cid, draft, db, people[0])
                    publish_snapshot(db, exam["id"], exam, draft)
                    exams.append(exam["id"])
                marker = one(
                    db,
                    "INSERT INTO openbook_demo_v3 VALUES(true,:c,:e,:v) RETURNING *",
                    c=cid,
                    e=exams,
                    v=versions,
                )
    except BaseException:
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    for vid in marker["versions"]:
        process_one(vid)
    with engine.connect() as db:
        states = list(
            rows(
                db,
                "SELECT filename,status FROM reference_version WHERE id=ANY(:v) "
                "ORDER BY id",
                v=marker["versions"],
            )
        )
    if [v["status"] for v in states] != ["searchable"] * 4 + ["view-only"]:
        raise RuntimeError(
            "Demo indexing incomplete. Check worker status and retry failed versions."
        )
    return marker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", required=True, action="store_true")
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    marker = seed(
        lambda: (
            sys.stdin.readline().rstrip("\r\n")
            if args.password_stdin
            else getpass("Choose a local password for the seven demo accounts: ")
        )
    )
    print("Course:", COURSE, marker["course_id"])
    print("Exam A and B IDs:", *marker["exams"])
    print("Accounts:", ", ".join(USERS))
    print(
        "Five references verified. Existing schedules, passwords and attempts are "
        "preserved."
    )


if __name__ == "__main__":
    main()
