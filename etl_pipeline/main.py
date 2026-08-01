import os
import glob
import argparse
from ingest import download_10k
from parser import SECParser
from chunker import Chunker
from vector_store import upload_chunks_to_pinecone, delete_all_vectors
from config import settings
from logger import get_logger

logger = get_logger(__name__)

def run_pipeline(ticker: str, year: str):
    logger.info(f"Starting pipeline for {ticker} ({year})...")

    # 1. DOWNLOAD
    logger.info("Step 1: Downloading 10-K")
    download_10k(ticker)

    base_path = f"../data/raw/sec-edgar-filings/{ticker}/10-K"

    files = glob.glob(f"{base_path}/*/full-submission.txt")
    if not files:
        logger.error("No file downloaded.")
        return

    raw_file_path = files[0]
    logger.info(f"File found: {raw_file_path}")

    # 2. PARSE
    logger.info("Step 2: Parsing HTML")
    os.makedirs("../data/parsed", exist_ok=True)

    parser = SECParser(raw_file_path, ticker=ticker, year=year)
    clean_text = parser.parse()
    logger.info(f"Parsing complete. Text length: {len(clean_text)} chars")

    # 3. CHUNK
    logger.info("Step 3: Chunking")
    chunker = Chunker(clean_text, ticker=ticker, year=year)
    chunks = chunker.run()
    avg = sum(len(c['text']) for c in chunks) / len(chunks) if chunks else 0

    logger.info(f"Chunking complete. Generated {len(chunks)} chunks. Avg: {avg:.0f} chars")

    # 4. UPLOAD TO PINECONE
    if chunks:
        logger.info("Step 4: Storing Vectors in Pinecone")
        upload_chunks_to_pinecone(chunks)


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