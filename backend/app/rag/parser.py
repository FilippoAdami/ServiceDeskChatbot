from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import ValidationError

from backend.app.rag.models import KBDocument, KBFrontMatter

logger = logging.getLogger(__name__)


class KBParseException(Exception):
    """Raised when a Markdown document fails front matter extraction or validation."""

    pass


def parse_markdown_content(raw_content: str, source_path: str = "") -> tuple[KBFrontMatter, str]:
    """Parse YAML front matter and body content from a raw Markdown string.

    Expects front matter enclosed between triple dashes:
    ---
    id: ...
    ---
    Body...
    """
    stripped = raw_content.lstrip()
    if not stripped.startswith("---"):
        raise KBParseException(f"Document {source_path} is missing opening YAML front matter '---'")

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        raise KBParseException(f"Document {source_path} is missing closing YAML front matter '---'")

    front_matter_raw = parts[1].strip()
    body_content = parts[2].strip()

    try:
        data = yaml.safe_load(front_matter_raw)
        if not isinstance(data, dict):
            raise KBParseException(f"Front matter in {source_path} is not a valid YAML dictionary")
    except yaml.YAMLError as e:
        raise KBParseException(f"Failed to parse YAML front matter in {source_path}: {e}") from e

    try:
        front_matter = KBFrontMatter(**data)
    except ValidationError as e:
        raise KBParseException(f"Front matter validation failed for {source_path}: {e}") from e

    return front_matter, body_content


def parse_kb_file(file_path: Path, base_dir: Optional[Path] = None) -> Optional[KBDocument]:
    """Read and parse a Markdown document from disk.

    Validates that:
    1. The path exists and has .md extension.
    2. The path is within the allowed base_dir (if provided), preventing directory traversal.
    3. YAML front matter is valid.
    """
    resolved_path = file_path.resolve()
    if base_dir is not None:
        resolved_base = base_dir.resolve()
        try:
            resolved_path.relative_to(resolved_base)
        except ValueError:
            raise KBParseException(f"Path traversal detected: {file_path} is outside {base_dir}")

    if not resolved_path.is_file() or resolved_path.suffix.lower() != ".md":
        raise KBParseException(f"Target is not a Markdown file: {file_path}")

    raw_text = resolved_path.read_text(encoding="utf-8")
    rel_path = str(file_path)

    front_matter, content = parse_markdown_content(raw_text, source_path=rel_path)
    return KBDocument(
        front_matter=front_matter,
        content=content,
        source_path=rel_path,
        raw_text=raw_text,
    )


def load_knowledge_base_directory(
    base_dir: Path,
    only_approved: bool = True,
) -> tuple[List[KBDocument], List[str]]:
    """Scan directory recursively for all .md files, parse them, and return approved documents.

    Returns:
        (approved_documents, skipped_document_paths)
    """
    if not base_dir.exists() or not base_dir.is_dir():
        logger.warning("Knowledge base directory does not exist: %s", base_dir)
        return [], []

    approved_docs: List[KBDocument] = []
    skipped_paths: List[str] = []

    for file_path in sorted(base_dir.rglob("*.md")):
        try:
            doc = parse_kb_file(file_path, base_dir=base_dir)
            if doc is None:
                continue

            if only_approved:
                if doc.front_matter.status.lower() == "approved":
                    approved_docs.append(doc)
                else:
                    logger.info(
                        "Skipping non-approved KB document %s (status=%s)",
                        file_path.name,
                        doc.front_matter.status,
                    )
                    skipped_paths.append(str(file_path))
            else:
                approved_docs.append(doc)
        except Exception as e:
            logger.error("Failed to parse KB file %s: %s", file_path, e)
            skipped_paths.append(str(file_path))

    return approved_docs, skipped_paths
