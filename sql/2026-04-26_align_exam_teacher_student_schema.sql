-- Production schema alignment for teacher/student learning APIs.
-- This script intentionally patches existing overlapping tables only.
-- Demo/test INSERT statements from local should NOT be run on production.
--
-- New tables such as classrooms, classroom_memberships, learning_documents,
-- and exam_question_options are created automatically by the app startup
-- bootstrap if they do not exist yet.

BEGIN;

-- Backfill new classrooms table from legacy classes table when both exist.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'classes'
    )
    AND EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'classrooms'
    ) THEN
        INSERT INTO classrooms (id, name, description, join_code, created_by_user_id, created_at, updated_at)
        SELECT
            c.id,
            c.name,
            c.description,
            c.class_code,
            c.teacher_id,
            COALESCE(c.created_at, CURRENT_TIMESTAMP),
            COALESCE(c.updated_at, CURRENT_TIMESTAMP)
        FROM classes c
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- exams: add new columns used by current code.
ALTER TABLE exams
ADD COLUMN IF NOT EXISTS scope VARCHAR(20) NOT NULL DEFAULT 'system';

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS classroom_id INTEGER;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS duration_minutes INTEGER NOT NULL DEFAULT 30;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS total_points INTEGER NOT NULL DEFAULT 0;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS is_published BOOLEAN;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- Drop old/new check constraints first so backfill updates do not fail mid-script.
ALTER TABLE exams
DROP CONSTRAINT IF EXISTS exams_check;

ALTER TABLE exams
DROP CONSTRAINT IF EXISTS exams_scope_classroom_check;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exams' AND column_name = 'time_limit_minutes'
    ) THEN
        EXECUTE '
            UPDATE exams
            SET duration_minutes = COALESCE(time_limit_minutes, duration_minutes)
        ';
    END IF;
END $$;

UPDATE exams
SET is_published = COALESCE(is_active, FALSE)
WHERE is_published IS NULL;

ALTER TABLE exams
ALTER COLUMN is_published SET NOT NULL;

ALTER TABLE exams
ALTER COLUMN is_published SET DEFAULT FALSE;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exams' AND column_name = 'total_score'
    ) THEN
        EXECUTE '
            UPDATE exams
            SET total_points = COALESCE(CAST(total_score AS INTEGER), total_points)
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exams' AND column_name = 'status'
    ) THEN
        EXECUTE '
            UPDATE exams
            SET is_active = CASE
                WHEN status = ''published'' THEN TRUE
                WHEN status = ''draft'' THEN FALSE
                WHEN status = ''closed'' THEN FALSE
                ELSE is_active
            END
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exams' AND column_name = 'class_id'
    ) THEN
        EXECUTE '
            UPDATE exams e
            SET classroom_id = e.class_id
            WHERE e.scope = ''class''
              AND e.classroom_id IS NULL
              AND e.class_id IS NOT NULL
              AND EXISTS (
                  SELECT 1
                  FROM classrooms c
                  WHERE c.id = e.class_id
              )
        ';
    END IF;
END $$;

UPDATE exams
SET classroom_id = NULL
WHERE scope = 'system';

-- Keep any unresolved old rows untouched if they still rely on legacy data.
-- NOT VALID makes the new check apply to new rows without failing on old data.
ALTER TABLE exams
ADD CONSTRAINT exams_scope_classroom_check
CHECK (
    ((scope = 'system') AND (classroom_id IS NULL))
    OR
    ((scope = 'class') AND (classroom_id IS NOT NULL))
) NOT VALID;

-- exam_questions: add new columns and backfill from old schema.
ALTER TABLE exam_questions
ADD COLUMN IF NOT EXISTS question_type VARCHAR(30);

ALTER TABLE exam_questions
ADD COLUMN IF NOT EXISTS prompt TEXT;

ALTER TABLE exam_questions
ADD COLUMN IF NOT EXISTS image_url TEXT;

ALTER TABLE exam_questions
ADD COLUMN IF NOT EXISTS order_index INTEGER;

