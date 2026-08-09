import os
import glob
import argparse
from ingest import download_10k
from parser import SECParser
from cleaner import SECCleaner
from chunker import Chunker
from vector_store import upload_chunks_to_pinecone, delete_all_vectors
from logger import get_logger

logger = get_logger(__name__)


def _download_10k(ticker: str) -> str:
    """Step 1: Download SEC filing, return path to full-submission.txt."""
    download_10k(ticker)

    base_path = f"../data/raw/sec-edgar-filings/{ticker}/10-K"
    files = glob.glob(f"{base_path}/*/full-submission.txt")
    if not files:
        raise FileNotFoundError(f"No 10-K file found for {ticker}")

    return files[0]


def _parse_10k(raw_file_path: str, ticker: str, year: str) -> str:
    """Step 2: Extract 10-K document from raw SEC filing."""
    os.makedirs("../data/parsed", exist_ok=True)
    parser = SECParser(raw_file_path, ticker=ticker, year=year)
    return parser.parse()


def _clean_html(html_content: str) -> str:
    """Step 3: Clean extracted HTML into LLM-friendly text."""
    os.makedirs("../data/cleaned", exist_ok=True)
    cleaner = SECCleaner(html_content)
    return cleaner.clean()


def _chunk_and_upload(text: str, ticker: str, year: str) -> None:
    """Step 4-5: Split cleaned text into chunks and upload to Pinecone."""
    chunker = Chunker(text, ticker=ticker, year=year)
    chunks = chunker.run()
    avg = sum(len(c["text"]) for c in chunks) / len(chunks) if chunks else 0
    logger.info(f"Chunking complete. Generated {len(chunks)} chunks. Avg: {avg:.0f} chars")

    if chunks:
        logger.info("Step 5: Storing Vectors in Pinecone")
        upload_chunks_to_pinecone(chunks)


def run_pipeline(ticker: str, year: str):
    logger.info(f"Starting pipeline for {ticker} ({year})...")

    logger.info("Step 1: Downloading 10-K")
    raw_file_path = _download_10k(ticker)
    logger.info(f"File found: {raw_file_path}")

    logger.info("Step 2: Parsing HTML")
    html_text = _parse_10k(raw_file_path, ticker, year)
    logger.info(f"Parsing complete. Text length: {len(html_text)} chars")

    logger.info("Step 3: Cleaning HTML")
    cleaned_text = _clean_html(html_text)
    logger.info(f"Cleaning complete. Text length: {len(cleaned_text)} chars")

    _chunk_and_upload(cleaned_text, ticker, year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SEC data ingestion pipeline.")
    parser.add_argument("ticker", type=str, help="The company ticker symbol (e.g., AAPL).")
    parser.add_argument("year", type=str, help="The fiscal year of the 10-K report (e.g., 2023).")
    parser.add_argument("--clean", action="store_true", help="Delete all vectors from the Pinecone index before running the pipeline.")

    args = parser.parse_args()

    if args.clean:
        logger.info("Clearing Pinecone Index")
        delete_all_vectors()

    run_pipeline(ticker=args.ticker, year=args.year)