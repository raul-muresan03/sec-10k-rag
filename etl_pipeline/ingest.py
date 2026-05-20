import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sec_edgar_downloader import Downloader
from config import settings
from logger import get_logger

logger = get_logger(__name__)

def download_10k(ticker: str):
    email = settings.sec_api_email
    if not email:
        raise ValueError("Email is missing in settings")

    dl = Downloader("SecRagTool", email, "../data/raw")

    logger.info(f"[{ticker}] 10-K is downloading...")

    dl.get("10-K", ticker, limit=1, after="2023-01-01")

    logger.info(f"[{ticker}] Download successful!")

if __name__ == "__main__":
    download_10k("NVDA")