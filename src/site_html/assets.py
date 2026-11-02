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


def cleanup_unused_assets(*, max_age_seconds: int = 86400) -> list[str]:
    """
    Delete hashed assets under ``assets/`` that no HTML references and that are
    older than ``max_age_seconds`` (default 1 day). Always keeps ``echarts.min.js``.
    """
    import re
    import time

    root = _REPO_ROOT
    refs: set[str] = set()
    html_files = list(root.glob("*.html")) + list((root / "events").rglob("*.html"))
    for html_path in html_files:
        try:
            text = html_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        refs.update(re.findall(r"assets/([A-Za-z0-9._-]+)", text))

    keep_forever = {"echarts.min.js"}
    now = time.time()
    removed: list[str] = []
    if not _ASSETS_DIR.is_dir():
        return removed
    for path in sorted(_ASSETS_DIR.iterdir()):
        if not path.is_file() or path.name in keep_forever or path.name in refs:
            continue
        if now - path.stat().st_mtime < max_age_seconds:
            continue
        path.unlink(missing_ok=True)
        removed.append(path.name)
    return removed
