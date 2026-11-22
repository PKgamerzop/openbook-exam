"""Create closed synthetic exam results using the production grading trigger."""

import argparse
import json
import os
from datetime import timedelta

from app import store
from app.authoring import Draft, create, publish_snapshot, validate_publication
from app.db import get_engine
from app.demo import KEYS, QUESTIONS, USERS
from app.results import release
from app.store import one, rows

TITLES = ("DBMS Results — Released", "DBMS Results — Awaiting release")


def seed_results():
    engine = get_engine()
    if (
        engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or engine.url.database not in {"openbook", "openbook_demo"}
        or os.getenv("OPENBOOK_LOCAL_HTTP") != "1"
    ):
        raise ValueError("Use the approved local development database")
    with engine.begin() as db:
        rows(db, "SELECT pg_advisory_xact_lock(28300103)")
        marker = one(db, "SELECT * FROM openbook_demo_v3")
        cid = marker["course_id"]
        uid = one(db, "SELECT owner_id FROM course WHERE id=:c", c=cid)["owner_id"]
        students = [
            r["id"]
            for r in rows(
                db,
                "SELECT id FROM account WHERE username=ANY(:names) ORDER BY username",
                names=USERS[1:],
            )
        ]
        opening = store.now() - timedelta(days=2)
        closing = opening + timedelta(hours=1)
        ids = []
        for i, title in enumerate(TITLES):
            if prior := one(
                db,
                """SELECT id FROM exam WHERE course_id=:c
                AND draft->>'title'=:t""",
                c=cid,
                t=title,
            ):
                ids.append(prior["id"])
                continue
            questions = [
                dict(
                    stem=stem,
                    options=[a, b],
                    correct=key,
                    topics=[topic, "DBMS"],
                    explanation=f"Review the worked examples for {topic.lower()}.",
                )
                for (topic, stem, a, b), key in zip(QUESTIONS[i], KEYS[i], strict=True)
            ]
            draft = Draft(
                title=title,
                students=students,
                questions=questions,
                opens_at=opening,
                closes_at=closing,
                duration=60,
                instructions="Choose one response per scenario.",
                rules="Use permitted DBMS guides.",
                reference_versions=marker["versions"][i * 2 : i * 2 + 2],
            )
            validate_publication(draft, opening - timedelta(seconds=1))
            exam = create(cid, draft, db, uid)
            eid = exam["id"]
            publish_snapshot(db, eid, exam, draft)
            for student, correct, answered in zip(
                students[:5], [5, 3, 1, 2, 0], [5, 5, 5, 2, 0], strict=True
            ):
                data = {
                    str(j): {
                        "answer": q.correct if j < correct else 1 - q.correct,
                        "flagged": False,
                    }
                    for j, q in enumerate(draft.questions[:answered])
                }
                reason = "expired" if not answered else "submitted"
                rows(
                    db,
                    """INSERT INTO exam_attempt
                    (exam_id,version,student_id,started_at,deadline,responses,
                     finalized_at,final_reason)
                    VALUES(:e,1,:s,:o,:c,cast(:r as jsonb),:c,:f)""",
                    e=eid,
                    s=student,
                    o=opening,
                    c=closing,
                    r=json.dumps(data),
                    f=reason,
                )
            if i == 0:
                release(eid, db, uid)
            ids.append(eid)
        return ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true", required=True)
    parser.parse_args()
    print("Phase 5 released and unreleased exam IDs:", *seed_results())
