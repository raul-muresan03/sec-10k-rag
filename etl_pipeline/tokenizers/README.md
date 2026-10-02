# Bundled BGE tokenizer

`bge-small-en-v1.5.json` is the unmodified `tokenizer.json` from
[`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5),
revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`.

SHA-256: `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`.

The model card declares MIT licensing. Its BERT WordPiece tokenizer is derived
from Google's BERT (Apache-2.0); the upstream Apache license is included here.
No model weights are bundled. Runtime loads this file locally with truncation
disabled and includes special tokens and the query instruction in input budgets.

Cloudflare does not publish an immutable model/tokenizer revision. This pinned
upstream tokenizer is the documented BGE tokenizer, not a claimed digest of the
provider's deployed weights. Document and query vectors always use Cloudflare,
explicit `mean` pooling, and provider-returned values without local normalization.
