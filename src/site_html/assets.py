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
_DATA_GEN_DIR = _REPO_ROOT / "data" / "gen"


def assets_dir() -> Path:
    return _ASSETS_DIR


def data_gen_dir() -> Path:
    return _DATA_GEN_DIR


def _page_prefix(page: str) -> str:
    _, _, _, prefix = _resolve(page or "index.html")
    return prefix


def _normalize_bytes(content: str | bytes) -> bytes:
    if isinstance(content, bytes):
        return content.replace(b"\r\n", b"\n")
    return content.replace("\r\n", "\n").encode("utf-8")


def write_data_js(
    name: str,
    js_body: str,
    *,
    page: str = "",
    hashed: bool = True,
) -> tuple[str, str]:
    """
    Write a ``.js`` under ``data/gen/`` and return ``(href, digest)``.

    ``name`` is like ``h2h_wta.js`` (extension required). When ``hashed`` is
    True the file is ``h2h_wta.<digest>.js``; otherwise the filename is fixed
    and callers should append ``?v=<digest>`` themselves.
    """
    path_name = Path(name)
    stem, suffix = path_name.stem, path_name.suffix.lower()
    if not stem or suffix != ".js":
        raise ValueError(f"data js name must be like h2h_wta.js, got {name!r}")

    data = _normalize_bytes(js_body)
    digest = hashlib.sha256(data).hexdigest()[:8]
    filename = f"{stem}.{digest}{suffix}" if hashed else f"{stem}{suffix}"
    _DATA_GEN_DIR.mkdir(parents=True, exist_ok=True)
    out = _DATA_GEN_DIR / filename
    if hashed:
        if not out.exists():
            out.write_bytes(data)
    else:
        # Fixed name: rewrite when content changes so ?v= stays truthful.
        if not out.exists() or out.read_bytes() != data:
            out.write_bytes(data)
    href = f"{_page_prefix(page)}data/gen/{filename}"
    if not hashed:
        href = f"{href}?v={digest}"
    return href, digest


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

    data = _normalize_bytes(content)
    digest = hashlib.sha256(data).hexdigest()[:8]
    filename = f"{stem}.{digest}{suffix}"
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    out = _ASSETS_DIR / filename
    if not out.exists():
        out.write_bytes(data)

    return f"{_page_prefix(page)}assets/{filename}"


def cleanup_unused_assets(*, max_age_seconds: int = 86400) -> list[str]:
    """
    Delete hashed files under ``assets/`` and ``data/gen/`` that no HTML
    references and that are older than ``max_age_seconds`` (default 1 day).
    Always keeps ``echarts.min.js``. Fixed-name ``data/gen`` files (no hash
    infix) are left alone — they are rewritten in place.
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
        refs.update(re.findall(r"data/gen/([A-Za-z0-9._-]+)", text))

    keep_forever = {"echarts.min.js"}
    now = time.time()
    removed: list[str] = []

    def _is_hashed(name: str) -> bool:
        # stem.hash.ext — hash is 8 hex chars
        parts = name.split(".")
        return len(parts) >= 3 and len(parts[-2]) == 8 and all(
            c in "0123456789abcdef" for c in parts[-2]
        )

    for folder in (_ASSETS_DIR, _DATA_GEN_DIR):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.name in keep_forever or path.name in refs:
                continue
            if folder is _DATA_GEN_DIR and not _is_hashed(path.name):
                continue
            if now - path.stat().st_mtime < max_age_seconds:
                continue
            path.unlink(missing_ok=True)
            removed.append(path.name)
    return removed
