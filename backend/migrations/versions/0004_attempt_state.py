"""Persist timed examination state without modifying frozen revisions."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE exam_attempt
            ADD COLUMN responses jsonb NOT NULL DEFAULT '{}',
            ADD COLUMN scratchpad text NOT NULL DEFAULT '',
            ADD COLUMN state_revision integer NOT NULL DEFAULT 0,
            ADD COLUMN finalized_at timestamptz,
            ADD COLUMN final_reason text CHECK(final_reason IN ('submitted','expired')),
            ADD CHECK ((finalized_at IS NULL) = (final_reason IS NULL));
        CREATE TABLE exam_page_mark (
            exam_id integer NOT NULL,
            revision integer NOT NULL,
            student_id integer NOT NULL,
            version_id integer NOT NULL,
            page integer NOT NULL CHECK (page > 0),
            name text NOT NULL DEFAULT '',
            pinned boolean NOT NULL DEFAULT false,
            PRIMARY KEY (exam_id,revision,student_id,version_id,page),
            FOREIGN KEY (exam_id,revision,student_id) REFERENCES exam_assignment,
            FOREIGN KEY (exam_id,revision,version_id) REFERENCES exam_reference
        );
        CREATE INDEX pending_attempt_deadline ON exam_attempt(deadline)
            WHERE finalized_at IS NULL;
    """)


def downgrade():
    op.execute("""
        DROP TABLE exam_page_mark;
        DROP INDEX pending_attempt_deadline;
        ALTER TABLE exam_attempt DROP COLUMN responses, DROP COLUMN scratchpad,
            DROP COLUMN state_revision, DROP COLUMN finalized_at,
            DROP COLUMN final_reason;
    """)
