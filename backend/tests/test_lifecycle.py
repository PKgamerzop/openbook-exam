from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from conftest import client
from pydantic import ValidationError

from app.authoring import Question
from app.db import get_engine
from app.store import one

QUESTION = {
    "stem": "Which number is even?",
    "options": ["Three", "Four"],
    "correct": 1,
    "topics": ["Parity"],
}


@pytest.mark.parametrize(
    "patch",
    [
        {"stem": " "},
        {"options": ["One"]},
        {"correct": 2},
        {"correct": -1},
        {"topics": []},
        {"topics": [" "]},
    ],
)
def test_mcq_requires_stem_options_key_and_topics(patch):
    with pytest.raises(ValidationError):
        Question.model_validate(QUESTION | patch)


def test_objectives_optional():
    assert Question.model_validate(QUESTION).objectives == []
    assert Question.model_validate(QUESTION | {"objectives": ["Classify"]}).objectives


def test_exam_lifecycle(pilot):
    password, clock = pilot
    teacher, other, learner, outside = [client() for _ in range(4)]
    assert teacher.get("/api/me").status_code == 401
    assert (
        teacher.post(
            "/api/login", json={"username": "teacher", "password": "wrong"}
        ).status_code
        == 401
    )
    for session, name in zip(
        [teacher, other, learner, outside],
        ["teacher", "other", "learner", "outside"],
        strict=True,
    ):
        response = session.post(
            "/api/login", json={"username": name, "password": password}
        )
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        assert session.get("/api/me").json()["username"] == name
    assert learner.get("/api/courses").status_code == 403
    assert teacher.get("/api/student/exams").status_code == 403
    assert (
        teacher.post(
            "/api/courses", json={"name": "X"}, headers={"X-OpenBook-Request": ""}
        ).status_code
        == 403
    )
    course = teacher.post("/api/courses", json={"name": "Mathematics"}).json()["id"]
    root = f"/api/courses/{course}"
    assert other.get(root).status_code == 404
    assert other.post(root + "/enroll", json={"username": "learner"}).status_code == 404
    user = teacher.post(root + "/enroll", json={"username": "learner"}).json()[
        "student_id"
    ]
    draft = teacher.post(
        f"/api/lecturer/courses/{course}/exams", json={"title": "Parity"}
    ).json()
    path = "/api/lecturer/exams/" + str(draft["id"])
    start = "/api/student/exams/" + str(draft["id"]) + "/start"
    assert other.get(path).status_code == 404
    assert learner.get(path).status_code == 403
    assert teacher.post(path + "/publish", json={"edit_number": 1}).status_code == 422
    opens = clock[0] + timedelta(minutes=5)
    closes = opens + timedelta(hours=1)
    data = dict(
        title="Parity",
        instructions="Choose one",
        rules="Notes allowed",
        students=[user],
        questions=[QUESTION],
        duration=10,
        opens_at=opens.isoformat(),
        closes_at=closes.isoformat(),
    )

    def save(data, number):
        return teacher.put(path, json={"draft": data, "edit_number": number})

    assert (
        save(data | {"students": [outside.get("/api/me").json()["id"]]}, 1).status_code
        == 422
    )
    assert save(data | {"questions": [QUESTION | {"topics": []}]}, 1).status_code == 422
    assert save(data | {"closes_at": opens.isoformat()}, 1).status_code == 200
    assert teacher.post(path + "/publish", json={"edit_number": 2}).status_code == 422
    assert save(data, 2).status_code == 200
    assert save(data, 2).status_code == 409

    def publish_once(_):
        with client() as parallel:
            parallel.cookies.set(
                "openbook_session", teacher.cookies["openbook_session"]
            )
            return parallel.post(path + "/publish", json={"edit_number": 3}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(publish_once, range(2))) == [200, 409]
    assert learner.post(start).status_code == 409
    assert learner.get("/api/student/exams").json()[0]["availability"] == "upcoming"
    assert outside.get("/api/student/exams").json() == []
    assert outside.post(start).status_code == 404
    assert outside.get(start.removesuffix("/start")).status_code == 404
    data["rules"] = "Paper only"
    assert save(data, 4).status_code == 200
    assert learner.get(start.removesuffix("/start")).json()["rules"] == "Notes allowed"
    assert teacher.post(path + "/publish", json={"edit_number": 5}).status_code == 200
    assert save(data | {"title": "Unpublished change"}, 6).status_code == 200
    clock[0] = opens
    assert save(data, 7).status_code == 409
    assert teacher.post(path + "/publish", json={"edit_number": 7}).status_code == 409
    details = learner.get(start.removesuffix("/start")).json()
    assert details["title"] == "Parity" and details["rules"] == "Paper only"
    assert details["availability"] == "open"
    assert set(details) == {
        "title",
        "instructions",
        "rules",
        "calculator",
        "duration",
        "opens_at",
        "closes_at",
        "id",
        "availability",
    }
    cookie = learner.cookies.get("openbook_session")

    def begin(_):
        with client() as parallel:
            parallel.cookies.set("openbook_session", cookie)
            response = parallel.post(start)
            assert response.status_code == 200, response.text
            return response.json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        attempts = list(pool.map(begin, range(4)))
    assert all(a == attempts[0] for a in attempts)
    assert set(attempts[0]) == {"id", "started_at", "deadline", "questions"}
    assert attempts[0]["questions"] == [
        {"stem": QUESTION["stem"], "options": QUESTION["options"]}
    ]
    with get_engine().connect() as db:
        assert one(db, "SELECT count(*) AS n FROM exam_attempt")["n"] == 1
        old = one(db, "SELECT snapshot FROM exam_version WHERE number=1")["snapshot"]
        assert old["rules"] == "Notes allowed"
    clock[0] = opens + timedelta(minutes=10)
    assert learner.post(start).status_code == 409
    clock[0] = closes
    assert learner.get("/api/student/exams").json()[0]["availability"] == "closed"
    assert learner.post(start).status_code == 409
    assert learner.post("/api/logout").status_code == 200
    with client() as replay:
        replay.cookies.set("openbook_session", cookie)
        assert replay.get("/api/me").status_code == 401
