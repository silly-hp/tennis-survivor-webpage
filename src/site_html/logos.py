"""Site logo SVG fragments.

Colours come from the active theme's CSS variables, so the logo follows the
surface theme (hard / clay / grass) and light/dark mode automatically:
frame = --ink, draw-bracket strings = --primary, ball = --secondary.
"""
from __future__ import annotations

_ACC = "stroke:var(--primary,#E8541A)"
_BALL = "fill:var(--secondary,#E8541A)"
_FRAME = "stroke:var(--ink,#1a2035)"

_LOGO_RACKET_INNER = f"""\
  <g style="{_ACC}" stroke-width="1.8" stroke-linecap="round" fill="none">
    <line x1="23" y1="28" x2="40" y2="28"/>
    <line x1="23" y1="37" x2="40" y2="37"/>
    <line x1="23" y1="51" x2="40" y2="51"/>
    <line x1="23" y1="60" x2="40" y2="60"/>
    <line x1="40" y1="28" x2="40" y2="37"/>
    <line x1="40" y1="51" x2="40" y2="60"/>
    <line x1="40" y1="32.5" x2="57" y2="32.5"/>
    <line x1="40" y1="55.5" x2="57" y2="55.5"/>
    <line x1="57" y1="32.5" x2="57" y2="55.5"/>
    <line x1="57" y1="44" x2="67" y2="44" stroke-width="2.2"/>
  </g>
  <circle cx="72" cy="44" r="5.5" style="{_BALL}"/>
  <circle cx="72" cy="44" r="2.5" style="fill:var(--surface,#ffffff)"/>"""

_LOGO_HANDLE = f"""\
  <g style="{_FRAME}" stroke-linecap="round" opacity=".8">
    <ellipse cx="50" cy="43" rx="33" ry="37" fill="none" stroke-width="2.5"/>
    <line x1="43" y1="79" x2="57" y2="79" stroke-width="3"/>
    <line x1="50" y1="80" x2="50" y2="96" stroke-width="4"/>
  </g>"""


def _logo_svg(mode: str = "light", size: int = 44, extra_style: str = "") -> str:
    """Return one logo SVG element.

    ``mode`` only picks the CSS class (``logo-light`` / ``logo-dark``) that the
    theme toggle shows or hides; both variants are drawn from theme variables.
    """
    display = "" if mode == "light" else "display:none;"
    return (
        f'<svg class="logo-{mode}" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 100 100" aria-hidden="true" '
        f'style="width:{size}px;height:{size}px;flex-shrink:0;{display}{extra_style}">\n'
        f"{_LOGO_HANDLE}\n{_LOGO_RACKET_INNER}\n</svg>"
    )


def _logo_pair(size: int = 44) -> str:
    return _logo_svg("light", size) + "\n" + _logo_svg("dark", size)
