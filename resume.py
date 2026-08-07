import json
import pdfplumber
import docx
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = docx.Document(BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def extract_raw_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type. Please upload a .pdf or .docx resume.")


def structure_resume(gemini_client, raw_text: str) -> dict:
    """
    Uses Gemini to turn raw resume text into structured JSON we can
    feed into interview prompts.
    """
    prompt = f"""
    Extract structured information from this resume text.
    Return ONLY valid JSON, no markdown fences, no extra commentary,
    matching exactly this shape:

    {{
      "name": string,
      "current_role": string,
      "years_experience": number,
      "skills": [string],
      "past_roles": [{{"title": string, "company": string, "duration": string}}],
      "education": [string],
      "summary": string
    }}

    Resume text:
    \"\"\"{raw_text}\"\"\"
    """

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    cleaned = response.text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # fall back gracefully rather than crashing the request
        return {"summary": raw_text[:1000], "parse_error": True}
