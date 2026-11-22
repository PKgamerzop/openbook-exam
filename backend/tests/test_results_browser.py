import os

import pytest
from playwright.sync_api import expect, sync_playwright
from test_browser import screenshot
from test_browser import website as website
from test_references import dataset as dataset

from app.demo import COURSE, USERS
from app.results_demo import TITLES, seed_results


@pytest.mark.skipif(os.getenv("OPENBOOK_TEST_BROWSER") != "1", reason="Requires Chrome")
def test_result_release_browser(dataset, website):
    _, password, _ = dataset
    seed_results()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1280, "height": 850})
        page.goto(website)

        def button(name):
            return page.get_by_role("button", name=name, exact=True)

        def login(name):
            page.get_by_label("Username", exact=True).fill(name)
            page.get_by_label("Password", exact=True).fill(password)
            button("Sign in").click()

        login(USERS[1])
        button(TITLES[1]).click()
        page.get_by_text("My results", exact=True).click()
        expect(
            page.get_by_text("Attempt submitted. Results await release.")
        ).to_be_visible()
        expect(page.get_by_text("Correct option:", exact=False)).to_have_count(0)
        button("Sign out").click()
        login(USERS[0])
        button(COURSE).click()
        button(TITLES[1]).click()
        button("View exam results").click()
        expect(page.get_by_text("Score distribution", exact=True)).to_be_visible()
        screenshot(page, "01-lecturer-results")
        button(USERS[1]).click()
        expect(page.get_by_text("5/5 (100%)", exact=True)).to_be_visible()
        button("Release results").click()
        expect(page.get_by_role("dialog")).to_be_visible()
        screenshot(page, "02-release-confirmation")
        button("Confirm result release").click()
        expect(page.get_by_text("Released ", exact=False).first).to_be_visible()
        button("Sign out").click()
        login(USERS[1])
        button(TITLES[1]).click()
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_text("My results", exact=True).click()
        expect(page.get_by_text("5/5 (100%)", exact=True)).to_be_visible()
        expect(page.get_by_text("Correct option:", exact=False)).to_have_count(5)
        screenshot(page, "03-student-feedback-mobile")
        browser.close()
