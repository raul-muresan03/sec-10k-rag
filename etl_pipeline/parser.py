import re

import etl_pipeline

DOCUMENT_PATTERN = re.compile(r"(?<=<DOCUMENT>).*?(?=</DOCUMENT>)", re.IGNORECASE | re.DOTALL)
DOCUMENT_TYPE_PATTERN = re.compile(r"<TYPE>\s*([^\r\n<]+)", re.IGNORECASE)


def parse_10K(file_path: str) -> None:
    with open(file_path, "r") as f:
        file = f.read()

    documents = DOCUMENT_PATTERN.findall(file)
    if not documents:
        raise ValueError("No document block found in submission")

    document_10K = None
    for document in documents:
        document_type = DOCUMENT_TYPE_PATTERN.search(document)
        if document_type and document_type.group(1).strip().upper() == "10-K":
            document_10K = document
            break

    if document_10K is None:
        raise ValueError("No 10-K document found in submission")

    with open(etl_pipeline.DATA_DIR / "output_parser.txt", "w") as f:
        f.write(document_10K)

if __name__ == "__main__":
    file_path = etl_pipeline.DATA_DIR / "sec-edgar-filings/NVDA/10-K/0001045810-26-000021/full-submission.txt"
    parse_10K(str(file_path))
