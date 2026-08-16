from typing import List, Tuple
from chunker import text_2_vector_embedding, get_similarity_score, chunk_10K
import json

def get_most_similar_chunks(prompt: str, top_n: int) -> List[Tuple[str, float]]:
    with open("../data/all_chunks_embeddings.json") as f:
        data = json.load(f)

    chunks = data["chunks"]
    embeddings = data["embeddings"]
    prompt_embedding = text_2_vector_embedding(prompt)

    scores = []
    for i in range(len(chunks)):
        score = get_similarity_score(embeddings[i], prompt_embedding)
        scores.append([score, chunks[i]])

    scores.sort(reverse=True)
    return scores[:top_n]


if __name__ == "__main__":
    result = get_most_similar_chunks("Who is the CEO in Nvidia?", 5)
    for score, chunk in result:
        print("Score:", score)
        print(chunk)
        print("-----------------------------")