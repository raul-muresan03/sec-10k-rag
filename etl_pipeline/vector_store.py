from typing import List, Tuple
from chunker import text_2_vector_embedding, get_similarity_score
import json
import time

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
        prompt_embedding = text_2_vector_embedding(cleaned_prompt)
        prompt_cache[cleaned_prompt] = prompt_embedding

    scores = []
    for i in range(len(chunks)):
        score = get_similarity_score(embeddings[i], prompt_embedding)
        scores.append([score, chunks[i]])

    scores.sort(reverse=True)
    return scores[:top_n]


if __name__ == "__main__":
    start1 = time.time()
    result = get_most_similar_chunks("Who is the CEO in Nvidia?", 5)
    end1 = time.time()
    time1 = end1 - start1

    start2 = time.time()
    result = get_most_similar_chunks("Who is the CEO in Nvidia?", 5)
    end2 = time.time()
    time2 = end2 - start2

    # for score, chunk in result:
        # print("Score:", score)
        # # print(chunk)
        # print("-----------------------------")

    print(f"Before prompt caching: {time1}")        # 2.197699546813965 s
    print(f"After prompt caching: {time2}")         # 0.16060185432434082 s
