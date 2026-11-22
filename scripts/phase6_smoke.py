"""Verify trusted HTTPS and preserved synthetic data on staging or restore."""

import argparse
import hashlib
import json
import re
import ssl
from getpass import getpass
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://localhost:8443")
    parser.add_argument("--ca", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--password-stdin", action="store_true")
    args = parser.parse_args()
    password = input() if args.password_stdin else getpass("Synthetic pilot password: ")
    data = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    context = ssl.create_default_context(cafile=str(args.ca))

    def session():
        return build_opener(
            HTTPSHandler(context=context), HTTPCookieProcessor(CookieJar())
        )

    def send(path, *, client, method="GET", body=None, status=200, headers=None):
        request = Request(
            args.origin + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "X-OpenBook-Request": "1"}
            | (headers or {}),
        )
        try:
            response = client.open(request, timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            assert response.code == status, (
                f"{method} {path}: {response.code} != {status}"
            )
            return response.read(), response.headers

    teacher, student = session(), session()
    for endpoint in ("live", "health"):
        payload, headers = send(f"/api/{endpoint}", client=teacher)
        assert json.loads(payload)["status"] == "ok"
        assert headers["Cache-Control"] == "no-store"
        assert headers["Strict-Transport-Security"]
    for client, username in (
        (teacher, "pilot_lecturer"),
        (student, "pilot_student_06"),
    ):
        _, headers = send(
            "/api/login",
            client=client,
            method="POST",
            body={"username": username, "password": password},
        )
        cookie = headers["Set-Cookie"].lower()
        assert all(v in cookie for v in ("secure", "httponly", "samesite=strict"))
    attempt = data["exams"]["rehearsal"]
    html, _ = send(f"/lecturer/exams/{attempt}", client=teacher)
    script = re.search(rb'src="(/assets/[^"]+\.js)"', html)
    assert script, "SPA fallback did not provide the production entry script"
    bundle, _ = send(script[1].decode(), client=teacher)
    assert b"Optional authoring assistance" not in bundle
    worker = re.search(rb"/assets/pdf\.worker\.min-[A-Za-z0-9_-]+\.mjs", bundle)
    assert worker, "Missing PDF.js worker bundle"
    _, headers = send(worker[0].decode(), client=teacher)
    assert "javascript" in headers["Content-Type"]
    send(f"/api/lecturer/exams/{attempt}/assistance", client=teacher, status=404)
    send(
        "/api/logout",
        client=teacher,
        method="POST",
        status=403,
        headers={"Origin": "https://other.example"},
    )
    root = f"/api/lecturer/courses/{data['course']}/references"
    reference = data["versions"][0]
    pdf, _ = send(f"{root}/{reference}/file", client=teacher)
    piece, headers = send(
        f"{root}/{reference}/file",
        client=teacher,
        status=206,
        headers={"Range": "bytes=0-1023"},
    )
    assert pdf.startswith(b"%PDF-") and piece == pdf[:1024]
    assert headers["Cache-Control"] == "no-store"
    print("Private 120-page PDF SHA-256", hashlib.sha256(pdf).hexdigest())
    for label in ("released", "unreleased"):
        eid = data["exams"][label]
        payload, _ = send(f"/api/lecturer/exams/{eid}/results", client=teacher)
        grading = json.loads(payload)
        assert bool(grading["release"]) == (label == "released")
        graded = [
            row["score"] for row in grading["students"] if row["score"] is not None
        ]
        assert sorted(graded) == [0, 1, 1, 1, 1]
    eid = data["exams"]["unreleased"]
    payload, _ = send(f"/api/student/exams/{eid}/result", client=student)
    assert "score" not in json.loads(payload)
    send("/api/logout", client=student, method="POST")
    send("/api/me", client=student, status=401)
    print(
        "HTTPS, secure session, SPA, PDF ranges, AI-disabled and grading checks passed"
    )


if __name__ == "__main__":
    main()
