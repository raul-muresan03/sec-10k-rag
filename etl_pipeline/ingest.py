import os
from dotenv import load_dotenv
from sec_edgar_downloader import Downloader

load_dotenv()

def download_10k(ticker: str):
    email = os.getenv("SEC_API_EMAIL")
    if not email:
        raise ValueError("Email is missing in .env")

    dl = Downloader("SecRagTool", email, "data")
    
    print(f"[{ticker}] 10-K is downloading...")
    
    dl.get("10-K", ticker, limit=1, after="2023-01-01")

    print(f"[{ticker}] Download successful!")

if __name__ == "__main__":
    download_10k("AAPL")