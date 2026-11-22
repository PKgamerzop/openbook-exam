import json
import os
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import website as website
from test_references import dataset as dataset
from test_references import login

from app import assistance
from app.demo import COURSE, TITLES, USERS


@pytest.fixture(autouse=True)
def reset_limit():
    assistance.requests.clear()
    yield
    assistance.requests.clear()


def test_roles_disabled_mock_and_rate_limit(dataset, monkeypatch):
    demo, password, clock = dataset
    a, b = demo["exams"]
    root = f"/api/lecturer/exams/{b}/assistance"
    teacher = login(USERS[0], password)
    other = login("other", password)
    student = login(USERS[3], password)
    monkeypatch.setenv("OPENBOOK_AI_PROVIDER", "disabled")
    assert teacher.get(root).json() == {"provider": "disabled"}
    assert (
        teacher.post(root + "/scenario", json={"topic": "Query plans"}).status_code
        == 503
    )
    assert other.get(root).status_code == 404
    assert student.get(root).status_code == 403
    assert teacher.get(f"/api/lecturer/exams/{a}/assistance").status_code == 409
    monkeypatch.setenv("OPENBOOK_AI_PROVIDER", "mock")
    path = f"/api/lecturer/exams/{b}"
    before = teacher.get(path).json()
    for _ in range(2):
        result = teacher.post(root + "/review", json={"position": 0}).json()
        assert (
            result["provider"] == "mock"
            and result["edit_number"] == before["edit_number"]
        )
        assert result["suggestions"][0]["proposed_stem"]
    for _ in range(2):
        assert teacher.post(
            root + "/scenario", json={"topic": "Query plans"}
        ).is_success
    assert (
        teacher.post(root + "/scenario", json={"topic": "Query plans"}).status_code
        == 429
    )
    assert teacher.get(path).json() == before
    clock[0] += timedelta(days=2)
    assert teacher.post(root + "/review", json={"position": 0}).status_code == 409


@pytest.mark.parametrize(
    "failure", [None, TimeoutError(), ValueError(), {"output": [{}]}]
)
def test_provider_isolation_and_errors(dataset, monkeypatch, failure):
    demo, password, _ = dataset
    root = f"/api/lecturer/exams/{demo['exams'][1]}/assistance"
    monkeypatch.setenv("OPENBOOK_AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENBOOK_AI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "local-test-value")
    teacher = login(USERS[0], password)

    class FakeProvider:
        def open(self, req, timeout):
            message = json.loads(req.data)
            assert message["store"] is False and message["max_output_tokens"] == 1600
            assert timeout == 12
            content = json.loads(message["input"])["authoring"]
            assert set(content) == {
                "stem",
                "options",
                "correct",
                "topics",
                "objectives",
            }
            assert "demo_student" not in json.dumps(content)
            if isinstance(failure, Exception):
                raise failure
            data = failure or {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": '{"suggestions":[{"unexpected":"failure"}]}',
                            }
                        ],
                    }
                ],
            }
            return BytesIO(json.dumps(data).encode())

    monkeypatch.setattr(assistance, "build_opener", lambda *_: FakeProvider())
    assert teacher.post(root + "/review", json={"position": 0}).status_code == 503


@pytest.mark.skipif(os.getenv("OPENBOOK_TEST_BROWSER") != "1", reason="Requires Chrome")
def test_mock_browser(dataset, website, monkeypatch):
    _, password, _ = dataset
    monkeypatch.setenv("OPENBOOK_AI_PROVIDER", "mock")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 850})
        page.goto(website)

        def button(name):
            return page.get_by_role("button", name=name, exact=True)

        page.get_by_label("Username", exact=True).fill(USERS[0])
        page.get_by_label("Password", exact=True).fill(password)
        button("Sign in").click()
        button(COURSE).click()
        button(TITLES[1]).click()
        page.get_by_text("Optional authoring assistance", exact=True).click()
        page.get_by_label("Topic", exact=True).fill("Join strategies")
        button("Suggest scenarios").click()
        expect(page.get_by_text("Engineering trade-off", exact=True)).to_be_visible()
        button("Review question").click()
        expect(button("Apply proposed stem")).to_be_enabled()
        if directory := os.getenv("OPENBOOK_SCREENSHOTS"):
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            page.locator(".authoring-assistance").screenshot(
                path=target / "01-mock-authoring-review.png"
            )
        expect(button("Save draft")).to_be_disabled()
        stem = page.get_by_label("Question stem").first
        original = stem.input_value()
        button("Apply proposed stem").click()
        expect(stem).to_have_value("Using the assumptions given, " + original)
        expect(button("Save draft")).to_be_enabled()
        button("Save draft").click()
        expect(page.get_by_text("Draft saved", exact=True)).to_be_visible()
        browser.close()
