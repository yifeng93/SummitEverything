"""Heading-aware Markdown chunks with stable, content-version-bound identities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TextChunk:
    page_id: UUID
    content_sha256: str
    chunk_id: str
    heading: str
    text: str


def chunk_markdown(
    page_id: UUID, content_sha256: str, body: str, *, max_characters: int = 1200
) -> list[TextChunk]:
    sections: list[tuple[str, list[str]]] = []
    heading = ""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            if current:
                paragraphs.append("\n".join(current).strip())
                current = []
            if paragraphs or sections or heading:
                sections.append((heading, paragraphs))
            heading = match.group(1).strip()
            paragraphs = []
        elif line.strip():
            current.append(line)
        elif current:
            paragraphs.append("\n".join(current).strip())
            current = []
    if current:
        paragraphs.append("\n".join(current).strip())
    if paragraphs or heading or not sections:
        sections.append((heading, paragraphs))
    chunks: list[TextChunk] = []
    for section_heading, section_paragraphs in sections:
        segments: list[str] = []
        buffer = ""
        for paragraph in section_paragraphs:
            pieces = [
                paragraph[index : index + max_characters]
                for index in range(0, len(paragraph), max_characters)
            ]
            for piece in pieces:
                candidate = f"{buffer}\n\n{piece}".strip() if buffer else piece
                if buffer and len(candidate) > max_characters:
                    segments.append(buffer)
                    buffer = piece
                else:
                    buffer = candidate
        if buffer:
            segments.append(buffer)
        for segment_index, text in enumerate(segments):
            identity = (
                f"{page_id}:{content_sha256}:{section_heading}:{segment_index}:{text}"
            ).encode()
            chunks.append(
                TextChunk(
                    page_id=page_id,
                    content_sha256=content_sha256,
                    chunk_id=hashlib.sha256(identity).hexdigest(),
                    heading=section_heading,
                    text=text,
                )
            )
    return chunks
