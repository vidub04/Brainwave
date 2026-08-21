##review done
import os
import re
import json
import time
import logging
import requests
from typing import Optional, Any, Dict
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("adaptive_engine.llm")

ACTIVE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.6-flash",
]

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. LLM requests will use fallback mode.")
##clean extra white spaces and commentary
    def clean_json_string(self, raw_text: str) -> str:
        """Extracts and repairs JSON text from markdown blocks or raw response."""
        text = raw_text.strip()
        
        # Match ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()
        
        # Find opening { or [
        first_brace = text.find("{")
        first_bracket = text.find("[")
        start_idx = -1
        if first_brace != -1 and first_bracket != -1:
            start_idx = min(first_brace, first_bracket)
        elif first_brace != -1:
            start_idx = first_brace
        elif first_bracket != -1:
            start_idx = first_bracket

        if start_idx != -1:
            last_brace = text.rfind("}")
            last_bracket = text.rfind("]")
            end_idx = max(last_brace, last_bracket)
            if end_idx != -1 and end_idx >= start_idx:
                text = text[start_idx:end_idx+1]
        
        return text

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        default_data: Optional[Dict[str, Any]] = None,
        retries: int = 2
    ) -> Dict[str, Any]:
        """Calls Gemini REST endpoint with retries and returns parsed JSON object."""
        if not self.api_key:
            return default_data or {}

        instruction_prefix = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\n" if system_instruction else ""
        full_prompt = f"{instruction_prefix}{prompt}\n\nIMPORTANT: Respond ONLY with valid JSON, no markdown fences, no extra commentary."

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }

        for attempt in range(retries):
            for model_name in ACTIVE_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    resp = self.session.post(url, json=payload, timeout=8)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                raw_text = parts[0].get("text", "")
                                cleaned = self.clean_json_string(raw_text)
                                try:
                                    return json.loads(cleaned)
                                except json.JSONDecodeError:
                                    fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)
                                    return json.loads(fixed)
                    elif resp.status_code == 429:
                        logger.warning(f"Rate limit 429 on {model_name}; trying next model...")
                        continue
                    else:
                        logger.warning(f"Gemini API returned status {resp.status_code} for {model_name}")
                except Exception as ex:
                    logger.warning(f"LLM request error on {model_name} (attempt {attempt+1}): {ex}")
                    continue

        logger.warning("All LLM JSON generation candidates exhausted; returning default data.")
        return default_data or {}

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        default_text: str = "",
        retries: int = 2
    ) -> str:
        """Calls Gemini and returns plain text string."""
        if not self.api_key:
            return default_text

        instruction_prefix = f"SYSTEM INSTRUCTION:\n{system_instruction}\n\n" if system_instruction else ""
        full_prompt = f"{instruction_prefix}{prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048
            }
        }

        for attempt in range(retries):
            for model_name in ACTIVE_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    resp = self.session.post(url, json=payload, timeout=8)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
                except Exception as ex:
                    logger.warning(f"LLM text request error on {model_name}: {ex}")
                    continue

        return default_text


_default_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _default_llm_client
    if _default_llm_client is None:
        _default_llm_client = LLMClient()
    return _default_llm_client
