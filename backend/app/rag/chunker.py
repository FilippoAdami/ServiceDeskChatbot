from __future__ import annotations

import re
from typing import List

from backend.app.rag.models import KBChunk, KBDocument


def slugify(text: str) -> str:
    """Convert heading text to a URL/ID friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "section"


def chunk_document(
    doc: KBDocument,
    max_chunk_chars: int = 1500,
    chunk_overlap_chars: int = 200,
) -> List[KBChunk]:
    """Split a Markdown document into semantic chunks based on headings (#, ##, ###).

    Each chunk contains:
    - Deterministic chunk_id: '{doc_id}#{slug}#{index}'
    - Source metadata: doc_id, doc_title, category, heading, source_path
    - Contextual text: Document title and heading breadcrumbs prepended to section body.
    """
    lines = doc.content.splitlines()
    sections: List[tuple[str, List[str]]] = []
    current_heading = "Introduzione"
    current_lines: List[str] = []

    heading_regex = re.compile(r"^(#{1,3})\s+(.+)$")

    for line in lines:
        match = heading_regex.match(line.strip())
        if match:
            # If we already have lines accumulated, save previous section
            if current_lines:
                sections.append((current_heading, current_lines))
                current_lines = []
            heading_text = match.group(2).strip()
            current_heading = heading_text
        else:
            current_lines.append(line)

    if current_lines or not sections:
        sections.append((current_heading, current_lines))

    chunks: List[KBChunk] = []
    chunk_global_index = 0

    for heading, section_lines in sections:
        body = "\n".join(section_lines).strip()
        if not body:
            # Skip empty sections (e.g., heading right after another heading)
            continue

        slug = slugify(heading)

        # If section is small enough, keep as single chunk
        if len(body) <= max_chunk_chars:
            chunk_id = f"{doc.front_matter.id}#{slug}#{chunk_global_index}"
            full_text = f"[{doc.front_matter.title} > {heading}]\n\n{body}"
            metadata = {
                "doc_id": doc.front_matter.id,
                "doc_title": doc.front_matter.title,
                "category": doc.front_matter.category,
                "heading": heading,
                "chunk_index": chunk_global_index,
                "source_path": doc.source_path,
                "tags": ", ".join(doc.front_matter.tags),
                "version": doc.front_matter.version,
            }
            chunks.append(
                KBChunk(
                    chunk_id=chunk_id,
                    doc_id=doc.front_matter.id,
                    doc_title=doc.front_matter.title,
                    category=doc.front_matter.category,
                    heading=heading,
                    chunk_index=chunk_global_index,
                    text=full_text,
                    source_path=doc.source_path,
                    metadata=metadata,
                )
            )
            chunk_global_index += 1
        else:
            # Split longer section into overlapping sub-chunks by paragraphs or sliding window
            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
            current_sub_lines: List[str] = []
            current_len = 0

            for para in paragraphs:
                para_len = len(para)
                if current_len + para_len > max_chunk_chars and current_sub_lines:
                    sub_body = "\n\n".join(current_sub_lines)
                    chunk_id = f"{doc.front_matter.id}#{slug}#{chunk_global_index}"
                    full_text = f"[{doc.front_matter.title} > {heading}]\n\n{sub_body}"
                    chunks.append(
                        KBChunk(
                            chunk_id=chunk_id,
                            doc_id=doc.front_matter.id,
                            doc_title=doc.front_matter.title,
                            category=doc.front_matter.category,
                            heading=heading,
                            chunk_index=chunk_global_index,
                            text=full_text,
                            source_path=doc.source_path,
                            metadata={
                                "doc_id": doc.front_matter.id,
                                "doc_title": doc.front_matter.title,
                                "category": doc.front_matter.category,
                                "heading": heading,
                                "chunk_index": chunk_global_index,
                                "source_path": doc.source_path,
                                "tags": ", ".join(doc.front_matter.tags),
                                "version": doc.front_matter.version,
                            },
                        )
                    )
                    chunk_global_index += 1

                    # Retain last paragraph for overlap if it doesn't exceed overlap budget
                    if len(current_sub_lines[-1]) <= chunk_overlap_chars:
                        current_sub_lines = [current_sub_lines[-1], para]
                        current_len = len(current_sub_lines[0]) + para_len
                    else:
                        current_sub_lines = [para]
                        current_len = para_len
                else:
                    current_sub_lines.append(para)
                    current_len += para_len

            if current_sub_lines:
                sub_body = "\n\n".join(current_sub_lines)
                chunk_id = f"{doc.front_matter.id}#{slug}#{chunk_global_index}"
                full_text = f"[{doc.front_matter.title} > {heading}]\n\n{sub_body}"
                chunks.append(
                    KBChunk(
                        chunk_id=chunk_id,
                        doc_id=doc.front_matter.id,
                        doc_title=doc.front_matter.title,
                        category=doc.front_matter.category,
                        heading=heading,
                        chunk_index=chunk_global_index,
                        text=full_text,
                        source_path=doc.source_path,
                        metadata={
                            "doc_id": doc.front_matter.id,
                            "doc_title": doc.front_matter.title,
                            "category": doc.front_matter.category,
                            "heading": heading,
                            "chunk_index": chunk_global_index,
                            "source_path": doc.source_path,
                            "tags": ", ".join(doc.front_matter.tags),
                            "version": doc.front_matter.version,
                        },
                    )
                )
                chunk_global_index += 1

    return chunks
