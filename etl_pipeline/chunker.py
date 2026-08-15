from typing import List
import requests
import json
from pprint import pprint


def cosine_similarity(a):
    pass

def get_similarity_score(text: str) -> float:
    pass

def get_all_vector_embeddings(document: str) -> List[List[float]]:
    sentences = extract_sentences(document)
    all_embeddings = []
    for sentence in sentences:
        embedding = text_2_vector_embedding(sentence)
        all_embeddings.append(embedding)

    return all_embeddings

def text_2_vector_embedding(text: str) -> List[float]:
    url = "http://localhost:11434/api/embed"
    data = {
        "model": "nomic-embed-text",
        "input": text
    }

    response = requests.post(url=url, json=data)
    if response.status_code == 200:
        data = response.json()
        return data["embeddings"]
    else:
        print(f"Error: {response.status_code}")

def extract_sentences(document: str) -> List[str]:
    sentences = document.split("\n\n")
    index = 0
    with open("../data/output_extract_sentences.txt", "a") as f:
        for sentence in sentences:
            f.write(str(index))
            f.write("\n")
            f.write(sentence)
            f.write("\n\n")
            index = index + 1

    return sentences

def chunk_10K(file_path: str) -> List[str]:
    with open(file_path, "r") as f:
        document = f.read()
        sentences = extract_sentences(document)

# if __name__ == "__main__":
    # chunks = chunk_10K("../data/output_cleaner.txt")
    # for chunk in chunks:
        # pass


sample_text = "A total solar eclipse occurred at the Moon's descending node of orbit on Wednesday, 12 August 2026 with a magnitude of 1.0386. A solar eclipse occurs when the Moon passes between the Earth and the Sun, and totally or partly obscures the view of the Sun for a viewer on Earth. A total solar eclipse occurs when the Moon's apparent diameter is larger than the Sun's, blocking all direct sunlight. Totality occurs in a narrow path across Earth's surface, with the partial solar eclipse visible over a surrounding region thousands of kilometres wide. Because the eclipse occurred about 2.3 days after perigee (on 10 August 2026, at 11:18 UTC), the Moon's apparent diameter was visually extra-large."

all_embeddings = get_all_vector_embeddings(sample_text)
# print(all_embeddings)
pprint(all_embeddings)