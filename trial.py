from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os
from fastapi.staticfiles import StaticFiles



load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

class PromptRequest(BaseModel):
    prompt: str


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )





@app.post("/generate")
async def generate(data: PromptRequest):

        SYSTEM_PROMPT = """
        Act like a HR Professional interviewer of a prestigious company.
        Ask questions to a candidate seeking a job at your company.
        Use bullet points where appropriate.
        Never answer unrelated questions.
        """

        full_prompt = f"""
        {SYSTEM_PROMPT}

        User:
        {data.prompt}
        """


        response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=full_prompt
    )

        return {
        "response": response.text
    }

print(os.getenv("GEMINI_API_KEY"))