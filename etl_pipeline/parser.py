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

        for element in soup.find_all(['script', 'style', 'head']):
            element.decompose()

        tables = soup.find_all("table")
        for table in tables:
            rows = []

            all_trs = table.find_all("tr")

            for tr in all_trs:
                cells = tr.find_all(["td", "th"])
                raw_cells = [cell.get_text(" ", strip=True).replace("|", "") for cell in cells]

                if not any(c.strip() for c in raw_cells):
                    continue

                merged_cells = []
                skip_next = False

                for i in range(len(raw_cells)):
                    if skip_next:
                        skip_next = False
                        continue

                    current_txt = raw_cells[i]
                    next_txt = raw_cells[i+1] if i + 1 < len(raw_cells) else ""

                    if current_txt == "$" and next_txt:
                        merged_cells.append("$" + next_txt)
                        skip_next = True 

                    elif current_txt == "%" and merged_cells:
                        merged_cells[-1] = merged_cells[-1] + "%"

                    elif current_txt == "(" and next_txt:
                        merged_cells.append("(" + next_txt)
                        skip_next = True
                    elif current_txt == ")" and merged_cells:
                        merged_cells[-1] = merged_cells[-1] + ")"

                    else:
                        merged_cells.append(current_txt)

                final_row = [c for c in merged_cells if c.strip()]

                if final_row:
                    rows.append(final_row)

            if not rows:
                continue

            md_table = []

            max_cols = max(len(r) for r in rows)

            header_row = rows[0]
            if len(header_row) < max_cols:
                missing = max_cols - len(header_row)
                header_row = [""] * missing + header_row
            
            md_table.append("| " + " | ".join(header_row) + " |")
            md_table.append("| " + " | ".join(["---"] * max_cols) + " |")

            for r in rows[1:]:
                if len(r) < max_cols:
                    r.extend([""] * (max_cols - len(r)))
                md_table.append("| " + " | ".join(r) + " |")

            table.replace_with("\n" + "\n".join(md_table) + "\n\n\u200b") 

        return soup.get_text(separator="\n", strip=True)

    def parse(self) -> str:
        """
        Main method (Public API).
        Orchestrates the flow: Read -> Extract 10-K -> Clean HTML -> Return Text.
        """
        content = self._read_file()
        extracted_10k_doc = self._extract_10k_document(content)
        cleaned_html = self._clean_html(extracted_10k_doc)

        return cleaned_html
