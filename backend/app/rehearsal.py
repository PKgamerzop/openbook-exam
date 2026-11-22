"""Create timed Phase 4 rehearsals alongside the existing local DBMS demo."""

import argparse
import os
from datetime import timedelta

from app import store
from app.authoring import Draft, create, publish_snapshot, validate_publication
from app.db import get_engine
from app.demo import KEYS, QUESTIONS, USERS
from app.store import one, rows

TITLES = ("DBMS Rehearsal — Timed workspace", "DBMS Rehearsal — Calculator disabled")


def seed_rehearsals():
    engine = get_engine()
    if (
        engine.url.host not in {"127.0.0.1", "localhost", "::1"}
        or engine.url.database not in {"openbook", "openbook_demo"}
        or os.getenv("OPENBOOK_LOCAL_HTTP") != "1"
    ):
        raise ValueError("Phase 4 rehearsal requires the local demo database")
    with engine.begin() as db:
        rows(db, "SELECT pg_advisory_xact_lock(28300103)")
        marker = one(db, "SELECT * FROM openbook_demo_v3")
        cid = marker["course_id"]
        lecturer = one(db, "SELECT owner_id FROM course WHERE id=:c", c=cid)["owner_id"]
        students = [
            r["id"]
            for r in rows(
                db, "SELECT id FROM account WHERE username=ANY(:names)", names=USERS[1:]
            )
        ]
        now = store.now()
        ids = []
        for i, title in enumerate(TITLES):
            existing = one(
                db,
                "SELECT id FROM exam WHERE course_id=:c AND draft->>'title'=:t",
                c=cid,
                t=title,
            )
            if existing:
                ids.append(existing["id"])
                continue
            questions = [
                dict(stem=stem, options=[a, b], topics=[topic], correct=key)
                for group, keys in zip(QUESTIONS, KEYS, strict=True)
                for (topic, stem, a, b), key in zip(group, keys, strict=True)
            ]
            opening = now - timedelta(minutes=1)
            draft = Draft(
                title=title,
                instructions="Choose one answer for each scenario.",
                rules="Use the attached DBMS guides.",
                opens_at=opening,
                closes_at=now + timedelta(days=7),
                duration=15 if i == 0 else 2,
                calculator=i == 0,
                questions=questions,
                students=students,
                reference_versions=marker["versions"][:4],
            )
            validate_publication(draft, opening - timedelta(seconds=1))
            exam = create(cid, draft, db, lecturer)
            publish_snapshot(db, exam["id"], exam, draft)
            ids.append(exam["id"])
        return ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true", required=True)
    parser.parse_args()
    print("Phase 4 rehearsal exam IDs:", *seed_rehearsals())
