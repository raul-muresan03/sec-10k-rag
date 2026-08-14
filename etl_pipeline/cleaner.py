import re
import os
from bs4 import BeautifulSoup

def clean_10K(file_path: str) -> None:
    with open(file_path, "r") as f:
        # print(f.read(10000))

        cleaned_doc = f.read()
        pattern_text = r"<TEXT>[\s\S]*?</TEXT>"
        cleaned_doc = re.search(pattern_text, cleaned_doc)
        cleaned_doc = cleaned_doc.group()

        pattern_ix_header = r"<ix\:header>[\s\S]*?</ix\:header>"
        cleaned_doc = re.sub(pattern_ix_header, "", cleaned_doc)

        soup = BeautifulSoup(cleaned_doc, "lxml")

        # for tag_name in []
        # for tag in soup.find_all("div"):
            # tag.decompose()

        cleaned_doc = soup.prettify()

        print(cleaned_doc)

    with open("output_clean.txt", "w") as f:
        f.write(cleaned_doc)

if __name__ == "__main__":
    clean_10K("output.txt")