"""Measure synthetic staging only. Run each cohort once on its reserved exams."""

import argparse
import json
import math
import ssl
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from http.client import HTTPException, HTTPSConnection
from http.cookies import SimpleCookie
from pathlib import Path
from threading import Barrier, BrokenBarrierError, Lock
from time import perf_counter
from urllib.parse import urlsplit

KEYS = (0, 1, 0, 1, 0, 0, 0, 1, 0, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://localhost:8443")
    parser.add_argument("--ca", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, choices=(30, 60), required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--password-stdin", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlsplit(args.origin)
    if parsed.scheme != "https" or parsed.hostname != "localhost" or args.rounds < 1:
        parser.error("Use isolated localhost HTTPS staging and a positive round count.")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    tls = ssl.create_default_context(cafile=str(args.ca))
    password = input() if args.password_stdin else getpass("Synthetic pilot password: ")
    timings = defaultdict(list)
    mutex = Lock()
    ready = Barrier(args.concurrency, timeout=30)

    def session(name):
        connection = HTTPSConnection(
            parsed.hostname,
            parsed.port,
            context=tls,
            timeout=30,
            source_address=("127.0.0.1", 0),
        )
        cookie = SimpleCookie()
        call(
            (connection, cookie),
            "POST",
            "/login",
            {"username": name, "password": password},
        )
        return connection, cookie

    def call(
        client, method, route, body=None, *, measure=None, expect=200, headers=None
    ):
        connection, cookie = client
        started = perf_counter()
        request_headers = {
            "X-OpenBook-Request": "1",
            "Content-Type": "application/json",
        } | (headers or {})
        if "openbook_session" in cookie:
            request_headers["Cookie"] = (
                "openbook_session=" + cookie["openbook_session"].coded_value
            )
        connection.request(
            method,
            "/api" + route,
            body=json.dumps(body).encode() if body is not None else None,
            headers=request_headers,
        )
        with connection.getresponse() as response:
            raw = response.read()
            code = response.status
            is_json = response.headers.get_content_type() == "application/json"
            if value := response.getheader("Set-Cookie"):
                cookie.load(value)
        if measure:
            with mutex:
                timings[measure].append((perf_counter() - started, code == expect))
        if code != expect:
            raise RuntimeError(
                f"{measure or method} expected {expect}, received {code}"
            )
        return json.loads(raw) if is_json else raw

    teacher = session("pilot_lecturer")
    students = [
        session(f"pilot_student_{i:02}") for i in range(1, args.concurrency + 1)
    ]
    exams = [
        manifest["exams"][f"load{args.concurrency}-{group}"] for group in ("a", "b")
    ]

    def learner(i, client):
        eid, other = exams[i % 2], exams[1 - i % 2]
        exam = f"/student/exams/{eid}"
        attempt = exam + "/attempt"
        refs = exam + "/references"
        ready.wait()
        first = call(client, "POST", exam + "/start", measure="start")
        current = call(client, "GET", attempt, measure="navigation")
        assert current["revision"] == 0, "Use a fresh reserved examination."
        assert current["id"] == first["id"]
        assert all(set(q) == {"stem", "options"} for q in first["questions"])
        documents = call(client, "GET", refs)
        doc_ids = {d["id"] for d in documents}
        document = documents[0]["id"]
        foreign_doc = manifest["versions"][0 if i % 2 else 2]
        call(
            client,
            "GET",
            f"/student/exams/{other}/attempt",
            expect=404,
            measure="isolation",
        )
        call(
            client,
            "GET",
            f"{refs}/{foreign_doc}/file",
            expect=404,
            headers={"Range": "bytes=0-1023"},
            measure="isolation",
        )
        responses = {}
        for iteration in range(args.rounds):
            pos = iteration % len(KEYS)
            answer = KEYS[pos] if (i + iteration) % 2 == 0 else 1 - KEYS[pos]
            edit = {"answer": answer, "flagged": iteration % 3 == 0}
            current = call(
                client,
                "PUT",
                f"{attempt}/questions/{pos}",
                edit | {"revision": current["revision"]},
                measure="save",
            )
            responses[str(pos)] = edit
            fresh = call(client, "GET", attempt, measure="navigation")
            assert fresh["responses"] == responses
            search = call(
                client,
                "GET",
                refs + "/search?q=" + ("dependency" if i % 2 else "leaf"),
                measure="search",
            )
            assert search and all(hit["id"] in doc_ids for hit in search)
            pdf = call(
                client,
                "GET",
                f"{refs}/{document}/file",
                expect=206,
                headers={"Range": "bytes=0-1023"},
                measure="pdf_range",
            )
            assert pdf.startswith(b"%PDF-")
        final = call(
            client,
            "POST",
            attempt + "/submit",
            {"revision": current["revision"]},
            measure="submit",
        )
        replay = call(
            client,
            "POST",
            attempt + "/submit",
            {"revision": 0},
            measure="submit_replay",
        )
        assert final["responses"] == responses and final["final_reason"] == "submitted"
        for key in ("id", "finalized_at", "responses"):
            assert replay[key] == final[key]
        grade = sum(edit["answer"] == KEYS[int(pos)] for pos, edit in responses.items())
        return i, eid, first["id"], grade

    started = perf_counter()
    failures = []
    completions = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(learner, i, client) for i, client in enumerate(students)]
        for future in futures:
            try:
                completions.append(future.result())
            except (
                AssertionError,
                BrokenBarrierError,
                KeyError,
                OSError,
                RuntimeError,
                HTTPException,
                ValueError,
            ) as exc:
                failures.append(type(exc).__name__ + ": " + str(exc))
    duration = perf_counter() - started
    expected = {(eid, attempt): score for _, eid, attempt, score in completions}
    for eid in exams:
        result = call(teacher, "GET", f"/lecturer/exams/{eid}/results")
        for student in result["students"]:
            attempt = student["attempt_id"]
            if expected.pop((eid, attempt), None) != student["score"]:
                failures.append("Lecturer grade verification mismatch")
    if expected or len({row[2] for row in completions}) != len(completions):
        failures.append("Unexpected number of unique finalized attempts")
    counts = sum(len(samples) for samples in timings.values())
    summary = {}
    for name, samples in timings.items():
        durations = sorted(t for t, _ in samples)
        summary[name] = {
            "requests": len(samples),
            "errors": sum(not ok for _, ok in samples),
            **{
                f"p{p}_ms": round(
                    durations[math.ceil(len(samples) * p / 100) - 1] * 1000, 1
                )
                for p in (50, 95, 99)
            },
        }
    report = {
        "sessions": args.concurrency,
        "rounds": args.rounds,
        "completed_and_checked": len(completions),
        "seconds": round(duration, 2),
        "measured_requests_per_second": round(counts / duration, 1),
        "measurements": summary,
        "failures": failures,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for connection, _ in [teacher, *students]:
        connection.close()
    print(json.dumps(report, indent=2))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
