from typing import List
import requests
from math import sqrt
import json

def get_similarity_score(first: List[float], second: List[float]) -> float:
    if first is None or second is None:
        return -2

    dot_product = 0
    magnitude_first = 0
    magnitude_second = 0

    for i in range(len(first)):
        dot_product += first[i] * second[i]
        magnitude_first += first[i] * first[i]
        magnitude_second += second[i] * second[i]

    if magnitude_first == 0 or magnitude_second == 0:
        return -2

    magnitude_first = sqrt(magnitude_first)
    magnitude_second = sqrt(magnitude_second)

    cosine_similarity = dot_product / (magnitude_first * magnitude_second)
    return cosine_similarity

def text_to_embedding(text: str) -> List[float]:
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

def _get_all_paragraphs(document: str) -> List[str]:
    paragraphs = []
    for s in document.split("\n\n"):
        if s.strip():
            paragraphs.append(s)

    return paragraphs

def _get_all_vector_embeddings(paragraphs: List[str]) -> List[List[float]]:
    all_embeddings = []
    index = 1
    for paragraph in paragraphs:
        embedding = text_to_embedding(paragraph)
        all_embeddings.append(embedding)
        print(f"Embedding {index} is done!")
        index = index + 1

    return all_embeddings

def _get_all_paragraphs_lengths(paragraphs: List[str]) -> List[int]:
    lengths = []
    for paragraph in paragraphs:
        lengths.append(len(paragraph))

    return lengths

def chunk_10K(file_path: str) -> List[str]:
    with open(file_path, "r") as f:
        document = f.read()
        paragraphs = _get_all_paragraphs(document)
        paragraphs_lengths = _get_all_paragraphs_lengths(paragraphs)
        all_embeddings = _get_all_vector_embeddings(paragraphs)
        with open("../data/all_embeddings.json", "w") as f2:
            json.dump(all_embeddings, f2)

        similarity_scores = []
        for i in range(len(all_embeddings)):
            if i + 1 < len(all_embeddings):
                score = get_similarity_score(all_embeddings[i], all_embeddings[i + 1])
                similarity_scores.append(score)

    all_chunks = []
    current_chunk = paragraphs[0]
    current_chunk_length = paragraphs_lengths[0]
    for i in range(len(similarity_scores)):
        if similarity_scores[i] >= 0.6 and current_chunk_length < 10000:
            current_chunk += " " + paragraphs[i + 1]
            current_chunk_length += paragraphs_lengths[i + 1]
        else:
            all_chunks.append(current_chunk)
            current_chunk = paragraphs[i + 1]
            current_chunk_length = paragraphs_lengths[i + 1]

    all_chunks.append(current_chunk)

    chunk_embeddings = _get_all_vector_embeddings(all_chunks)
    with open("../data/all_chunks_embeddings.json", "w") as f:
        json.dump({"chunks": all_chunks, "embeddings": chunk_embeddings}, f)

    return all_chunks

if __name__ == "__main__":
    all_chunks = chunk_10K("../data/output_cleaner.txt")

    with open("../data/all_chunks.txt", "w") as f:
        for chunk in all_chunks:
            f.write(chunk)
            f.write("\n\n")
            f.write("=============================================================")
            f.write("\n\n")