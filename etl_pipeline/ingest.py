from dotenv import load_dotenv
import os

load_dotenv()

def download_10k(company_code: str):
    email = os.getenv("SEC_API_EMAIL")
    if not email:
        print("Email is missing from .env file")




if __name__ == "__main__":
    download_10k("NVDA")