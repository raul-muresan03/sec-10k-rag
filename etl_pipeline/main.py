import os
import glob
from dotenv import load_dotenv
from ingest import download_10k
from parser import SECParser
from chunker import Chunker

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
    
    # 4. PREVIEW
    if chunks:
        print("\n--- Preview First 2 Chunks ---")
        print("--- Chunk 1 ---")
        print(chunks[0]["text"])
        print(f"\n[Metadata] Page: {chunks[0]['page']}, Section: {chunks[0]['section']}")
        
        print("\n--- Chunk 2 ---")
        print(chunks[1]["text"])
        print(f"\n[Metadata] Page: {chunks[1]['page']}, Section: {chunks[1]['section']}")


if __name__ == "__main__":
    run_pipeline("AAPL", "2024")