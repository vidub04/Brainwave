from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from supabase import create_client,Client

load_dotenv()

SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase:Client=create_client(SUPABASE_URL,SUPABASE_KEY)

def get_your_info():
    '''This function will return the number of conversations in the conversations table'''

    result=supabase.table("conversations") \
    .select("title") \
    .execute()

    return result.data


client=genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

tools=[get_your_info]

config=types.GenerateContentConfig(
      tools=tools
)
response=client.models.generate_content(
      model="gemini-3.5-flash",
      contents="Can you tell me how all the titles of conversations stored in the conversations table of my database?",
      config=config
)

print(response.text)
