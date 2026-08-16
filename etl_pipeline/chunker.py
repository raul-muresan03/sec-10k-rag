from typing import List
import requests
from pprint import pprint
import math

def get_similarity_score(first: List[float], second: List[float]) -> float:
    if first is None or second is None:
        return -2

    dot_product = 0
    magnitude_first = 0
    magnitude_second = 0

    vector_size = len(first)

    for i in range(vector_size):
        dot_product += first[i] * second[i]
        magnitude_first += first[i] * first[i]
        magnitude_second += second[i] * second[i]

    if magnitude_first == 0 or magnitude_second == 0:
        return -2

    magnitude_first = math.sqrt(magnitude_first)
    magnitude_second = math.sqrt(magnitude_second)

    cosine_similarity = dot_product / (magnitude_first * magnitude_second)
    return cosine_similarity

def _text_2_vector_embedding(text: str) -> List[float]:
    url = "http://localhost:11434/api/embed"
    data = {
        "model": "nomic-embed-text",
        "input": text
    }

    response = requests.post(url=url, json=data)
    if response.status_code == 200:
        data = response.json()
        return data["embeddings"][0]
    else:
        print(f"Error: {response.status_code}")
        return []

def get_all_vector_embeddings(document: str) -> List[List[float]]:
    sentences = []
    for s in document.split("\n\n"):
        if s.strip():
            sentences.append(s)

    print(len(sentences))

    all_embeddings = []
    index = 1
    for sentence in sentences:
        embedding = _text_2_vector_embedding(sentence)
        all_embeddings.append(embedding)
        print(f"Embedding {index} is done!")
        index = index + 1

    return all_embeddings


def chunk_10K(file_path: str) -> List[float]:
    with open(file_path, "r") as f:
        document = f.read()
        all_embeddings = get_all_vector_embeddings(document)
        similarity_scores = []
        for i in range(len(all_embeddings)):
            if i + 1 < len(all_embeddings):
                score = get_similarity_score(all_embeddings[i], all_embeddings[i + 1])
                similarity_scores.append(score)

    return similarity_scores



if __name__ == "__main__":
    similarity_scores = chunk_10K("../data/output_cleaner.txt")
    print(f"similarity scores: {similarity_scores}")

# sample_text = "A total solar eclipse occurred at the Moon's descending node of orbit on Wednesday, 12 August 2026 with a magnitude of 1.0386. A solar eclipse occurs when the Moon passes between the Earth and the Sun, and totally or partly obscures the view of the Sun for a viewer on Earth. A total solar eclipse occurs when the Moon's apparent diameter is larger than the Sun's, blocking all direct sunlight. Totality occurs in a narrow path across Earth's surface, with the partial solar eclipse visible over a surrounding region thousands of kilometres wide. Because the eclipse occurred about 2.3 days after perigee (on 10 August 2026, at 11:18 UTC), the Moon's apparent diameter was visually extra-large."

# all_embeddings = get_all_vector_embeddings(sample_text)
# pprint(all_embeddings)