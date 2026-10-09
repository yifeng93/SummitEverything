"""Replaceable local embedding boundary used by the M1 acceptance workflow."""

from __future__ import annotations

import hashlib
import math
import re


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for word in re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE):
        if re.search(r"[\u3400-\u9fff]", word):
            tokens.extend(word[index : index + 2] for index in range(len(word) - 1))
            if len(word) == 1:
                tokens.append(word)
        else:
            tokens.append(word)
    return tokens


class FakeEmbedding:
    """Deterministic hashed bag-of-words vectors; never contacts a model service."""

    dimensions = 64

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        self.calls += 1
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            seed = hashlib.sha256(f"{fingerprint}:{token}".encode()).digest()
            bucket = int.from_bytes(seed[:2], "big") % self.dimensions
            vector[bucket] += 1.0 if seed[2] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0
    return sum(a * b for a, b in zip(left, right, strict=True))
