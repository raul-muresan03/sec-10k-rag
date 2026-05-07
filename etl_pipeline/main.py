import os
import glob
import argparse
from dotenv import load_dotenv
from ingest import download_10k
from parser import SECParser
from chunker import Chunker
from vector_store import upload_chunks_to_pinecone, delete_all_vectors

load_dotenv()

def run_pipeline(ticker: str, year: str):
    print(f"Starting pipeline for {ticker} ({year})...")

    # 1. DOWNLOAD
    print(f"\n--- Step 1: Downloading 10-K ---")
    download_10k(ticker)

    base_path = f"../data/raw/sec-edgar-filings/{ticker}/10-K"

    files = glob.glob(f"{base_path}/*/full-submission.txt")
    if not files:
        print("Error: No file downloaded.")
        return

    raw_file_path = files[0]
    print(f"File found: {raw_file_path}")

    # 2. PARSE
    print(f"\n--- Step 2: Parsing HTML ---")
    os.makedirs("../data/parsed", exist_ok=True)

    parser = SECParser(raw_file_path, ticker=ticker, year=year)
    clean_text = parser.parse()
    print(f"Parsing complete. Text length: {len(clean_text)} characters")

    # 3. CHUNK
    print(f"\n--- Step 3: Chunking ---")
    chunker = Chunker(clean_text, ticker=ticker, year=year)
    chunks = chunker.run()
    average_chunk_size = 0
    for chunk in chunks:
        average_chunk_size += len(chunk['text'])
    average_chunk_size /= len(chunks) if chunks else 1

    print(f"Chunking complete. Generated {len(chunks)} chunks.")
    print(f"Average chunk size: {average_chunk_size:.2f} characters")

    # 4. UPLOAD TO PINECONE
    if chunks:
        print("\n--- Step 4: Storing Vectors in Pinecone ---")
        upload_chunks_to_pinecone(chunks)

    # 5. PREVIEW
    if chunks:
        print("\n--- Preview First 2 Chunks ---")
        print("--- Chunk 1 ---")
        print(chunks[0]["text"])
        print(f"\n[Metadata] Page: {chunks[0]['page']}, Section: {chunks[0]['section']}")

        print("\n--- Chunk 2 ---")
        print(chunks[1]["text"])
        print(f"\n[Metadata] Page: {chunks[1]['page']}, Section: {chunks[1]['section']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SEC data ingestion pipeline.")
    parser.add_argument("ticker", type=str, help="The company ticker symbol (e.g., AAPL).")
    parser.add_argument("year", type=str, help="The fiscal year of the 10-K report (e.g., 2023).")
    parser.add_argument("--clean", action="store_true", help="Delete all vectors from the Pinecone index before running the pipeline.")

    args = parser.parse_args()

    if args.clean:
        print("\n--- Pre-run Step: Clearing Pinecone Index ---")
        delete_all_vectors()
        print("--- Index Cleared ---\n")

    run_pipeline(ticker=args.ticker, year=args.year)