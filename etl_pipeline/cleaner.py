import re
import os
from bs4 import BeautifulSoup


#TODO - add [PAGE_N] and [SECTION_N] markers

#TODO
def _remove_table_of_contents(content: str) -> str:
    pass

#TODO
def _remove_empty_sections(content: str) -> str:
    pass

#TODO - refactor from clean_10K
def parse_tables(content: str) -> str:
    pass

def clean_10K(file_path: str) -> None:
    with open(file_path, "r") as f:

        cleaned_doc = f.read()
        pattern_text = r"<TEXT>[\s\S]*?</TEXT>"
        cleaned_doc = re.search(pattern_text, cleaned_doc)
        cleaned_doc = cleaned_doc.group()

        pattern_ix_header = r"<ix\:header>[\s\S]*?</ix\:header>"
        cleaned_doc = re.sub(pattern_ix_header, "", cleaned_doc)

        soup = BeautifulSoup(cleaned_doc, "lxml")

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
                    cell_text = cell.get_text(separator=" ", strip=True).replace("|", "")
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

        for tag in soup.find_all(['ix:nonnumeric', 'ix:nonfraction']):
            tag.unwrap()

        cleaned_doc = soup.get_text(separator=" ", strip=True)

        cleaned_doc = _remove_empty_sections(cleaned_doc)
        cleaned_doc = _remove_table_of_contents(cleaned_doc)


        for placeholder, md_table in table_placeholders.items():
            cleaned_doc = cleaned_doc.replace(placeholder, "\n\n" + md_table + "\n\n")

    with open("output_clean.txt", "w") as f:
        f.write(cleaned_doc)

if __name__ == "__main__":
    clean_10K("output.txt")