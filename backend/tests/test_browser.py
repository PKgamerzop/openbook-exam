import os
import socket
from datetime import timedelta
from pathlib import Path
from threading import Thread

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright
from starlette.staticfiles import StaticFiles

from app.demo import COURSE, TITLES, USERS, seed
from app.demo_fixtures import fixture
from app.main import app


@pytest.fixture
def website():
    assets = StaticFiles(directory=Path("../frontend/dist"), html=True)

    async def website_app(scope, receive, send):
        handler = app if scope["path"].startswith("/api/") else assets
        await handler(scope, receive, send)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        config = uvicorn.Config(website_app, lifespan="off", log_level="warning")
        server = uvicorn.Server(config)
        thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{sock.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=5)


@pytest.mark.skipif(
    os.getenv("OPENBOOK_TEST_BROWSER") != "1",
    reason="Requires built frontend and Chrome",
)
def test_lecturer_to_student(pilot, website):
    password, clock = pilot
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(timezone_id="UTC")
        page.goto(website)

        def button(name):
            return page.get_by_role("button", name=name, exact=True)

        def login(name):
            page.get_by_label("Username", exact=True).fill(name)
            page.get_by_label("Password", exact=True).fill(password)
            button("Sign in").click()

        login("teacher")
        page.get_by_label("Course name").fill("Mathematics")
        button("Create course").click()
        page.get_by_label("Student username").fill("learner")
        button("Enroll student").click()
        expect(page.get_by_text("learner", exact=True)).to_be_visible()
        page.get_by_label("New exam title").fill("Parity")
        button("Create draft").click()
        page.get_by_label("Instructions").fill("Choose one option.")
        page.get_by_label("Permitted resources and rules").fill("Paper notes only.")
        page.get_by_label("Opens (local time)").fill("2035-01-01T12:01")
        page.get_by_label("Closes (local time)").fill("2035-01-01T13:00")
        page.get_by_label("Duration in minutes").fill("10")
        page.get_by_label("learner", exact=True).check()
        button("Add question").click()
        page.get_by_label("Question stem").fill("Which number is even?")
        page.get_by_label("Option 1", exact=True).fill("Three")
        page.get_by_label("Option 2", exact=True).fill("Four")
        page.get_by_label("Correct option 2").check()
        button("Save draft").click()
        expect(page.get_by_role("alert")).to_contain_text("topics")
        page.get_by_label("Topics (required, comma-separated)").fill("Parity")
        button("Save draft").click()
        expect(page.get_by_text("Draft saved", exact=True)).to_be_visible()
        page.get_by_text("Preview draft", exact=True).click()
        expect(page.get_by_text("Four (correct)", exact=True)).to_be_visible()
        button("Validate and publish").click()
        expect(page.get_by_text("View published exam", exact=True)).to_be_visible()
        button("Sign out").click()
        login("learner")
        button("Parity").click()
        expect(button("Start or resume attempt")).to_be_disabled()
        clock[0] += timedelta(minutes=1)
        button("Refresh availability").click()
        button("Start or resume attempt").click()
        expect(page.get_by_text("Which number is even?", exact=True)).to_be_visible()
        expect(page.get_by_text("Four", exact=True)).to_be_visible()
        expect(page.get_by_text("Four (correct)", exact=True)).to_have_count(0)
        browser.close()


@pytest.mark.skipif(os.getenv("OPENBOOK_TEST_BROWSER") != "1", reason="Requires Chrome")
def test_reference_browser(pilot, website, monkeypatch, tmp_path):
    password, _ = pilot
    monkeypatch.setenv("OPENBOOK_PDF_DIR", str(tmp_path))
    seed(lambda: password)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.goto(website)

        def button(name):
            return page.get_by_role("button", name=name, exact=True)

        def login(name):
            page.get_by_label("Username", exact=True).fill(name)
            page.get_by_label("Password", exact=True).fill(password)
            button("Sign in").click()

        login(USERS[0])
        button(COURSE).click()
        button("Reference Library").click()
        button("Preview Scan").click()
        expect(page.get_by_label("Scan, page 1")).to_be_visible()
        page.get_by_label("PDF file").set_input_files(
            dict(
                name="browser-upload.pdf",
                mimeType="application/pdf",
                buffer=fixture("transactions-guide"),
            )
        )
        button("Upload PDF").click()
        button("Preview browser-upload").click()
        expect(page.get_by_label("browser-upload, page 1")).to_be_visible()
        button("Sign out").click()
        login(USERS[5])
        button(TITLES[0]).click()
        button("Start or resume attempt").click()
        page.get_by_label("Search all permitted PDFs").fill("deadlock")
        button("Search references").click()
        button("Transactions Guide · page 2").click()
        canvas = page.get_by_label("Transactions Guide, page 2")
        expect(canvas).to_be_visible()
        assert canvas.evaluate("""c => c.getContext('2d').getImageData(
            0,0,c.width,c.height).data.some((v,i)=>i%4===0 && v<128)""")
        button("Previous page").click()
        expect(page.get_by_label("Transactions Guide, page 1")).to_be_visible()
        browser.close()
