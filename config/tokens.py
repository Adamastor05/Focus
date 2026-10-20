from dotenv import load_dotenv
import os

load_dotenv()

token_discord = os.getenv("TOKEN")
apis_text = os.getenv("GEMINI_APIS")

apis_array = apis_text.split(",")

TOKEN = os.getenv("TOKEN")

GEMINI_API_KEYS = apis_array
