from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional

from app.schemas.knowledge import DomainTopic, SourceTier


def calculate_content_hash(text: str) -> str:
    """Computes a deterministic SHA-256 hash of normalized text content."""
    normalized = " ".join(text.strip().split()).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


class DocumentCleaner:
    """
    Cleans raw document text, removing web/parsing artifacts while
    preserving semantic headings, section hierarchy, and medical content.
    """

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Normalize carriage returns and line endings
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip standard HTML tags if present (while preserving inner text)
        cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)

        # Remove repeated header/footer artifacts and common navigation text
        boilerplate_patterns = [
            r"(?i)^cookie policy.*$",
            r"(?i)^all rights reserved.*$",
            r"(?i)^terms of use.*$",
            r"(?i)^skip to main content.*$",
            r"(?i)^share this page:.*$",
        ]
        for pattern in boilerplate_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE)

        # Collapse excess empty lines (preserve max 2 consecutive newlines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Trim lines
        lines = [line.rstrip() for line in cleaned.split("\n")]
        return "\n".join(lines).strip()


class DocumentLoader:
    """
    Loads documents from various file formats (.md, .txt, .html)
    and extracts metadata and cleaned text.
    """

    @staticmethod
    def load_file(file_path: Path) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        raw_content = path.read_text(encoding="utf-8")
        cleaned_content = DocumentCleaner.clean(raw_content)
        content_hash = calculate_content_hash(cleaned_content)

        return {
            "file_name": path.name,
            "file_path": str(path.resolve()),
            "raw_content": raw_content,
            "cleaned_content": cleaned_content,
            "content_hash": content_hash,
            "extension": path.suffix.lower(),
        }
