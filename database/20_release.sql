BEGIN;
SET LOCAL search_path=remi_project,pg_catalog;
CREATE TABLE IF NOT EXISTS graph_reviews (
 review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, slug text NOT NULL, fingerprint text NOT NULL,
 moderator_id integer NOT NULL REFERENCES moderators, approved boolean NOT NULL, reviewed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS profile_recovery (
 digest bytea PRIMARY KEY, student_id integer NOT NULL REFERENCES students, expires_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS release_catalog (version integer PRIMARY KEY, seeded_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS mastery_owner_skill ON mastery_estimates(student_id,competency_id,estimate_id DESC);
INSERT INTO catalog_migrations(version) VALUES(20) ON CONFLICT DO NOTHING;
COMMIT;
