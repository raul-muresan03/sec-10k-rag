from dotenv import load_dotenv
import os
from sec_edgar_downloader import Downloader

import etl_pipeline

load_dotenv()

def download_10k(company_code: str):
    email = os.getenv("SEC_API_EMAIL")
    if not email:
        print("Email is missing from .env file")
    etl_pipeline.DATA_DIR.mkdir(parents=True, exist_ok=True)
    downloader = Downloader("SEC RAG TOOL", email, str(etl_pipeline.DATA_DIR))

    downloader.get("10-K", company_code, limit=1)

if __name__ == "__main__":
    download_10k("NVDA")
