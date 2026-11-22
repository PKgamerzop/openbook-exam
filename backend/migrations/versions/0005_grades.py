"""Persist deterministic assessment and version-scoped release."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE attempt_grade (
            attempt_id integer PRIMARY KEY REFERENCES exam_attempt(id),
            score integer NOT NULL CHECK(score>=0),
            maximum integer NOT NULL CHECK(maximum>0),
            incorrect integer NOT NULL CHECK(incorrect>=0),
            unanswered integer NOT NULL CHECK(unanswered>=0),
            assessment jsonb NOT NULL,
            graded_at timestamptz NOT NULL DEFAULT now(),
            CHECK(score+incorrect+unanswered=maximum),
            CHECK(jsonb_array_length(assessment)=maximum)
        );
        CREATE TABLE exam_result_release (
            exam_id integer,
            version integer,
            actor_id integer NOT NULL REFERENCES account(id),
            released_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY(exam_id,version),
            FOREIGN KEY(exam_id,version) REFERENCES exam_version(exam_id,number)
        );
        CREATE FUNCTION grade_mcqs(questions jsonb,responses jsonb)
        RETURNS TABLE(score integer,maximum integer,incorrect integer,
                      unanswered integer,assessment jsonb)
        LANGUAGE sql IMMUTABLE AS $$
            WITH answer AS (
                SELECT ord-1 AS position, (q->>'correct')::integer AS correct,
                    (responses->((ord-1)::text)->>'answer')::integer AS selected
                FROM jsonb_array_elements(questions) WITH ORDINALITY AS q(q,ord)
            ), outcome AS (
                SELECT *, CASE WHEN selected IS NULL THEN 'unanswered'
                    WHEN selected=correct THEN 'correct' ELSE 'incorrect' END AS status
                FROM answer
            )
            SELECT count(*) FILTER (WHERE status='correct')::integer,
                   count(*)::integer,
                   count(*) FILTER (WHERE status='incorrect')::integer,
                   count(*) FILTER (WHERE status='unanswered')::integer,
                   coalesce(jsonb_agg(jsonb_build_object(
                       'position',position,'selected',selected,'outcome',status
                   ) ORDER BY position),'[]'::jsonb)
            FROM outcome;
        $$;
        CREATE FUNCTION record_finalized_grade() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO attempt_grade(attempt_id,score,maximum,incorrect,
                                      unanswered,assessment)
            SELECT NEW.id,g.* FROM exam_version v
            CROSS JOIN LATERAL grade_mcqs(v.snapshot->'questions',NEW.responses) g
            WHERE (v.exam_id,v.number)=(NEW.exam_id,NEW.version)
            ON CONFLICT (attempt_id) DO NOTHING;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER grade_finalized_attempt
        AFTER INSERT OR UPDATE OF finalized_at ON exam_attempt
        FOR EACH ROW WHEN (NEW.finalized_at IS NOT NULL)
        EXECUTE FUNCTION record_finalized_grade();
        INSERT INTO attempt_grade(attempt_id,score,maximum,incorrect,
                                  unanswered,assessment)
        SELECT a.id,g.* FROM exam_attempt a JOIN exam_version v
        ON (v.exam_id,v.number)=(a.exam_id,a.version)
        CROSS JOIN LATERAL grade_mcqs(v.snapshot->'questions',a.responses) g
        WHERE a.finalized_at IS NOT NULL
        ON CONFLICT (attempt_id) DO NOTHING;
    """)


def downgrade():
    op.execute("""
        DROP TRIGGER grade_finalized_attempt ON exam_attempt;
        DROP FUNCTION record_finalized_grade();
        DROP FUNCTION grade_mcqs(jsonb,jsonb);
        DROP TABLE exam_result_release, attempt_grade;
    """)
