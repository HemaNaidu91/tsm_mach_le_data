# some sample code
from dotenv import load_dotenv
import os

load_dotenv()
API_URL: str = os.getenv("API_URL")

print(API_URL)
