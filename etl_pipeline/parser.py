import re

import etl_pipeline

regex_10K_document = r"(?<=<DOCUMENT>)[\s\S]*?(?=</DOCUMENT>)"

def parse_10K(file_path: str) -> None:
    with open(file_path, 'r') as f:
        file = f.read()
        match = re.search(regex_10K_document, file)
        if match is None:
            raise ValueError("No document block found in submission")
        document_10K = match.group()

    with open(etl_pipeline.DATA_DIR / "output_parser.txt", "w") as f:
        f.write(document_10K)

if __name__ == "__main__":
    file_path = etl_pipeline.DATA_DIR / "sec-edgar-filings/NVDA/10-K/0001045810-26-000021/full-submission.txt"
    parse_10K(str(file_path))
