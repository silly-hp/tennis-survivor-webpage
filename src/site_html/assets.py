"""Content-hashed static assets for shared CSS / JS (phase 3.1).

``asset_url`` writes ``assets/<stem>.<sha256[:8]><suffix>`` when missing and
returns a path relative to the page being generated. Pages are not wired to
this helper until 3.1-4 / 3.1-5.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import time
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


_HD_TIME_RE = re.compile(r'(<span class="hd-time">)[^<]*(</span>)')


def _mask_volatile(text: str) -> str:
    return _HD_TIME_RE.sub(r"\1\2", text)


def write_page(path: str | Path, html_str: str) -> bool:
    """
    Write a generated HTML page unless only its header "更新" time changed.

    Every run stamps the current time into ``.hd-time``; rewriting ~170 event
    pages for that alone churned git every 15 minutes and defeated browser
    revalidation. The kept page shows when its content last changed.
    Returns True when the file was (re)written.
    """
    out = Path(path)
    data = html_str
    try:
        old = out.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        old = None
    if old is not None and (
        old == data or _mask_volatile(old) == _mask_volatile(data)
    ):
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(data, encoding="utf-8")
    return True


_REF_RE = re.compile(r"(?:assets|data/gen)/([A-Za-z0-9._-]+)")


def _is_hashed(name: str) -> bool:
    """``stem.<8 hex>.ext`` — only these are ever pruned."""
    parts = name.split(".")
    return len(parts) >= 3 and len(parts[-2]) == 8 and all(
        c in "0123456789abcdef" for c in parts[-2]
    )


def _refs_on_disk(root: Path) -> set[str]:
    refs: set[str] = set()
    html_files = list(root.glob("*.html")) + list((root / "events").rglob("*.html"))
    for html_path in html_files:
        try:
            text = html_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        refs.update(_REF_RE.findall(text))
    return refs


def _refs_at_head(root: Path) -> set[str] | None:
    """
    Asset names referenced by the HTML committed at ``HEAD`` (= what is live
    right now). ``None`` when git is unavailable, so callers can fall back.
    """
    try:
        proc = subprocess.run(
            [
                "git", "grep", "-h", "-o", "-I", "-E",
                r"(assets|data/gen)/[A-Za-z0-9._-]+",
                "HEAD", "--", "*.html",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # git grep: 0 = matches, 1 = no matches, anything else = error
    if proc.returncode not in (0, 1):
        return None
    return set(_REF_RE.findall(proc.stdout))


def cleanup_unused_assets(*, max_age_seconds: int = 86400) -> list[str]:
    """
    Delete hashed files under ``assets/`` and ``data/gen/`` that are referenced
    neither by the HTML on disk (just generated) nor by the HTML committed at
    ``HEAD`` (currently published). Keeping the ``HEAD`` generation means a
    page a visitor already has open can still load its assets after the
    publish; anything older is removed.

    File ``mtime`` is not used when git is available: CI checks out a fresh
    tree, so every file looks brand new there and an age rule never fires.
    Without git, falls back to "unreferenced and older than
    ``max_age_seconds``".

    Always keeps ``echarts.min.js`` and any non-hashed file (fixed-name
    ``data/gen`` files are rewritten in place).
    """
    root = _REPO_ROOT
    refs = _refs_on_disk(root)
    head_refs = _refs_at_head(root)
    use_age = head_refs is None
    if head_refs:
        refs |= head_refs

    keep_forever = {"echarts.min.js"}
    now = time.time()
    removed: list[str] = []

    for folder in (_ASSETS_DIR, _DATA_GEN_DIR):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            name = path.name
            if not path.is_file() or name in keep_forever or name in refs:
                continue
            if not _is_hashed(name):
                continue
            if use_age and now - path.stat().st_mtime < max_age_seconds:
                continue
            path.unlink(missing_ok=True)
            removed.append(name)
    return removed
