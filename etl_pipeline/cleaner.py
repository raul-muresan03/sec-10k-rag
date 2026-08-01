import os
import re
from bs4 import BeautifulSoup

class SECCleaner:
    def __init__(self, file_content: str):
        self.file_content = file_content

    def remove_table_of_contents(self, text: str) -> str:
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

    def remove_part3_and_part4(self, text: str) -> str:
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

    def remove_empty_sections(self, text: str) -> str:
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

    def remove_noise_tags(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Removes noise tags (scripts, styles, images, links, XBRL-specific tags, hidden elements based on style).
        """
        for tag_name in ["script", "style", "header", "img", "a", "ix:header", "ix:hidden"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        for hidden in soup.find_all(['div', 'span'], style=True):
            if 'display:none' in hidden['style'].lower().replace(" ", ""):
                hidden.decompose()

        return soup

    def clean_tables(self, soup: BeautifulSoup) -> tuple[BeautifulSoup, dict[str, str]]:
        """
        1. Parses HTML tables into a matrix structure, handling 'colspan' attributes to preserve grid alignment.
        2.Normalizes table dimensions by padding short rows to create a rectangular matrix.
        3. Intelligently merges columns to handle financial formatting (e.g., detached '$' or '%') and shifts content to consolidate related data into a single column.
        4. Removes completely empty columns from tables to reduce noise.
        5. Replaces HTML tables with unique placeholders, then injects formatted Markdown tables with proper spacing after the initial text extraction.
        """

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

        return soup, table_placeholders

    def clean_footer(self, cleaned_text: str) -> str:
        """
        Replaces page footers (e.g., "Company | Year Form 10-K | Page") with `[[PAGE_X]]` markers for metadata extraction.
        """

        # {Company} | {year} Form 10-K | {number}
        footer_pattern = r"(?m)^.*?\|\s+\d{4}\s+Form\s+10-K\s+\|\s+(\d+)$"
        cleaned_text = re.sub(footer_pattern, r"\n[[PAGE_\1]]\n", cleaned_text)
        cleaned_text = re.sub(r"(?m)^\s*(\d{1,3})\s*$", r"\n[[PAGE_\1]]\n", cleaned_text)

        return cleaned_text

    def normalize_text(self, cleaned_text: str) -> str:
        """
        Normalizes "\xa0" (non-breaking spaces) and new lines
        """
        cleaned_text = cleaned_text.replace("\xa0", " ")
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
        cleaned_text = re.sub(r' *\n *', '\n', cleaned_text)

        return cleaned_text

    def remove_special_characters_and_bullet_points(self, cleaned_text: str) -> str:
        """
        Removes characters like '®' and '•', and also excessive new lines
        """
        cleaned_text = re.sub(r"(?:^|\n)\s*®\s*(?:\n|$)", " ", cleaned_text)
        cleaned_text = re.sub(r"(?m)^\s*•\s*$\n", "• ", cleaned_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r"Report of Independent Registered Public Accounting Firm[\s\S]*?\/s\/ [A-Za-z &]+ LLP", "", cleaned_text)

        return cleaned_text

    def filter_page_markers(self, cleaned_text: str) -> str:
        pattern = r"\[\[PAGE_(\d+)\]\]"
        matches = list(re.finditer(pattern, cleaned_text))

        if not matches:
            return cleaned_text

        valid_pages = set()
        current_page = 0

        for match in matches:
            page_val = int(match.group(1))
            if current_page == 0:
                if page_val <= 10:
                    valid_pages.add(page_val)
                    current_page = page_val
            else:
                if 0 <= (page_val - current_page) <= 3:
                    valid_pages.add(page_val)
                    current_page = page_val

        def _replace_invalid(match):
            page_val = int(match.group(1))
            if page_val in valid_pages:
                return match.group(0)
            else:
                return str(page_val)

        return re.sub(pattern, _replace_invalid, cleaned_text)

    def mark_sections(self, cleaned_text: str) -> str:
        """
        Marks document sections (e.g., "Item 1. Business", "PART I.") with `[[SECTION_...]]` markers for metadata.
        """
        def _create_section_tag(match):
            original_text = match.group(1)
            clean_tag_content = re.sub(r'\s+', ' ', original_text).strip()

            return f"\n[[SECTION_{clean_tag_content}]]\n{original_text}"

        item_section_pattern = r"(?m)^(\s*Item\s+\d+[A-Z]?\.\s+.*?)(?=\n|$)"
        cleaned_text = re.sub(item_section_pattern, _create_section_tag, cleaned_text, flags=re.IGNORECASE)

        part_section_pattern = r"(?m)^(\s*PART\s+[IVXLCDM]+\.?\s*.*?)(?=\n|$)"
        cleaned_text = re.sub(part_section_pattern, _create_section_tag, cleaned_text, flags=re.IGNORECASE)

        return cleaned_text

    def clean_html(self, html_content: str) -> str:
        """
        Pipeline for cleaning the HTML content, resulting a LLM-friendly text.
        """
        soup = BeautifulSoup(html_content, "lxml")
        self.remove_noise_tags(soup)
        _, table_placeholders = self.clean_tables(soup)

        cleaned_text = soup.get_text(separator="\n", strip=True)

        for placeholder, md_table in table_placeholders.items():
            cleaned_text = cleaned_text.replace(placeholder, "\n\n" + md_table + "\n\n")

        cleaned_text = self.clean_footer(cleaned_text)
        cleaned_text = self.normalize_text(cleaned_text)
        cleaned_text = self.remove_table_of_contents(cleaned_text)
        cleaned_text = self.remove_part3_and_part4(cleaned_text)
        cleaned_text = self.remove_empty_sections(cleaned_text)
        cleaned_text = self.mark_sections(cleaned_text)
        cleaned_text = self.remove_special_characters_and_bullet_points(cleaned_text)
        cleaned_text = self.filter_page_markers(cleaned_text)

        return cleaned_text

    def clean(self) -> str:
        content = self.clean_html(self.file_content)

        with open("../data/cleaned/clean_10k.txt", "w", encoding="utf-8") as f:
            f.write(content)

        return content

if __name__ == "__main__":
    with open(os.getenv("RAW_APPLE_10K_PATH")) as f:
        content = f.read()

    cleaner = SECCleaner(content)
    cleaner.clean()