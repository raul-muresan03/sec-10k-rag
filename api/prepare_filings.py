"""Prepare manifest-pinned dev filings from an operator shell."""

import argparse

from etl_pipeline.filing_download import download_verified
from etl_pipeline.filing_store import FilingIndexStore
from etl_pipeline.model_config import ModelConfig


def main(*, store: FilingIndexStore | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filing-id", help="Prepare one filing; omit to prepare all dev filings")
    args = parser.parse_args()
    try:
        ModelConfig.from_env().require_local_indexes()
        store = store if store is not None else FilingIndexStore()
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    catalog = store.catalog()
    if args.filing_id is not None and args.filing_id not in catalog:
        parser.error("Unknown dev filing ID")

    for selected_id in ([args.filing_id] if args.filing_id else catalog):
        filing = catalog[selected_id]
        print(f"Preparing {filing.ticker} {filing.year}…", flush=True)
        download_verified(filing)
        ready = store.prepare_selected(filing.ticker, filing.year)
        print(f"Ready: {ready.ticker} {ready.year} ({ready.chunk_count} chunks)", flush=True)


if __name__ == "__main__":
    main()
