from pathlib import Path

import pytest

from backend.app.rag.parser import (
    KBParseException,
    load_knowledge_base_directory,
    parse_kb_file,
    parse_markdown_content,
)


def test_parse_valid_markdown_content() -> None:
    raw = """---
id: KB-TEST-001
title: Test Document
category: Testing
tags: [alpha, beta]
status: approved
version: 1.0
---

# Title Heading
Some body text here.
"""
    fm, body = parse_markdown_content(raw, source_path="test.md")
    assert fm.id == "KB-TEST-001"
    assert fm.title == "Test Document"
    assert fm.category == "Testing"
    assert fm.tags == ["alpha", "beta"]
    assert fm.status == "approved"
    assert "Some body text here." in body


def test_parse_missing_front_matter() -> None:
    raw = "# No front matter here\nJust text."
    with pytest.raises(KBParseException, match="missing opening YAML front matter"):
        parse_markdown_content(raw)


def test_parse_invalid_yaml_front_matter() -> None:
    raw = """---
id: [unterminated list
---
Body
"""
    with pytest.raises(KBParseException, match="Failed to parse YAML front matter"):
        parse_markdown_content(raw)


def test_parse_missing_required_fields() -> None:
    raw = """---
title: Incomplete Front Matter
---
Body
"""
    with pytest.raises(KBParseException, match="Front matter validation failed"):
        parse_markdown_content(raw)


def test_path_traversal_prevention(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    outside_file = outside_dir / "secret.md"
    outside_file.write_text(
        "---\nid: KB-LEAK\ntitle: Leak\ncategory: C\nstatus: approved\n---\nSecret",
        encoding="utf-8",
    )

    with pytest.raises(KBParseException, match="Path traversal detected"):
        parse_kb_file(outside_file, base_dir=kb_dir)


def test_load_knowledge_base_directory(tmp_path: Path) -> None:
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    approved_file = kb_dir / "approved.md"
    approved_file.write_text(
        "---\nid: KB-APP-1\ntitle: App 1\ncategory: C1\nstatus: approved\n---\nApproved content",
        encoding="utf-8",
    )

    draft_file = kb_dir / "draft.md"
    draft_file.write_text(
        "---\nid: KB-DRF-1\ntitle: Draft 1\ncategory: C1\nstatus: draft\n---\nDraft content",
        encoding="utf-8",
    )

    archived_file = kb_dir / "archived.md"
    archived_file.write_text(
        "---\nid: KB-ARC-1\ntitle: Archived 1\ncategory: C1\nstatus: archived\n---\nArchived content",
        encoding="utf-8",
    )

    approved, skipped = load_knowledge_base_directory(kb_dir, only_approved=True)

    assert len(approved) == 1
    assert approved[0].front_matter.id == "KB-APP-1"
    assert len(skipped) == 2
    assert any("draft.md" in p for p in skipped)
    assert any("archived.md" in p for p in skipped)
