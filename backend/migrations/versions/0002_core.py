"""Create pilot accounts, course rosters, exam drafts and published revisions."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE account (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            username text UNIQUE NOT NULL,
            password_hash text NOT NULL,
            role text NOT NULL CHECK (role IN ('student','lecturer'))
        );
        CREATE TABLE login_session (
            digest text PRIMARY KEY, user_id integer NOT NULL REFERENCES account,
            expires_at timestamptz NOT NULL
        );
        CREATE INDEX session_expiry ON login_session(expires_at);
        CREATE TABLE course (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            owner_id integer NOT NULL REFERENCES account, name text NOT NULL,
            UNIQUE (owner_id, name)
        );
        CREATE TABLE enrollment (
            course_id integer REFERENCES course, student_id integer REFERENCES account,
            PRIMARY KEY (course_id,student_id)
        );
        CREATE TABLE classification (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            course_id integer NOT NULL REFERENCES course,
            kind text NOT NULL CHECK (kind IN ('topic','objective')),
            name text NOT NULL,
            UNIQUE (course_id,kind,name)
        );
        CREATE TABLE exam (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            course_id integer NOT NULL REFERENCES course, draft jsonb NOT NULL,
            edit_number integer NOT NULL DEFAULT 1,
            published_number integer
        );
        CREATE INDEX exam_course ON exam(course_id);
        CREATE TABLE exam_version (
            exam_id integer REFERENCES exam, number integer NOT NULL,
            opens_at timestamptz NOT NULL, closes_at timestamptz NOT NULL,
            snapshot jsonb NOT NULL, CHECK (opens_at < closes_at),
            PRIMARY KEY (exam_id,number)
        );
        ALTER TABLE exam ADD FOREIGN KEY (id,published_number)
            REFERENCES exam_version(exam_id,number);
        CREATE TABLE exam_assignment (
            exam_id integer, version integer, student_id integer REFERENCES account,
            PRIMARY KEY (exam_id,version,student_id),
            FOREIGN KEY (exam_id,version) REFERENCES exam_version
        );
        CREATE INDEX student_exam ON exam_assignment(student_id,exam_id);
        CREATE TABLE exam_attempt (
            id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            exam_id integer NOT NULL, version integer NOT NULL,
            student_id integer NOT NULL, started_at timestamptz NOT NULL,
            deadline timestamptz NOT NULL CHECK (deadline > started_at),
            UNIQUE (exam_id,student_id),
            FOREIGN KEY (exam_id,version,student_id) REFERENCES exam_assignment
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE exam_attempt, exam_assignment, exam_version, exam,
            classification, enrollment, course, login_session, account;
    """)
