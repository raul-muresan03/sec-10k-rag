import os
import re

class SECParser:
    """
    Parser dedicated for raw SEC EDGAR files (full-submission.txt).
    Extracts only the 10-K document content.
    """

    def __init__(self, file_path: str, ticker: str = "UNKNOWN", year: str = "UNKNOWN"):
        self.file_path = file_path
        self.ticker = ticker
        self.year = year

    def _read_file(self) -> str:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(self.file_path, "r", encoding="latin-1") as f:
                return f.read()

    def _extract_10k_document(self, raw_content: str) -> str:
        """
        The raw file contains many documents (<DOCUMENT>).
        This function extracts only the section that is of type "10-K".
        """

        doc_list = re.findall(r"<DOCUMENT>.*?</DOCUMENT>", raw_content, re.DOTALL)
        for item in doc_list:
            if re.search(r"<TYPE>10-K", item, re.IGNORECASE):
                text_match = re.search(r"<TEXT>(.*?)</TEXT>", item, re.DOTALL | re.IGNORECASE)
                if text_match:
                    return text_match.group(1)
                return item

        raise ValueError("No 10-K document found in file")

    def parse(self) -> str:
        content = self._read_file()
        content = self._extract_10k_document(content)

        with open("../data/parsed/parsed_10k.txt", "w", encoding="utf-8") as f:
            f.write(content)

        return content

if __name__ == "__main__":
    parser = SECParser(os.getenv("RAW_APPLE_10K_PATH"), ticker="APPL", year="2024")

    parser.parse()
