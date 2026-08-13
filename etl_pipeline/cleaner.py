import re
import os

def clean_10K(file_path: str) -> None:
    with open(file_path, "r") as f:
        # print(f.read(10000))

        cleaned_doc = f.read()
        pattern = r"(?<=<)[\s\S]*?(?=>)"
        # cleaned_doc = re.sub(pattern, "", file)
        # cleaned_doc = re.sub(r"<>", "", cleaned_doc)
        # cleaned_doc = re.sub(r"&#", "", cleaned_doc)
        # cleaned_doc = re.sub(r"https?://\S+", "", cleaned_doc)
        print(cleaned_doc)

    with open("output_clean.txt", "w") as f:
        f.write(cleaned_doc)

if __name__ == "__main__":
    clean_10K("output.txt")