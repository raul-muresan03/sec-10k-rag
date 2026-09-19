import time

import etl_pipeline
from etl_pipeline.chunker import chunk_10K
from etl_pipeline.cleaner import clean_10K
from etl_pipeline.ingest import download_10k
from etl_pipeline.parser import parse_10K


ACTIVE_ACCESSION_FILENAME = "active_accession.txt"
VECTOR_STORE_FILENAME = "all_chunks_embeddings.json"


def ensure_index(ticker: str, year: int) -> None:
    print(f"Checking SEC for {ticker.upper()} 10-K filings...", flush=True)
    download_start = time.perf_counter()
    filing_path = download_10k(ticker, year)
    download_end = time.perf_counter()
    download_seconds = download_end - download_start
    accession = filing_path.parent.name
    print(f"Selected {accession} in {download_seconds:.2f}s.", flush=True)

    accession_path = etl_pipeline.DATA_DIR / ACTIVE_ACCESSION_FILENAME
    vector_store_path = etl_pipeline.DATA_DIR / VECTOR_STORE_FILENAME
    if (
        vector_store_path.is_file()
        and accession_path.is_file()
        and accession_path.read_text().strip() == accession
    ):
        print("Reusing the active index for this filing.", flush=True)
        return

    accession_path.unlink(missing_ok=True)
    vector_store_path.unlink(missing_ok=True)

    print("Parsing the filing...", flush=True)
    parsing_start = time.perf_counter()
    parse_10K(str(filing_path))
    parsing_end = time.perf_counter()
    parsing_seconds = parsing_end - parsing_start
    print(f"Parsing completed in {parsing_seconds:.2f}s.", flush=True)

    parsed_path = etl_pipeline.DATA_DIR / "output_parser.txt"
    print("Cleaning the filing...", flush=True)
    cleaning_start = time.perf_counter()
    clean_10K(str(parsed_path))
    cleaning_end = time.perf_counter()
    cleaning_seconds = cleaning_end - cleaning_start
    print(f"Cleaning completed in {cleaning_seconds:.2f}s.", flush=True)

    cleaned_path = etl_pipeline.DATA_DIR / "output_cleaner.txt"
    print("Creating chunks and embeddings...", flush=True)
    chunking_start = time.perf_counter()
    chunk_10K(str(cleaned_path))
    chunking_end = time.perf_counter()
    chunking_seconds = chunking_end - chunking_start
    print(f"Indexing completed in {chunking_seconds:.2f}s.", flush=True)

    if not vector_store_path.is_file():
        raise RuntimeError(f"Vector store was not created: {vector_store_path}")

    accession_path.write_text(accession)
