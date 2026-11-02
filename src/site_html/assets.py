"""Content-hashed static assets for shared CSS / JS (phase 3.1).

``asset_url`` writes ``assets/<stem>.<sha256[:8]><suffix>`` when missing and
returns a path relative to the page being generated. Pages are not wired to
this helper until 3.1-4 / 3.1-5.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from site_html.header import _resolve

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_DIR = _REPO_ROOT / "assets"


def assets_dir() -> Path:
    return _ASSETS_DIR


def asset_url(name: str, content: str | bytes, page: str = "") -> str:
    """
    Write ``assets/<stem>.<hash><suffix>`` (no rewrite if the file exists) and
    return the URL relative to ``page``.

    ``name`` must include an extension, e.g. ``site.css`` or ``table.js``.
    """
    path_name = Path(name)
    stem, suffix = path_name.stem, path_name.suffix.lower()
    if not stem or suffix not in {".css", ".js"}:
        raise ValueError(f"asset name must be like site.css / table.js, got {name!r}")

    if isinstance(content, bytes):
        data = content.replace(b"\r\n", b"\n")
    else:
        data = content.replace("\r\n", "\n").encode("utf-8")

    digest = hashlib.sha256(data).hexdigest()[:8]
    filename = f"{stem}.{digest}{suffix}"
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = _ASSETS_DIR / filename
    if not out.exists():
        out.write_bytes(data)

    _, _, _, prefix = _resolve(page or "index.html")
    return f"{prefix}assets/{filename}"
