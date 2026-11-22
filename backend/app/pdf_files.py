"""Private storage and bounded, isolated PDF parsing."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import UUID

import psutil
from pypdf import PdfReader


def path_for(key):
    root = Path(
        os.getenv(
            "OPENBOOK_PDF_DIR", Path(__file__).resolve().parents[2] / ".private-pdfs"
        )
    ).resolve()
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    if root.is_relative_to(frontend):
        raise ValueError("PDF storage must be private")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = root / str(UUID(str(key)))
    if path.resolve().parent != root or path.is_symlink():
        raise ValueError("Invalid private file")
    return path


def parse(path, extract):
    """Run in a child process. Serialize only bounded output to the parent."""
    logging.disable(logging.CRITICAL)
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError()
        reader = PdfReader(stream, strict=True)
        if reader.is_encrypted:
            raise ValueError()
        count = len(reader.pages)
        if not 1 <= count <= int(os.getenv("OPENBOOK_PDF_MAX_PAGES", "200")):
            raise ValueError()
        if not extract:
            return count
        pages = []
        total = 0
        for page in reader.pages:
            content = (page.extract_text() or "").replace(chr(0), "").strip()
            total += len(content)
            if len(content) > 100000 or total > 2000000:
                raise ValueError()
            pages.append(content)
        return pages


def inspect_pdf(path, extract=False):
    deadline = time.monotonic() + 30
    with tempfile.TemporaryFile() as output:
        with subprocess.Popen(
            [sys.executable, __file__, str(path), "text" if extract else "count"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.DEVNULL,
        ) as child:
            monitor = psutil.Process(child.pid)
            try:
                while child.poll() is None:
                    try:
                        if monitor.memory_info().rss > 384 * 1024**2:
                            raise ValueError("PDF processing limit exceeded")
                    except psutil.NoSuchProcess:
                        break
                    if time.monotonic() >= deadline:
                        raise ValueError("PDF processing limit exceeded")
                    time.sleep(0.02)
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait()
            if child.returncode:
                raise ValueError("Invalid or unsupported PDF")
        output.seek(0)
        return json.load(output)


if __name__ == "__main__":
    data = parse(Path(sys.argv[1]), sys.argv[2] == "text")
    sys.stdout.buffer.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
