BEGIN;
SET LOCAL search_path TO remi_project;
CREATE TABLE web_tokens (
    digest bytea PRIMARY KEY, student_id integer NOT NULL REFERENCES students,
    expires_at timestamptz NOT NULL
);
ALTER TABLE moderators ADD COLUMN student_id integer UNIQUE REFERENCES students;
ALTER TABLE questions ADD COLUMN pilot_phase text CHECK (pilot_phase IN ('initial','retake'));
ALTER TABLE diagnostic_sessions ADD COLUMN pilot_slug text,
    ADD COLUMN retake_skill integer REFERENCES competencies, ADD COLUMN pilot_rules jsonb;
CREATE UNIQUE INDEX active_pilot ON diagnostic_sessions(student_id,pilot_slug)
    WHERE status='in_progress' AND pilot_slug IS NOT NULL;
CREATE TABLE pilot_issues (
    session_id integer NOT NULL, student_id integer NOT NULL,
    question_id integer NOT NULL, question_version_id integer NOT NULL,
    answer_id integer UNIQUE REFERENCES student_answers, withdrawn boolean NOT NULL DEFAULT false,
    PRIMARY KEY(student_id,question_id),
    FOREIGN KEY(session_id,student_id) REFERENCES diagnostic_sessions(session_id,student_id),
    FOREIGN KEY(question_id,question_version_id) REFERENCES question_versions(question_id,question_version_id)
);
CREATE INDEX pilot_issues_session ON pilot_issues(session_id);
CREATE TABLE course_sections (
    resource_id integer PRIMARY KEY REFERENCES learning_resources,
    course_id integer NOT NULL REFERENCES learning_resources,
    vector real[], encoder text
);
CREATE VIEW approved_pilot_questions AS
SELECT v.*, q.pilot_phase, q.difficulty
FROM questions q JOIN question_versions v USING(question_id)
WHERE q.pilot_phase IS NOT NULL AND q.validation_status='approved'
  AND v.version_number=(SELECT max(n.version_number) FROM question_versions n WHERE n.question_id=q.question_id)
  AND (SELECT decision FROM question_reviews r WHERE r.question_version_id=v.question_version_id
       ORDER BY r.review_id DESC LIMIT 1)='approved';
COMMIT;

