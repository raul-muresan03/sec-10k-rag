from email.mime import text
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os


class SECParser:
    """
    Parser dedicated for raw SEC EDGAR files (full-submission.txt).
    Extracts only the 10-K document content and cleans the HTML.
    """

    def __init__(self, file_path: str, ticker: str = "UNKNOWN", year: str = "UNKNOWN"):
        self.file_path = file_path
        self.ticker = ticker
        self.year = year

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

        doc_list = re.findall(r"<DOCUMENT>.*?</DOCUMENT>", raw_content, re.DOTALL)
        for item in doc_list:
            if re.search(r"<TYPE>10-K", item, re.IGNORECASE):
                text_match = re.search(r"<TEXT>(.*?)</TEXT>", item, re.DOTALL | re.IGNORECASE)
                if text_match:
                    return text_match.group(1)
                return item
        return None    
    
    def _remove_table_of_contents(self, text: str) -> str:
        """
        Removes Table of Contents (TOC) based on the occurrence of "Item 1. Business".
        """
    
        pattern = re.compile(r"^(?!\|)\s*Item\s+1\.?\s+Business", re.IGNORECASE | re.MULTILINE)
        matches = list(pattern.finditer(text))
    
        if len(matches) >= 2:
            return text[matches[1].start():]
        elif len(matches) == 1:
            return text[matches[0].start():]

        return text

    def _remove_part3_and_part4(self, text: str) -> str:
        """
        Removes PART III and PART IV using a cascade of 'kill switches'.
        Priority:
        1. PART III title.
        2. Item 15 (Exhibits).
        3. Item 16 (Form 10-K Summary - specific Intel).
        4. Standard Legal Signature Phrase (The ultimate fallback).
        """
        stop_patterns = [
            r"^(?!\|)\s*PART\s+III",
            r"^(?!\|)\s*Item\s+10\.\s+",
            r"Pursuant\s+to\s+the\s+requirements\s+of\s+the\s+Securities\s+Exchange\s+Act"
        ]

        for pattern_str in stop_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            match = pattern.search(text)
            
            if match:
                return text[:match.start()]

        return text
    
    def _remove_empty_sections(self, text: str) -> str:
        """
        Removes standard legal sections that are empty or marked 'Not applicable'.
        """
        patterns = [
            r"(?m)^Item\s+\w+\.\s+.*?\n\s*None\.\s*$",
            r"(?m)^Item\s+\w+\.\s+.*?\n\s*Not applicable\.\s*$",
            r"(?m)^Item\s+\w+\.\s+\[Reserved\]\s*$"
        ]
        for pattern in patterns:
            text = re.sub(pattern, "", text)
        return text
    
    def _clean_html(self, html_content: str) -> str:
        """
        Sanitizes HTML content and converts complex structures (like tables) into LLM-friendly text. This method
        orchestrates a series of cleaning and transformation steps to prepare the raw HTML for downstream processing.
        
        Key operations:
        1. Removes noise tags (scripts, styles, images, links, XBRL-specific tags, hidden elements based on style).
        2. Parses HTML tables into a matrix structure, handling 'colspan' attributes to preserve grid alignment.
        3. Normalizes table dimensions by padding short rows to create a rectangular matrix.
        4. Intelligently merges columns to handle financial formatting (e.g., detached '$' or '%') and shifts content
           to consolidate related data into a single column.
        5. Removes completely empty columns from tables to reduce noise.
        6. Replaces HTML tables with unique placeholders, then injects formatted Markdown tables with proper spacing
           after the initial text extraction.
        7. Replaces page footers (e.g., "Company | Year Form 10-K | Page") with `[[PAGE_X]]` markers for metadata extraction.
        8. Marks document sections (e.g., "Item 1. Business", "PART I.") with `[[SECTION_...]]` markers for metadata.
        9. Cleans up specific formatting issues like standalone '®' and '•' symbols, and excessive newlines.
        10. Removes specific audit report sections that are not relevant for RAG.
        """
        soup = BeautifulSoup(html_content, "lxml")

        for tag_name in ["script", "style", "header", "img", "a", "ix:header", "ix:hidden"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        for hidden in soup.find_all(['div', 'span'], style=True):
            if 'display:none' in hidden['style'].lower().replace(" ", ""):
                hidden.decompose()

        tables = soup.find_all("table")
        table_placeholders = {}
        for table_idx, table in enumerate(tables):
            rows_data = []
            for tr in table.find_all("tr"):
                current_row_cells = []
                cells = tr.find_all(["td", "th"])
                for cell in cells:
                    cell_text = cell.get_text(separator=" ", strip=True).replace("|", "").replace("\xa0", " ")
                    colspan_val = cell.get("colspan")
                    n = int(colspan_val) if colspan_val else 1

                    current_row_cells.append(cell_text)
                    if n > 1:
                        for i in range(n - 1):
                            current_row_cells.append("")

                if any(current_row_cells):
                    rows_data.append(current_row_cells)

            if not rows_data:
                continue

            max_cols = max(len(row) for row in rows_data)
            for row in rows_data:
                if len(row) < max_cols:
                    row.extend([""] * (max_cols - len(row)))

            for col_idx in range(max_cols - 2, -1, -1):
                should_merge = False
                is_distinct_column = False

                for row in rows_data:
                    if col_idx + 1 >= len(row):
                        continue

                    curr_val = row[col_idx].strip()
                    next_val = row[col_idx + 1].strip()

                    if curr_val == "$" and next_val == "%":
                        is_distinct_column = True
                        break

                    has_digit_curr = any(c.isdigit() for c in curr_val)
                    has_digit_next = any(c.isdigit() for c in next_val)
                    
                    if has_digit_curr and has_digit_next:
                        is_distinct_column = True
                        break

                    if curr_val == "$":
                        should_merge = True
                    elif next_val == "%": 
                        should_merge = True


                if should_merge and not is_distinct_column:
                    for row in rows_data:
                        val_curr = row[col_idx]
                        val_next = row[col_idx + 1]

                        if val_curr == "$":
                            row[col_idx] = "$ " + val_next
                        elif val_next == "%":
                            row[col_idx] = val_curr + "%"
                        elif val_curr == "":
                            row[col_idx] = val_next
                        else:
                            row[col_idx] = (val_curr + " " + val_next).strip()

                        del row[col_idx + 1]

            if rows_data:
                current_cols = len(rows_data[0])
                for col_idx in range(current_cols - 1, -1, -1):
                    is_empty_col = True
                    for row in rows_data:
                        if row[col_idx].strip():
                            is_empty_col = False
                            break
                    if is_empty_col:
                        for row in rows_data:
                            del row[col_idx]

            markdown_rows = []
            for i, row in enumerate(rows_data):
                markdown_row = "| " + " | ".join(row) + " |"
                markdown_rows.append(markdown_row)
                if i == 0:
                    separator_row = "| " + " | ".join(["---"] * len(row)) + " |"
                    markdown_rows.append(separator_row)

            markdown_table = "\n".join(markdown_rows)
            placeholder = f"[[TABLE_PLACEHOLDER_{table_idx}]]"
            table_placeholders[placeholder] = markdown_table
            table.replace_with(placeholder)

        cleaned_text = soup.get_text(separator="\n", strip=True)
        
        # Normalize non-breaking spaces and horizontal whitespace
        cleaned_text = cleaned_text.replace("\xa0", " ")
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
        
        cleaned_text = re.sub(r' *\n *', '\n', cleaned_text)

        for placeholder, md_table in table_placeholders.items():
            cleaned_text = cleaned_text.replace(placeholder, "\n\n" + md_table + "\n\n")

        # {Company} | {year} Form 10-K | {number}
        footer_pattern = r"(?m)^.*?\|\s+\d{4}\s+Form\s+10-K\s+\|\s+(\d+)$"
        cleaned_text = re.sub(footer_pattern, r"\n[[PAGE_\1]]\n", cleaned_text)

        cleaned_text = self._remove_table_of_contents(cleaned_text)
        cleaned_text = self._remove_part3_and_part4(cleaned_text)
        cleaned_text = self._remove_empty_sections(cleaned_text)

        def create_section_tag(match):
            original_text = match.group(1)
            clean_tag_content = re.sub(r'\s+', ' ', original_text).strip()
            
            return f"\n[[SECTION_{clean_tag_content}]]\n{original_text}"
        
        item_section_pattern = r"(?m)^(\s*Item\s+\d+[A-Z]?\.\s+.*?)(?=\n|$)"
        cleaned_text = re.sub(item_section_pattern, create_section_tag, cleaned_text)
        
        part_section_pattern = r"(?m)^(\s*PART\s+[IVXLCDM]+\.?\s*.*?)(?=\n|$)"
        cleaned_text = re.sub(part_section_pattern, create_section_tag, cleaned_text)

        # remove ® and bullet points on their own lines
        cleaned_text = re.sub(r"(?:^|\n)\s*®\s*(?:\n|$)", " ", cleaned_text)
        cleaned_text = re.sub(r"(?m)^\s*•\s*$\n", "• ", cleaned_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r"Report of Independent Registered Public Accounting Firm[\s\S]*?\/s\/ [A-Za-z &]+ LLP", "", cleaned_text)

        return cleaned_text

    def parse(self) -> str:
        """
        Main method (Public API).
        Orchestrates the flow: Read -> Extract 10-K -> Clean HTML -> Return Text.
        """
        content = self._read_file()
        content = self._extract_10k_document(content)
        content = self._clean_html(content)

        with open("../data/parsed/parsed_10k.txt", "w", encoding="utf-8") as f:
            f.write(content)

        return content

if __name__ == "__main__":
    load_dotenv()
    parser = SECParser(os.getenv("RAW_APPLE_10K_PATH"), ticker="APPL", year="2024")
    
    parser.parse()
