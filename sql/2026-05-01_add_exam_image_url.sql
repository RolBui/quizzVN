BEGIN;

ALTER TABLE exams
ADD COLUMN IF NOT EXISTS image_url TEXT;

UPDATE exams AS e
SET image_url = q.image_url
FROM (
    SELECT DISTINCT ON (exam_id)
        exam_id,
        image_url
    FROM exam_questions
    WHERE image_url IS NOT NULL
      AND BTRIM(image_url) <> ''
    ORDER BY exam_id, order_index NULLS LAST, id
) AS q
WHERE e.id = q.exam_id
  AND (e.image_url IS NULL OR BTRIM(e.image_url) = '');

COMMIT;
