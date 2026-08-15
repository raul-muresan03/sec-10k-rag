import re

regex_10K_document = r"(?<=<DOCUMENT>)[\s\S]*?(?=</DOCUMENT>)"

def parse_10K(file_path: str) -> None:
    with open(file_path, 'r') as f:
        file = f.read()
        match = re.search(regex_10K_document, file)
        document_10K = match.group()

    with open("../data/output_parser.txt", "w") as f:
        f.write(document_10K)

if __name__ == "__main__":
    file_path = "../data/sec-edgar-filings/NVDA/10-K/0001045810-26-000021/full-submission.txt"
    parse_10K(file_path)