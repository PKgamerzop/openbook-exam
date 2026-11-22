"""Add private course references and revision permissions."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE reference_document (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            course_id integer NOT NULL REFERENCES course,
            folder text NOT NULL, topics text[] NOT NULL DEFAULT '{}'
        );
        CREATE INDEX library_course ON reference_document(course_id);
        CREATE TABLE reference_version (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            document_id integer NOT NULL REFERENCES reference_document,
            number integer NOT NULL, storage_key uuid NOT NULL UNIQUE,
            filename text NOT NULL, title text NOT NULL,
            size integer NOT NULL CHECK(size>0), pages integer NOT NULL CHECK(pages>0),
            created_at timestamptz NOT NULL DEFAULT now(),
            status text NOT NULL DEFAULT 'processing'
                CHECK(status IN ('processing','searchable','view-only','failed')),
            UNIQUE(document_id,number)
        );
        CREATE TABLE reference_job (
            version_id integer PRIMARY KEY REFERENCES reference_version,
            token uuid, lease_until timestamptz
        );
        CREATE TABLE reference_page (
            version_id integer REFERENCES reference_version,
            page integer CHECK(page>0), content text NOT NULL,
            vector tsvector GENERATED ALWAYS AS
                (to_tsvector('simple'::regconfig, content)) STORED,
            PRIMARY KEY(version_id,page)
        );
        CREATE INDEX reference_search ON reference_page USING gin(vector);
        CREATE TABLE exam_reference (
            exam_id integer, revision integer,
            version_id integer REFERENCES reference_version,
            PRIMARY KEY(exam_id,revision,version_id),
            FOREIGN KEY(exam_id,revision) REFERENCES exam_version
        );
    """)


def downgrade():
    op.execute("""
        DROP TABLE exam_reference, reference_page, reference_job,
            reference_version, reference_document;
    """)
