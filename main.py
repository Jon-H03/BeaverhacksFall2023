import openai
import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Set up the API key
openai.api_key = os.getenv("OPENAI_API_KEY")


