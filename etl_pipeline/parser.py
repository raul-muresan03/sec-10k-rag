import re
from bs4 import BeautifulSoup

class SECParser:
    """
    Parser dedicated for raw SEC EDGAR files (full-submission.txt).
    Extracts only the 10-K document content and cleans the HTML.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def _read_file(self) -> str:
        """
        Reads the file content from disk.
        Try UTF-8 first, fallback to Latin-1 if it fails.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(self.file_path, "r", encoding="latin-1") as f:
                return f.read()

    def _extract_10k_document(self, raw_content: str) -> str:
        """
        The raw file contains many documents (<DOCUMENT>).
        We need to find the section that is of type "10-K".        
        """

        doc_list = re.findall("<DOCUMENT>.*?</DOCUMENT>", raw_content, re.DOTALL)
        for item in doc_list:
            if "<TYPE>10-K" in item:
                return item

        return None

    def _clean_html(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "lxml")
        
        for tag_name in ["script", "style", "header", "img"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        tables = soup.find_all("table")
        
        return soup.get_text(separator="\n", strip=True)


    def parse(self) -> str:
        """
        Main method (Public API).
        Orchestrates the flow: Read -> Extract 10-K -> Clean HTML -> Return Text.
        """
        content = self._read_file()
        extracted_10k_doc = self._extract_10k_document(content)
        cleaned_html = self._clean_html(extracted_10k_doc)
        
        with open("temp.txt", "w", encoding="utf-8") as f:
            f.write(cleaned_html)
            
        return cleaned_html

if __name__ == "__main__":
    parser = SECParser("data/test_parser.txt")
    parser.parse()