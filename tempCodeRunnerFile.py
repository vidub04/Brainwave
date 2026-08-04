from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

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

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=data.prompt
    )

    return {
        "response": response.text
    }

print(os.getenv("GEMINI_API_KEY"))