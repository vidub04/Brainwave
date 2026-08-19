import json
import pdfplumber
import docx
from io import BytesIO
from typing import Dict, Any


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


def structure_resume(llm_or_gemini_client, raw_text: str) -> dict:
    """
    Turns raw resume text into structured JSON.
    Works with both LLMClient and direct google.genai Client.
    """
    prompt = f"""
Extract structured information from this resume text.
Return ONLY valid JSON matching exactly this shape:
{{
  "name": "Candidate Name",
  "current_role": "Software Engineer",
  "years_experience": 3,
  "skills": ["Skill1", "Skill2"],
  "past_roles": [{{"title": "Role Title", "company": "Company Name", "duration": "2 years"}}],
  "education": ["Degree details"],
  "summary": "Brief background summary"
}}

Resume text:
\"\"\"{raw_text[:3000]}\"\"\"
"""

    default_structure = {
        "name": "Candidate",
        "current_role": "Engineer",
        "years_experience": 2,
        "skills": [],
        "past_roles": [],
        "education": [],
        "summary": raw_text[:300]
    }

    # If it's our LLMClient
    if hasattr(llm_or_gemini_client, "generate_json"):
        return llm_or_gemini_client.generate_json(
            prompt=prompt,
            default_data=default_structure
        )

    # If it's a raw google-genai client
    try:
        response = llm_or_gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
        )
        cleaned = response.text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except Exception:
        return default_structure
