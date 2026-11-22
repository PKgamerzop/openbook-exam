FROM python:3.14.10-slim-bookworm@sha256:3fe1a0b6c2d6b2ebb572906cdabeca75aeb558c0c17db5ffefbcf8094871c32b AS dependencies
WORKDIR /build
COPY requirements.txt constraints.production.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt -c constraints.production.txt

FROM python:3.14.10-slim-bookworm@sha256:3fe1a0b6c2d6b2ebb572906cdabeca75aeb558c0c17db5ffefbcf8094871c32b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBOOK_CONTAINER_DEPLOYMENT=1
WORKDIR /srv/openbook
COPY --from=dependencies /install /usr/local
RUN groupadd --gid 10001 openbook && useradd --uid 10001 --gid 10001 --no-create-home openbook \
    && install -d -m 0700 -o openbook -g openbook /private-pdfs
COPY app ./app
COPY alembic.ini .
COPY migrations ./migrations
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]
