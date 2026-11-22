from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from test_references import dataset as dataset
from test_references import login

from app.attempt_expiry import expire_batch
from app.demo import USERS


def test_workspace_state_and_submission(dataset):
    demo, password, clock = dataset
    exam = f"/api/student/exams/{demo['exams'][0]}"
    endpoint = exam + "/attempt"
    owner = login(USERS[1], password)
    outsider = login(USERS[2], password)
    assert owner.post(exam + "/start").is_success
    assert outsider.get(endpoint).status_code == 404
    initial = owner.get(endpoint).json()
    assert set(initial["questions"][0]) == {"stem", "options"}
    edit = dict(revision=0, answer=0, flagged=True)
    saved = owner.put(endpoint + "/questions/0", json=edit).json()
    assert saved["revision"] == 1
    assert owner.put(endpoint + "/questions/0", json=edit).status_code == 409
    clear = owner.put(
        endpoint + "/questions/0", json=edit | dict(revision=1, answer=None)
    )
    assert clear.json()["responses"]["0"] == {"answer": None, "flagged": True}
    scratch = owner.put(
        endpoint + "/scratchpad", json=dict(revision=2, scratchpad="Notes")
    )
    assert scratch.json()["revision"] == 3
    assert owner.get(endpoint).json()["scratchpad"] == "Notes"
    final = owner.post(endpoint + "/submit", json={"revision": 3}).json()
    assert final["final_reason"] == "submitted"
    assert owner.post(endpoint + "/submit", json={"revision": 0}).json() == final
    assert owner.get(exam + "/references").status_code == 403
    assert (
        owner.put(
            endpoint + "/scratchpad", json=dict(revision=3, scratchpad="x")
        ).status_code
        == 409
    )
    assert outsider.post(exam + "/start").is_success
    clock[0] += timedelta(hours=3)
    assert expire_batch() == 1
    assert expire_batch() == 0
    assert outsider.get(endpoint).json()["final_reason"] == "expired"


def test_marks_and_finalize_race(dataset):
    demo, password, _ = dataset
    a, b = [f"/api/student/exams/{eid}" for eid in demo["exams"]]
    owner = login(USERS[5], password)
    v = demo["versions"][2]
    marks = b + "/references/marks"
    assert owner.put(marks + f"/{v}/99", json={}).status_code == 404
    assert owner.put(marks + f"/{demo['versions'][0]}/1", json={}).status_code == 404
    assert owner.put(
        marks + f"/{v}/2", json={"name": "Example", "pinned": True}
    ).is_success
    assert owner.get(marks).json() == [
        dict(name="Example", pinned=True, version_id=v, page=2)
    ]
    assert owner.delete(marks + f"/{v}/2").is_success
    assert owner.get(marks).json() == []
    assert owner.post(a + "/start").is_success
    endpoint = a + "/attempt"
    second_tab = login(USERS[5], password)
    with ThreadPoolExecutor(max_workers=2) as pool:
        save = pool.submit(
            owner.put,
            endpoint + "/questions/0",
            json=dict(revision=0, answer=1, flagged=False),
        )
        submit = pool.submit(
            second_tab.post, endpoint + "/submit", json=dict(revision=0)
        )
    assert sorted([save.result().status_code, submit.result().status_code]) == [
        200,
        409,
    ]
    state = owner.get(endpoint).json()
    if save.result().is_success:
        assert state["final_reason"] is None and state["responses"]["0"]["answer"] == 1
    else:
        assert state["final_reason"] == "submitted" and state["responses"] == {}
