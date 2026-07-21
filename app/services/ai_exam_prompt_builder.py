import json
from typing import Any


EXAM_OUTPUT_SCHEMA = {
    "title": "string",
    "description": "string",
    "subject": "string",
    "grade": "string",
    "duration_minutes": 0,
    "total_points": 0,
    "questions": [],
}

QUESTION_TYPE_OUTPUT_SCHEMAS = {
    "multiple_choice": {
        "type": "multiple_choice",
        "content": "string",
        "options": ["option A", "option B", "option C", "option D"],
        "correct_answer": "one exact value from options",
        "explanation": "string",
        "difficulty": "easy | medium | hard",
        "points": 1,
        "topic": "string",
    },
    "true_false": {
        "type": "true_false",
        "content": "string",
        "options": [],
        "correct_answer": True,
        "explanation": "string",
        "difficulty": "easy | medium | hard",
        "points": 1,
        "topic": "string",
    },
    "short_answer": {
        "type": "short_answer",
        "content": "string",
        "options": [],
        "correct_answer": "a non-empty string or an array of accepted strings",
        "explanation": "string",
        "difficulty": "easy | medium | hard",
        "points": 1,
        "topic": "string",
    },
    "essay": {
        "type": "essay",
        "content": "string",
        "options": [],
        "correct_answer": None,
        "explanation": "a detailed scoring rubric or expected answer outline",
        "difficulty": "easy | medium | hard",
        "points": 1,
        "topic": "string",
    },
}


def build_exam_generation_prompt(data: dict[str, Any]) -> str:
    question_types = ", ".join(data["question_types"])
    question_type_distribution = json.dumps(
        data["question_type_distribution"],
        ensure_ascii=False,
    )
    difficulty_distribution = json.dumps(
        data["difficulty_distribution"],
        ensure_ascii=False,
    )
    difficulty_distribution_total = sum(data["difficulty_distribution"].values())
    difficulty_distribution_unit = (
        "question counts"
        if difficulty_distribution_total == data["question_count"]
        else "percentages"
    )
    output_schema = json.dumps(EXAM_OUTPUT_SCHEMA, ensure_ascii=False, indent=2)
    selected_type_schemas = {
        question_type: QUESTION_TYPE_OUTPUT_SCHEMAS[question_type]
        for question_type in data["question_types"]
    }
    question_type_schemas = json.dumps(
        selected_type_schemas,
        ensure_ascii=False,
        indent=2,
    )
    additional_instructions = data.get("additional_instructions") or "None"

    return f"""You are an exam generation assistant for QuizzVN.

Your job is to create a high-quality exam draft for a teacher.

Return only valid JSON. Do not include markdown. Do not include explanations outside the JSON.

Exam requirements:
- Subject: {data["subject"]}
- Grade: {data["grade"]}
- Topic: {data["topic"]}
- Duration: {data["duration_minutes"]} minutes
- Number of questions: {data["question_count"]}
- Question types: {question_types}
- Question type distribution (question counts): {question_type_distribution}
- Difficulty distribution ({difficulty_distribution_unit}): {difficulty_distribution}
- Language: {data["language"]}
- Additional instructions: {additional_instructions}

Rules:
0. The structured Exam requirements above are authoritative. If Topic or Additional instructions contain a conflicting duration, question count, question type, type count, or difficulty count, ignore the conflicting value and follow the structured fields above.
1. The exam must be suitable for the specified grade.
2. Do not create duplicate questions.
3. Each question must have a clear content field.
4. Each multiple_choice question must have exactly 4 options.
5. correct_answer must match one of the options for multiple_choice.
5a. For true_false, options must be an empty array and correct_answer MUST be the unquoted JSON boolean true or false. Never return "true", "false", "Đúng", "Sai", 1, or 0.
5b. For short_answer, options must be an empty array and correct_answer must be a non-empty string or a non-empty array of accepted strings.
5c. For essay, options must be an empty array, correct_answer may be null, and explanation must contain a detailed scoring rubric or expected answer outline.
6. Each question must include explanation.
7. Each question must include difficulty: easy, medium, or hard.
8. Each question must include points.
9. The number of questions must exactly match the requested question_count.
10. Do not include unsafe, harmful, or irrelevant content.
11. Use only these question types: {question_types}.
12. Follow the requested question type distribution exactly.
13. Follow the requested difficulty distribution exactly when it is given as question counts.
14. Do not use underscores, markdown, or artificial markers inside answer options.
15. For pronunciation questions, write full plain words in options. Do not write words like h_o_pe or _o_.
16. If a question needs an underlined part but the output schema has no rich text, explain the target sound/letter in the explanation instead of marking the option text.
17. Write question text and explanations in Vietnamese, but keep modern international proper nouns in their common form.
18. Do not phonetically transliterate country, person, place, or organization names. Use names such as Indonesia, Philippines, Malaysia, Singapore, ASEAN, WTO, and United Nations instead of hyphenated Vietnamese phonetic spellings.
19. Keep established Vietnamese textbook terms when they are the common form, such as Vi\u1ec7t Nam, L\u00e0o, Th\u00e1i Lan, Li\u00ean X\u00f4, M\u1ef9, and Li\u00ean h\u1ee3p qu\u1ed1c.

Return JSON in this exact structure:
{output_schema}

Use the matching question object format below for each selected question type.
These are format examples only; do not add example questions to the response:
{question_type_schemas}
"""


def build_exam_batch_generation_prompt(
    data: dict[str, Any],
    batch_index: int,
    batch_count: int,
    existing_questions: list[dict[str, Any]],
) -> str:
    base_prompt = build_exam_generation_prompt(data)
    existing_json = json.dumps(existing_questions, ensure_ascii=False, indent=2)

    return f"""{base_prompt}

Batch generation context:
- This is batch {batch_index}/{batch_count} for a larger exam.
- Return only this batch's {data["question_count"]} questions.
- Do not mention batch numbers in question content, answers, or explanations.
- Keep style and difficulty consistent with the full exam.

Existing draft questions to avoid repeating:
{existing_json}
"""

def build_exam_repair_prompt(
    original_prompt: str,
    previous_payload: dict[str, Any],
    errors: list[str],
) -> str:
    previous_json = json.dumps(previous_payload, ensure_ascii=False, indent=2)
    error_text = "\n".join(f"- {error}" for error in errors)

    return f"""{original_prompt}

The previous JSON failed validation.

Errors:
{error_text}

Previous JSON:
{previous_json}

Please fix the JSON. Return only valid JSON. Do not add markdown.
For true_false questions, correct_answer must be the unquoted JSON boolean true or false.
Do not use underscores or artificial underline markers in option text.
Keep modern international proper nouns in their common form. Do not use hyphenated Vietnamese phonetic spellings such as In-do-ne-xi-a or Phi-lip-pin.
"""


def build_more_questions_prompt(
    data: dict[str, Any],
    existing_questions: list[dict[str, Any]],
) -> str:
    base_prompt = build_exam_generation_prompt(data)
    existing_json = json.dumps(existing_questions, ensure_ascii=False, indent=2)

    return f"""{base_prompt}

You are adding questions to an existing draft, not creating a replacement exam.

Existing draft questions to avoid repeating:
{existing_json}

Rules for this add-on generation:
1. Return only the requested number of new questions.
2. Do not repeat or closely paraphrase any existing draft question, including rejected ones.
3. Keep the same subject, grade, topic, language, and exam style.
4. The teacher will review these new questions before saving the final exam.
"""
