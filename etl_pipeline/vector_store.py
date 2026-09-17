from typing import List, Tuple
from etl_pipeline.chunker import text_to_embedding, get_similarity_score
import json

prompt_cache = {}

def get_most_similar_chunks(prompt: str, top_n: int) -> List[Tuple[str, float]]:
    with open("../data/all_chunks_embeddings.json") as f:
        data = json.load(f)

    chunks = data["chunks"]
    embeddings = data["embeddings"]
    cleaned_prompt= prompt.strip().lower()

    if cleaned_prompt in prompt_cache:
        prompt_embedding = prompt_cache[cleaned_prompt]
    else:
        prompt_embedding = text_to_embedding(cleaned_prompt)
        prompt_cache[cleaned_prompt] = prompt_embedding

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