ALTER TABLE exam_questions
ADD COLUMN IF NOT EXISTS points INTEGER NOT NULL DEFAULT 1;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_questions' AND column_name = 'question_type'
    ) THEN
        EXECUTE '
            UPDATE exam_questions
            SET question_type = CASE
                WHEN question_type = ''text'' THEN ''text''
                ELSE ''single_choice''
            END
            WHERE question_type IS NULL OR question_type NOT IN (''single_choice'', ''text'')
        ';
    END IF;
END $$;

ALTER TABLE exam_questions
ALTER COLUMN question_type SET NOT NULL;

ALTER TABLE exam_questions
ALTER COLUMN question_type SET DEFAULT 'single_choice';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_questions' AND column_name = 'content'
    ) THEN
        EXECUTE '
            UPDATE exam_questions
            SET prompt = content
            WHERE prompt IS NULL AND content IS NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_questions' AND column_name = 'sort_order'
    ) THEN
        EXECUTE '
            UPDATE exam_questions
            SET order_index = sort_order
            WHERE order_index IS NULL AND sort_order IS NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_questions' AND column_name = 'score'
    ) THEN
        EXECUTE '
            UPDATE exam_questions
            SET points = COALESCE(CAST(score AS INTEGER), points)
            WHERE score IS NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_questions' AND column_name = 'content'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_questions
            ALTER COLUMN content DROP NOT NULL
        ';
    END IF;
END $$;

ALTER TABLE exam_question_options
ADD COLUMN IF NOT EXISTS image_url TEXT;

-- exam_attempts: add new columns and backfill from old student-based schema.
ALTER TABLE exam_attempts
ADD COLUMN IF NOT EXISTS user_id INTEGER;

ALTER TABLE exam_attempts
ADD COLUMN IF NOT EXISTS total_points INTEGER NOT NULL DEFAULT 0;

ALTER TABLE exam_attempts
ADD COLUMN IF NOT EXISTS correct_answers_count INTEGER;

ALTER TABLE exam_attempts
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempts' AND column_name = 'student_id'
    ) THEN
        EXECUTE '
            UPDATE exam_attempts
            SET user_id = student_id
            WHERE user_id IS NULL AND student_id IS NOT NULL
        ';
    END IF;
END $$;

UPDATE exam_attempts
SET updated_at = COALESCE(submitted_at, started_at, created_at, CURRENT_TIMESTAMP)
WHERE updated_at IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempts' AND column_name = 'student_id'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_attempts
            ALTER COLUMN student_id DROP NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempts' AND column_name = 'score'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_attempts
            ALTER COLUMN score DROP NOT NULL
        ';
    END IF;
END $$;

-- exam_attempt_answers: add new answer selection fields used by current code.
ALTER TABLE exam_attempt_answers
ADD COLUMN IF NOT EXISTS selected_option_id INTEGER;

ALTER TABLE exam_attempt_answers
ADD COLUMN IF NOT EXISTS answer_text TEXT;

ALTER TABLE exam_attempt_answers
ADD COLUMN IF NOT EXISTS answered_at TIMESTAMPTZ;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempt_answers' AND column_name = 'created_at'
    ) THEN
        EXECUTE '
            UPDATE exam_attempt_answers
            SET answered_at = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE answered_at IS NULL
        ';
    ELSE
        EXECUTE '
            UPDATE exam_attempt_answers
            SET answered_at = CURRENT_TIMESTAMP
            WHERE answered_at IS NULL
        ';
    END IF;
END $$;

ALTER TABLE exam_attempt_answers
ALTER COLUMN answered_at SET DEFAULT CURRENT_TIMESTAMP;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempt_answers' AND column_name = 'answer_text'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_attempt_answers
            ALTER COLUMN answer_text DROP NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempt_answers' AND column_name = 'is_correct'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_attempt_answers
            ALTER COLUMN is_correct DROP NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'exam_attempt_answers' AND column_name = 'score'
    ) THEN
        EXECUTE '
            ALTER TABLE exam_attempt_answers
            ALTER COLUMN score DROP NOT NULL
        ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'exam_question_options'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'exam_attempt_answers_selected_option_id_fkey'
    ) THEN
        ALTER TABLE exam_attempt_answers
        ADD CONSTRAINT exam_attempt_answers_selected_option_id_fkey
        FOREIGN KEY (selected_option_id)
        REFERENCES exam_question_options(id);
    END IF;
END $$;

COMMIT;
