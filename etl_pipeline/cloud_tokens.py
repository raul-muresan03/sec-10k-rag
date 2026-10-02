"""Pinned BGE tokenizer loaded from the bundle, never from the network."""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from tokenizers import Tokenizer

from etl_pipeline.model_errors import ModelInputError


TOKENIZER_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
TOKENIZER_SHA256 = "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"
TOKENIZER_PATH = Path(__file__).parent / "tokenizers" / "bge-small-en-v1.5.json"
CONTENT_TOKENS = 480
INPUT_TOKENS = 512
BATCH_TOKENS = 8192
BATCH_TEXTS = 100
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def tokenizer() -> Tokenizer:
    content = TOKENIZER_PATH.read_bytes()
    if sha256(content).hexdigest() != TOKENIZER_SHA256:
        raise ValueError("BGE tokenizer checksum mismatch")
    result = Tokenizer.from_str(content.decode("utf-8"))
    result.no_truncation()
    result.no_padding()
    return result


def token_count(text: str, *, special_tokens: bool = True) -> int:
    return len(tokenizer().encode(text, add_special_tokens=special_tokens).ids)


def validated_input(text: str, *, query: bool = False) -> str:
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 32_000:
        raise ModelInputError("Cloud embedding input must be nonempty and bounded")
    if token_count(text, special_tokens=False) > CONTENT_TOKENS:
        raise ModelInputError("Cloud embedding content exceeds 480 tokens")
    formatted = QUERY_PREFIX + text if query else text
    if token_count(formatted) > INPUT_TOKENS:
        raise ModelInputError("Cloud embedding input exceeds 512 tokens including formatting")
    return formatted
