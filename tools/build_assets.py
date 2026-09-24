# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools[woff]>=4.50", "uharfbuzz>=0.40"]
# ///
"""Build the SVG assets for the profile README.

The design is "Dark Liquid Glass": frosted glass panels over a slowly drifting
aurora on near-black, tuned to the portfolio's green so the README reads as the
night version of the site. Text is shaped with HarfBuzz and written out as
outlines in Inter and IBM Plex Mono, so the images look the same everywhere
without loading a font. Motion is CSS inside the SVGs, and it stops for anyone
whose system asks for reduced motion.

Run with either of:

    uv run tools/build_assets.py
    pip install "fonttools[woff]" uharfbuzz && python tools/build_assets.py

Fonts (OFL, from the @fontsource packages) are downloaded once from jsDelivr
and cached in the system temp directory. Set PROFILE_FONT_DIR to a folder that
already holds the .woff2 files to skip the download.
"""

from __future__ import annotations

import base64
import functools
import io
import logging
import math
import os
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from html import escape
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).resolve().parent
ASSETS_DIR = TOOLS_DIR.parent / "assets"
PORTRAIT = TOOLS_DIR / "portrait.jpg"

FONT_CDN = "https://cdn.jsdelivr.net/npm"
_PLEX = "@fontsource/ibm-plex-mono@5.2.7/files"
FONT_FILES = {
    "sans": "@fontsource-variable/inter@5.2.8/files/inter-latin-opsz-normal.woff2",
    "mono": f"{_PLEX}/ibm-plex-mono-latin-400-normal.woff2",
    "mono-medium": f"{_PLEX}/ibm-plex-mono-latin-500-normal.woff2",
}

# ---- Palette: the spec's glass, with the portfolio's green as the accent ----
BACKGROUND = "#06060a"
TEXT = "#f5f5f7"
BODY = "#b6b6c0"
LABEL = "#8a8a96"
ACCENT = "#6fb39a"
MINT = "#8fe3c2"
TEAL = "#6fd3e0"
BLUE = "#7fb6ff"
PEACH = "#ffb38a"
GRADIENT = (MINT, TEAL, BLUE)
GLOW_GREEN, GLOW_TEAL, GLOW_BLUE = "#27c485", "#16b6c8", "#2f6bff"

# ---- Content ----
NAME = "Dumindu Kumarapeli"
BADGE = "OPEN TO ML ROLES + RESEARCH"
TAGLINE = "I build research prototypes that ship."
AFFILIATION = "DATA SCIENCE · NSBM GREEN UNIVERSITY · SRI LANKA"
QUOTE = ("Reproducible pipelines.", "Honest limitations.", "Runnable systems.")
APOSTROPHE = "\u2019"  # typographic, for display text


@dataclass(frozen=True)
class Stat:
    eyebrow: str
    value: str
    caption: tuple[str, str]


STATS = (
    Stat("BUILT", "3 systems", ("end to end, from data", "to deployment")),
    Stat("AWARD", "NSRSIT 2026", ("Best Overall Research,", "session award")),
    Stat("TALK", "ICCMM 2026", ("accepted for an oral", "presentation")),
    Stat("PAPER", "ICACT 2026", ("submitted to Track 3,", "Digital Health")),
)


@dataclass(frozen=True)
class Project:
    slug: str
    name: str
    blurb: str
    tags: tuple[str, ...]


PROJECTS = (
    Project("owl", "OWL", "AI operations assistant for datacenters.", ("GEMINI", "PYTORCH", "MCP")),
    Project(
        "seshat",
        "Seshat",
        "Remembers what you tried in research, and why.",
        ("OLLAMA", "SQLITE", "REACT"),
    ),
    Project(
        "argus",
        "Argus",
        "Does a sensor-fusion map stay honest when sensors fail?",
        ("PYTHON", "NUMPY", "BAYESIAN"),
    ),
)


@dataclass(frozen=True)
class Publication:
    slug: str
    date: str
    status: str
    positive: bool  # green for published or accepted, neutral otherwise
    title: str
    venue: str


PUBLICATIONS = (
    Publication(
        "nsrsit",
        "2026",
        "PUBLISHED",
        True,
        "Privacy-preserving automated EDA with local LLMs",
        "NSRSIT 2026 · Best Overall Research, session award",
    ),
    Publication(
        "iccmm",
        "NOV 2026",
        "ACCEPTED · ORAL",
        True,
        "Timescale separation and model reduction in dengue forecasting",
        "ICCMM 2026 · University of Colombo",
    ),
    Publication(
        "icact",
        "2026",
        "SUBMITTED",
        False,
        "A regime audit for reproduction numbers in hybrid epidemic models",
        "ICACT 2026 · Track 3, Digital Health and Computational Life Sciences",
    ),
    Publication(
        "oncology",
        "2026",
        "UNDER REVIEW",
        False,
        "A composite clinical proxy for durable benefit in oncology",
        "Real-world clinicogenomic data",
    ),
)

BUTTONS = (
    ("portfolio", "Portfolio", True),
    ("cv", "CV", False),
    ("linkedin", "LinkedIn", False),
    ("email", "Email", False),
)

# Reliability curves from Argus (github.com/Dumee-25/Argus), using the worlds,
# seeds, trial count and step count of experiments/trust_misspecification.py:
# 2000 trials of 15 steps, thermal sensor alone, true decoy rate 0.35. Each
# pair is (mean stated confidence, observed frequency) for one occupied bin.
HONEST = (  # assumed decoy rate 0.35, the sensor's real one
    (0.0634, 0.0696),
    (0.1600, 0.1427),
    (0.2554, 0.2525),
    (0.3500, 0.3463),
    (0.4491, 0.4417),
    (0.5468, 0.5679),
    (0.6479, 0.6498),
    (0.7458, 0.7390),
    (0.8386, 0.8807),
    (0.9302, 0.9590),
)
OVERTRUSTED = (  # assumed decoy rate 0.0: told it never falls for a decoy
    (0.0981, 0.0811),
    (0.1425, 0.0687),
    (0.2516, 0.0831),
    (0.3504, 0.0605),
    (0.4505, 0.0550),
    (0.5475, 0.0465),
    (0.6479, 0.0454),
    (0.7488, 0.0460),
    (0.8490, 0.0443),
    (0.9331, 0.0447),
)

# One stylesheet for every asset. Durations follow the spec: the aurora drifts
# over 24 to 32 seconds, status dots pulse every 2 seconds.
STYLE = """
.d1,.d2,.d3,.halo,.ring,.star{transform-box:fill-box;transform-origin:center}
.d1{animation:d1 27s ease-in-out infinite alternate}
.d2{animation:d2 31s ease-in-out infinite alternate}
.d3{animation:d3 24s ease-in-out infinite alternate}
@keyframes d1{to{transform:translate(90px,36px) scale(1.18)}}
@keyframes d2{to{transform:translate(-120px,28px) scale(.9)}}
@keyframes d3{to{transform:translate(70px,-48px) scale(1.14)}}
.halo{animation:halo 2s ease-out infinite}
@keyframes halo{from{transform:scale(1);opacity:.6}to{transform:scale(2.8);opacity:0}}
.bob{animation:bob 3.2s ease-in-out infinite}
@keyframes bob{50%{transform:translateY(-7px)}}
.spin{animation:spin 6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.bounce{animation:bounce 1.3s ease-in-out infinite}
@keyframes bounce{50%{transform:translateY(-13px)}}
.ring{animation:ring 2.4s ease-out infinite}
@keyframes ring{from{transform:scale(.2);opacity:.9}to{transform:scale(1);opacity:0}}
.blink{animation:blink 1.8s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:.16}50%{opacity:1}}
.bar{animation:bar 1.6s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
@keyframes bar{0%,100%{transform:scaleY(.3)}50%{transform:scaleY(1)}}
.scan{animation:scan 2.6s ease-in-out infinite alternate}
@keyframes scan{from{transform:translateY(-24px)}to{transform:translateY(24px)}}
.hue{animation:hue 6s linear infinite}
@keyframes hue{0%,100%{fill:#8fe3c2}25%{fill:#6fd3e0}50%{fill:#7fb6ff}75%{fill:#ffb38a}}
.star{animation:star 2.8s ease-in-out infinite}
@keyframes star{0%,100%{transform:scale(.8);opacity:.7}50%{transform:scale(1.06);opacity:1}}
.flicker{animation:flicker 3.4s linear infinite}
@keyframes flicker{0%,40%,48%,56%,100%{opacity:1}44%{opacity:.3}52%{opacity:.55}}
.typing{animation:typing 1.2s ease-in-out infinite}
@keyframes typing{0%,60%,100%{opacity:.25;transform:none}
30%{opacity:1;transform:translateY(-3px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""".strip()

Axes = tuple[tuple[str, float], ...]


def display(weight: float = 700) -> Axes:
    """Inter at its display optical size, for headings."""
    return (("opsz", 32.0), ("wght", float(weight)))


def reading(weight: float = 400) -> Axes:
    """Inter at its text optical size, for body copy."""
    return (("opsz", 14.0), ("wght", float(weight)))


@dataclass(frozen=True)
class Run:
    """Placed text: SVG markup and the advance width it covers."""

    markup: str
    width: float


@dataclass(frozen=True)
class _Shaped:
    font: hb.Font
    scale: float
    glyphs: list[tuple[int, float, float]]  # glyph id, x and y offset in px
    width: float


@dataclass(frozen=True)
class Blob:
    """One light in the aurora: a soft radial glow."""

    cx: float
    cy: float
    rx: float
    ry: float
    colour: str
    opacity: float


def _number(value: float) -> str:
    return f"{value:.1f}".removesuffix(".0")


def _font_path(key: str) -> Path:
    filename = FONT_FILES[key].rsplit("/", 1)[-1]
    if local_dir := os.environ.get("PROFILE_FONT_DIR"):
        return Path(local_dir) / filename

    cached = Path(tempfile.gettempdir()) / "profile-readme-fonts" / filename
    if not cached.exists():
        url = f"{FONT_CDN}/{FONT_FILES[key]}"
        logger.info("downloading %s", url)
        cached.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            cached.write_bytes(response.read())
    return cached


@functools.cache
def _face(key: str) -> hb.Face:
    # HarfBuzz reads plain sfnt data, so the WOFF2 wrapper comes off first.
    with TTFont(_font_path(key)) as font:
        font.flavor = None
        sfnt = io.BytesIO()
        font.save(sfnt)
    return hb.Face(sfnt.getvalue())


def _shape(key: str, text: str, size: float, axes: Axes, tracking: float) -> _Shaped:
    """Lay out `text` in px; `tracking` is extra letter spacing in em."""
    face = _face(key)
    font = hb.Font(face)
    if axes:
        font.set_variations(dict(axes))
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer, {"kern": True, "liga": True})

    scale = size / face.upem
    spacing = tracking * face.upem
    glyphs, cursor = [], 0.0
    for info, position in zip(buffer.glyph_infos, buffer.glyph_positions, strict=True):
        glyphs.append(
            (info.codepoint, (cursor + position.x_offset) * scale, -position.y_offset * scale)
        )
        cursor += position.x_advance + spacing
    width = (cursor - spacing) * scale if glyphs else 0.0
    return _Shaped(font, scale, glyphs, width)


def measure(key: str, text: str, size: float, *, axes: Axes = (), tracking: float = 0.0) -> float:
    """Advance width of `text` in px."""
    return _shape(key, text, size, axes, tracking).width


def fit(
    key: str, text: str, size: float, max_width: float, *, axes: Axes = (), tracking: float = 0.0
) -> float:
    """The largest size at or below `size` at which `text` fits `max_width`."""
    while size > 8 and measure(key, text, size, axes=axes, tracking=tracking) > max_width:
        size -= 0.5
    return size


def wrap(key: str, text: str, size: float, max_width: float, *, axes: Axes = ()) -> list[str]:
    """Greedy word wrap."""
    lines: list[str] = []
    for word in text.split():
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and measure(key, candidate, size, axes=axes) <= max_width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


class Canvas:
    """Collects shared definitions for one SVG document.

    Solid text draws each distinct glyph once in <defs> and places copies with
    <use>, which roughly halves the size of text-heavy assets. Gradient text is
    drawn as absolute outlines instead, because a user-space gradient would
    restart inside every <use>.
    """

    def __init__(self) -> None:
        self._glyphs: dict[tuple[str, Axes, float, int], str | None] = {}
        self._gradients: dict[str, str] = {}
        self._defs: list[str] = []
        self._count = 0

    def uid(self, prefix: str) -> str:
        self._count += 1
        return f"{prefix}{self._count}"

    def define(self, markup: str) -> None:
        self._defs.append(markup)

    def linear(
        self,
        stops: tuple[tuple[float, str, float], ...],
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        user_space: bool = False,
    ) -> str:
        """A linear gradient; identical ones are defined once."""
        units = ' gradientUnits="userSpaceOnUse"' if user_space else ""
        body = "".join(
            f'<stop offset="{offset}" stop-color="{colour}" stop-opacity="{opacity}"/>'
            for offset, colour, opacity in stops
        )
        spec = f'x1="{_number(x1)}" y1="{_number(y1)}" x2="{_number(x2)}" y2="{_number(y2)}"{units}'
        key = spec + body
        if key not in self._gradients:
            gradient_id = self.uid("lg")
            self.define(f'<linearGradient id="{gradient_id}" {spec}>{body}</linearGradient>')
            self._gradients[key] = gradient_id
        return self._gradients[key]

    def radial(self, colour: str, opacity: float) -> str:
        key = f"radial{colour}{opacity}"
        if key not in self._gradients:
            gradient_id = self.uid("rg")
            self.define(
                f'<radialGradient id="{gradient_id}">'
                f'<stop offset="0" stop-color="{colour}" stop-opacity="{opacity}"/>'
                f'<stop offset=".45" stop-color="{colour}" stop-opacity="{opacity * 0.45:.3f}"/>'
                f'<stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient>'
            )
            self._gradients[key] = gradient_id
        return self._gradients[key]

    def _glyph(self, key: str, axes: Axes, size: float, shaped: _Shaped, glyph: int) -> str | None:
        cache_key = (key, axes, size, glyph)
        if cache_key not in self._glyphs:
            pen = SVGPathPen(None, ntos=_number)
            scale = shaped.scale
            shaped.font.draw_glyph_with_pen(glyph, TransformPen(pen, (scale, 0, 0, -scale, 0, 0)))
            outline = pen.getCommands()
            glyph_id = self.uid("g") if outline else None
            if glyph_id:
                self.define(f'<path id="{glyph_id}" d="{outline}"/>')
            self._glyphs[cache_key] = glyph_id
        return self._glyphs[cache_key]

    def text(
        self,
        key: str,
        text: str,
        size: float,
        *,
        x: float,
        y: float,
        fill: str = TEXT,
        axes: Axes = (),
        tracking: float = 0.0,
        anchor: str = "start",
        gradient: tuple[str, ...] | None = None,
        opacity: float | None = None,
    ) -> Run:
        """Place `text` with its baseline at `y`, aligned to `x` by `anchor`."""
        shaped = _shape(key, text, size, axes, tracking)
        if anchor == "middle":
            x -= shaped.width / 2
        elif anchor == "end":
            x -= shaped.width
        alpha = f' fill-opacity="{opacity}"' if opacity is not None else ""

        if gradient:
            pen = SVGPathPen(None, ntos=_number)
            scale = shaped.scale
            for glyph, dx, dy in shaped.glyphs:
                placed = TransformPen(pen, (scale, 0, 0, -scale, x + dx, y + dy))
                shaped.font.draw_glyph_with_pen(glyph, placed)
            step = 1 / (len(gradient) - 1)
            stops = tuple((round(i * step, 3), colour, 1) for i, colour in enumerate(gradient))
            paint = self.linear(stops, x, 0, x + shaped.width, 0, user_space=True)
            return Run(f'<path fill="url(#{paint})"{alpha} d="{pen.getCommands()}"/>', shaped.width)

        uses = []
        for glyph, dx, dy in shaped.glyphs:
            glyph_id = self._glyph(key, axes, size, shaped, glyph)
            if glyph_id:
                uses.append(
                    f'<use href="#{glyph_id}" x="{_number(x + dx)}" y="{_number(y + dy)}"/>'
                )
        return Run(f'<g fill="{fill}"{alpha}>{"".join(uses)}</g>', shaped.width)

    def document(self, width: float, height: float, title: str, body: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{_number(width)}" '
            f'height="{_number(height)}" viewBox="0 0 {_number(width)} {_number(height)}" '
            f'role="img"><title>{escape(title)}</title><style>{STYLE}</style>'
            f"<defs>{''.join(self._defs)}</defs>{body}</svg>\n"
        )


# ---- Surfaces ----


def backdrop(
    canvas: Canvas,
    width: float,
    height: float,
    radius: float,
    blobs: tuple[Blob, ...],
    *,
    animate: bool,
) -> str:
    """Near-black, the aurora, and a dark fade toward the bottom."""
    clip = canvas.uid("clip")
    canvas.define(
        f'<clipPath id="{clip}"><rect width="{width}" height="{height}" rx="{radius}"/></clipPath>'
    )
    lights = []
    for index, blob in enumerate(blobs):
        motion = f' class="d{index % 3 + 1}"' if animate else ""
        lights.append(
            f'<ellipse{motion} cx="{blob.cx}" cy="{blob.cy}" rx="{blob.rx}" ry="{blob.ry}" '
            f'fill="url(#{canvas.radial(blob.colour, blob.opacity)})"/>'
        )
    fade = canvas.linear(((0.5, BACKGROUND, 0), (1, BACKGROUND, 0.75)), 0, 0, 0, 1)
    return (
        f'<g clip-path="url(#{clip})"><rect width="{width}" height="{height}" '
        f'fill="{BACKGROUND}"/>{"".join(lights)}'
        f'<rect width="{width}" height="{height}" fill="url(#{fade})"/></g>'
    )


def glass(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    r: float,
    *,
    glare: bool = True,
    strength: float = 1.0,
) -> str:
    """A frosted panel: white fill at 8% fading to 2% at 155 degrees, a thin
    light along the top edge, glare over the top 40%, and a hairline border."""
    fill = canvas.linear(
        ((0, "#fff", round(0.08 * strength, 3)), (1, "#fff", round(0.02 * strength, 3))),
        0.29,
        0.05,
        0.71,
        0.95,
    )
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#{fill})"/>']
    if glare:
        sheen = canvas.linear(((0, "#fff", 0.08), (0.4, "#fff", 0)), 0, 0, 0, 1)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#{sheen})"/>'
        )
    edge = canvas.linear(
        ((0, "#fff", 0), (0.5, "#fff", 0.24), (1, "#fff", 0)), x, 0, x + w, 0, user_space=True
    )
    parts.append(
        f'<path d="M{_number(x + r)} {_number(y + 0.8)}H{_number(x + w - r)}" '
        f'stroke="url(#{edge})" stroke-width="1.2" fill="none"/>'
        f'<rect x="{_number(x + 0.5)}" y="{_number(y + 0.5)}" width="{_number(w - 1)}" '
        f'height="{_number(h - 1)}" rx="{_number(r - 0.5)}" fill="none" stroke="#fff" '
        'stroke-opacity=".11"/>'
    )
    return "".join(parts)


def status_dot(x: float, y: float, r: float, colour: str, *, pulse: bool) -> str:
    halo = (
        (f'<circle class="halo" cx="{_number(x)}" cy="{_number(y)}" r="{r}" fill="{colour}"/>')
        if pulse
        else ""
    )
    return halo + f'<circle cx="{_number(x)}" cy="{_number(y)}" r="{r}" fill="{colour}"/>'


def chip(
    canvas: Canvas,
    x: float,
    cy: float,
    text: str,
    *,
    positive: bool | None,
    size: float = 13,
    pulse: bool = False,
    anchor: str = "start",
) -> tuple[str, float]:
    """A pill label. positive=True is green, False neutral, None a plain tag."""
    tracking = 0.12
    text_width = measure("mono-medium", text, size, tracking=tracking)
    height = size * 2.35
    has_dot = positive is not None
    width = (size * 2.8 if has_dot else size * 1.6) + text_width + size * 1.3
    if anchor == "end":
        x -= width
    elif anchor == "middle":
        x -= width / 2

    if positive:
        fill, stroke, ink = (
            f'fill="{ACCENT}" fill-opacity=".14"',
            f'stroke="{ACCENT}" stroke-opacity=".4"',
            MINT,
        )
    elif positive is False:
        fill, stroke, ink = (
            'fill="#fff" fill-opacity=".06"',
            'stroke="#fff" stroke-opacity=".14"',
            "#cfcfd6",
        )
    else:
        fill, stroke, ink = (
            'fill="#fff" fill-opacity=".05"',
            'stroke="#fff" stroke-opacity=".12"',
            BODY,
        )

    top = cy - height / 2
    parts = [
        f'<rect x="{_number(x)}" y="{_number(top)}" width="{_number(width)}" '
        f'height="{_number(height)}" rx="{_number(height / 2)}" {fill} {stroke}/>'
    ]
    text_x = x + size * 1.3
    if has_dot:
        parts.append(status_dot(x + size * 1.45, cy, size * 0.3, ink, pulse=pulse))
        text_x = x + size * 2.55
    parts.append(
        canvas.text(
            "mono-medium", text, size, x=text_x, y=cy + size * 0.36, fill=ink, tracking=tracking
        ).markup
    )
    return "".join(parts), width


def arrow(
    x: float, y: float, size: float, colour: str, *, diagonal: bool = False, width: float = 1.8
) -> str:
    """A drawn arrow, since the latin font subsets have none. (x, y) is its centre."""
    h = size / 2
    if diagonal:
        d = (
            f"M{_number(x - h)} {_number(y + h)}L{_number(x + h)} {_number(y - h)}"
            f"M{_number(x - h * 0.35)} {_number(y - h)}H{_number(x + h)}V{_number(y + h * 0.35)}"
        )
    else:
        d = (
            f"M{_number(x - h)} {_number(y)}H{_number(x + h)}"
            f"M{_number(x + h * 0.25)} {_number(y - h * 0.7)}L{_number(x + h)} {_number(y)}"
            f"L{_number(x + h * 0.25)} {_number(y + h * 0.7)}"
        )
    return (
        f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def eyebrow(
    canvas: Canvas, text: str, *, x: float, y: float, anchor: str = "start", size: float = 14
) -> str:
    return canvas.text(
        "mono-medium", text, size, x=x, y=y, fill=LABEL, tracking=0.18, anchor=anchor
    ).markup


# ---- Hero ----


def _portrait(canvas: Canvas, cx: float, cy: float, rx: float, ry: float) -> str:
    """The photo in a vertical oval, set in a glass ring."""
    clip = canvas.uid("oval")
    canvas.define(
        f'<clipPath id="{clip}"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/></clipPath>'
    )
    photo = base64.b64encode(PORTRAIT.read_bytes()).decode()
    rim = canvas.linear(
        ((0, "#fff", 0.55), (0.45, "#fff", 0.08), (1, "#fff", 0.3)), 0.15, 0, 0.85, 1
    )
    return (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 11}" ry="{ry + 11}" fill="#fff" '
        'fill-opacity=".06" stroke="#fff" stroke-opacity=".14"/>'
        f'<image href="data:image/jpeg;base64,{photo}" x="{cx - rx}" y="{cy - ry}" '
        f'width="{2 * rx}" height="{2 * ry}" preserveAspectRatio="xMidYMid slice" '
        f'clip-path="url(#{clip})"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" '
        f'stroke="url(#{rim})" stroke-width="2"/>'
    )


def hero(*, compact: bool) -> str:
    canvas = Canvas()
    if compact:
        width, height, radius, cx = 640, 836, 36, 320
        blobs = (
            Blob(150, 190, 330, 260, GLOW_GREEN, 0.34),
            Blob(520, 150, 300, 240, GLOW_TEAL, 0.26),
            Blob(330, 760, 420, 280, GLOW_BLUE, 0.32),
        )
        parts = [
            backdrop(canvas, width, height, radius, blobs, animate=True),
            glass(canvas, 18, 18, width - 36, height - 36, 32),
            _portrait(canvas, cx, 186, 80, 100),
        ]
        badge, _ = chip(
            canvas, cx, 344, BADGE, positive=True, size=14.5, pulse=True, anchor="middle"
        )
        parts.append(badge)
        for line, baseline in (("Dumindu", 456), ("Kumarapeli", 530)):
            parts.append(
                canvas.text(
                    "sans",
                    line,
                    70,
                    x=cx,
                    y=baseline,
                    axes=display(700),
                    tracking=-0.035,
                    anchor="middle",
                ).markup
            )
        for line, baseline in (("I build research prototypes", 606), ("that ship.", 650)):
            parts.append(
                canvas.text(
                    "sans",
                    line,
                    33,
                    x=cx,
                    y=baseline,
                    axes=display(600),
                    tracking=-0.01,
                    anchor="middle",
                    gradient=GRADIENT,
                ).markup
            )
        for line, baseline in (
            ("DATA SCIENCE UNDERGRADUATE", 734),
            ("NSBM GREEN UNIVERSITY · SRI LANKA", 768),
        ):
            parts.append(eyebrow(canvas, line, x=cx, y=baseline, anchor="middle", size=17))
    else:
        width, height, radius, cx = 1200, 680, 40, 600
        blobs = (
            Blob(280, 170, 480, 330, GLOW_GREEN, 0.32),
            Blob(940, 150, 430, 300, GLOW_TEAL, 0.24),
            Blob(640, 610, 580, 300, GLOW_BLUE, 0.3),
        )
        parts = [
            backdrop(canvas, width, height, radius, blobs, animate=True),
            glass(canvas, 28, 28, width - 56, height - 56, 36),
            _portrait(canvas, cx, 196, 86, 108),
        ]
        badge, _ = chip(
            canvas, cx, 358, BADGE, positive=True, size=13.5, pulse=True, anchor="middle"
        )
        parts.append(badge)
        parts.append(
            canvas.text(
                "sans", NAME, 74, x=cx, y=466, axes=display(700), tracking=-0.035, anchor="middle"
            ).markup
        )
        parts.append(
            canvas.text(
                "sans",
                TAGLINE,
                31,
                x=cx,
                y=520,
                axes=display(600),
                tracking=-0.01,
                anchor="middle",
                gradient=GRADIENT,
            ).markup
        )
        parts.append(eyebrow(canvas, AFFILIATION, x=cx, y=580, anchor="middle"))
    title = f"{NAME}. {TAGLINE} Open to ML roles and research."
    return canvas.document(width, height, title, "".join(parts))


# ---- Buttons ----


def button(label: str, *, primary: bool) -> str:
    canvas = Canvas()
    height, size, pad = 56, 19, 26
    text_width = measure("sans", label, size, axes=reading(600))
    width = round(pad + text_width + 12 + 12 + pad)
    if primary:
        base = f'<rect width="{width}" height="{height}" rx="14" fill="{ACCENT}"/>'
        ink, stroke = BACKGROUND, BACKGROUND
    else:
        base = f'<rect width="{width}" height="{height}" rx="14" fill="#0c0c12"/>' + glass(
            canvas, 0, 0, width, height, 14, glare=False, strength=1.4
        )
        ink, stroke = TEXT, BODY
    label_run = canvas.text(
        "sans", label, size, x=pad, y=height / 2 + size * 0.36, fill=ink, axes=reading(600)
    )
    body = (
        base
        + label_run.markup
        + arrow(pad + text_width + 12 + 6, height / 2, 11, stroke, diagonal=True)
    )
    return canvas.document(width, height, label, body)


# ---- Quote ----


def quote() -> str:
    canvas = Canvas()
    width, height = 1200, 340
    blobs = (Blob(230, 150, 420, 240, GLOW_GREEN, 0.2), Blob(980, 210, 430, 240, GLOW_BLUE, 0.22))
    parts = [backdrop(canvas, width, height, 36, blobs, animate=False)]
    for line, baseline in zip(QUOTE, (120, 188, 256), strict=True):
        parts.append(
            canvas.text(
                "sans",
                line,
                54,
                x=width / 2,
                y=baseline,
                axes=display(700),
                tracking=-0.03,
                anchor="middle",
                gradient=GRADIENT,
            ).markup
        )
    return canvas.document(width, height, " ".join(QUOTE), "".join(parts))


# ---- Tech stack motifs, each drawn in a 100 x 100 box centred on 0,0 ----


def _python() -> str:
    return (
        f'<rect class="bob" x="-31" y="-26" width="32" height="32" rx="9" fill="{BLUE}" '
        'fill-opacity=".9"/>'
        f'<rect class="bob" style="animation-delay:-1.6s" x="-1" y="-4" width="32" '
        f'height="32" rx="9" fill="{MINT}" fill-opacity=".9"/>'
    )


def _pytorch() -> str:
    return (
        '<circle r="26" fill="none" stroke="#fff" stroke-opacity=".2" stroke-dasharray="2 5"/>'
        f'<circle r="7" fill="{PEACH}"/>'
        f'<g class="spin" style="animation-duration:4.5s"><circle cx="26" r="5.5" '
        f'fill="{MINT}"/></g>'
    )


def _tensorflow() -> str:
    return "".join(
        f'<circle class="bounce" style="animation-delay:{delay}s" cx="{cx}" cy="8" r="7" '
        f'fill="{colour}"/>'
        for cx, delay, colour in ((-22, 0, PEACH), (0, 0.15, TEAL), (22, 0.3, BLUE))
    )


def _react() -> str:
    orbits = "".join(
        f'<ellipse rx="33" ry="12" transform="rotate({angle})" fill="none" stroke="{TEAL}" '
        'stroke-width="2"/>'
        for angle in (0, 60, 120)
    )
    nucleus = f'<circle r="5.5" fill="{TEAL}"/>'
    return f'<g class="spin" style="animation-duration:14s">{orbits}</g>{nucleus}'


def _postgres() -> str:
    rings = "".join(
        f'<circle class="ring" style="animation-delay:{delay}s" r="32" fill="none" '
        f'stroke="{BLUE}" stroke-width="2"/>'
        for delay in (0, -0.8, -1.6)
    )
    return rings + f'<circle r="6" fill="{BLUE}"/>'


def _cuda() -> str:
    cells = []
    for row in range(4):
        for col in range(4):
            cells.append(
                f'<rect class="blink" style="animation-delay:{(row + col) * 0.14:.2f}s" '
                f'x="{-31 + col * 16}" y="{-31 + row * 16}" width="12" height="12" rx="3" '
                f'fill="{MINT}"/>'
            )
    return "".join(cells)


def _polars() -> str:
    return "".join(
        f'<rect class="bar" style="animation-delay:{-index * 0.22:.2f}s" x="{-32 + index * 14}" '
        f'y="-26" width="9" height="52" rx="3" fill="{BLUE if index % 2 else TEAL}"/>'
        for index in range(5)
    )


def _opencv() -> str:
    corner = (
        'fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="2.2" stroke-linecap="round"'
    )
    corners = "".join(
        f'<path d="M{sx * 34} {sy * 20}V{sy * 34}H{sx * 20}" {corner}/>'
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1))
    )
    return (
        corners + '<g class="scan">'
        f'<rect x="-26" y="-7" width="52" height="14" fill="{MINT}" fill-opacity=".12"/>'
        f'<rect x="-26" y="-1" width="52" height="2" rx="1" fill="{MINT}"/></g>'
    )


def _chroma() -> str:
    return "".join(
        f'<circle class="hue" style="animation-delay:{delay}s" cx="{cx}" cy="{cy}" r="17" '
        'fill-opacity=".82"/>'
        for cx, cy, delay in ((-12, -8, 0), (12, -8, -2), (0, 13, -4))
    )


def _gemini() -> str:
    return (
        '<path class="star" d="M0 -34C3 -10 10 -3 34 0C10 3 3 10 0 34C-3 10 -10 3 -34 0'
        f'C-10 -3 -3 -10 0 -34Z" fill="{BLUE}"/>'
    )


def _fastapi() -> str:
    return (
        f'<circle r="30" fill="{TEAL}" fill-opacity=".1" stroke="{TEAL}" stroke-opacity=".45"/>'
        f'<path class="flicker" d="M5 -22L-12 4H0L-5 22L12 -4H0Z" fill="{TEAL}"/>'
    )


def _ollama() -> str:
    bubble = (
        '<path d="M-30 -18H30A8 8 0 0 1 38 -10V12A8 8 0 0 1 30 20H-12L-24 30V20H-30'
        'A8 8 0 0 1 -38 12V-10A8 8 0 0 1 -30 -18Z" fill="#fff" fill-opacity=".05" '
        'stroke="#fff" stroke-opacity=".38" stroke-width="1.8"/>'
    )
    dots = "".join(
        f'<circle class="typing" style="animation-delay:{delay}s" cx="{cx}" cy="1" r="4.5" '
        f'fill="{MINT}"/>'
        for cx, delay in ((-14, 0), (0, 0.2), (14, 0.4))
    )
    return bubble + dots


MOTIFS: dict[str, Callable[[], str]] = {
    "Python": _python,
    "PyTorch": _pytorch,
    "TensorFlow": _tensorflow,
    "React": _react,
    "PostgreSQL": _postgres,
    "CUDA": _cuda,
    "Polars": _polars,
    "OpenCV": _opencv,
    "ChromaDB": _chroma,
    "Gemini": _gemini,
    "FastAPI": _fastapi,
    "Ollama": _ollama,
}

# Twelve-column bento: (tool, column span) per row, each row summing to 12.
BENTO_ROWS = (
    (("Python", 4), ("CUDA", 2), ("PyTorch", 3), ("React", 3)),
    (("Polars", 3), ("OpenCV", 3), ("Gemini", 2), ("FastAPI", 4)),
    (("ChromaDB", 2), ("Ollama", 4), ("PostgreSQL", 3), ("TensorFlow", 3)),
)


def _tile(
    canvas: Canvas, tool: str, x: float, y: float, w: float, h: float, *, label_size: float
) -> str:
    wide = w / h > 1.9
    if wide:
        cx, cy, scale = x + w - h * 0.52, y + h / 2 - 4, min(1.0, (h - 40) / 90)
    else:
        cx, cy, scale = x + w / 2, y + (h - 38) / 2 + 4, min(1.0, (h - 64) / 84)
    motif = (
        f'<g transform="translate({_number(cx)} {_number(cy)}) scale({scale:.2f})">'
        f"{MOTIFS[tool]()}</g>"
    )
    label = canvas.text("sans", tool, label_size, x=x + 20, y=y + h - 20, axes=reading(600))
    return glass(canvas, x, y, w, h, 22, strength=0.9) + motif + label.markup


def bento(*, compact: bool) -> str:
    canvas = Canvas()
    if compact:
        width, pad, gap, tile_h, columns = 640, 20, 14, 132, 2
        tools = [tool for row in BENTO_ROWS for tool, _ in row]
        rows = (len(tools) + columns - 1) // columns
        top = 74
        height = top + rows * tile_h + (rows - 1) * gap + pad
        blobs = (
            Blob(120, 260, 300, 380, GLOW_GREEN, 0.18),
            Blob(520, 760, 300, 380, GLOW_BLUE, 0.2),
        )
        parts = [
            backdrop(canvas, width, height, 32, blobs, animate=False),
            eyebrow(canvas, "STACK", x=pad + 4, y=50, size=15),
        ]
        tile_w = (width - 2 * pad - gap) / columns
        for index, tool in enumerate(tools):
            row, col = divmod(index, columns)
            parts.append(
                _tile(
                    canvas,
                    tool,
                    pad + col * (tile_w + gap),
                    top + row * (tile_h + gap),
                    tile_w,
                    tile_h,
                    label_size=20,
                )
            )
    else:
        width, pad, gap, tile_h = 1200, 28, 14, 170
        top = 80
        rows = len(BENTO_ROWS)
        height = top + rows * tile_h + (rows - 1) * gap + pad
        blobs = (
            Blob(200, 180, 420, 280, GLOW_GREEN, 0.2),
            Blob(1000, 520, 460, 300, GLOW_BLUE, 0.22),
            Blob(640, 330, 380, 240, GLOW_TEAL, 0.12),
        )
        parts = [
            backdrop(canvas, width, height, 36, blobs, animate=False),
            eyebrow(canvas, "STACK", x=pad + 6, y=54),
        ]
        unit = (width - 2 * pad - 11 * gap) / 12
        for row_index, row in enumerate(BENTO_ROWS):
            x = pad
            y = top + row_index * (tile_h + gap)
            for tool, span in row:
                w = span * unit + (span - 1) * gap
                parts.append(_tile(canvas, tool, x, y, w, tile_h, label_size=19))
                x += w + gap
    title = "Stack: " + ", ".join(tool for row in BENTO_ROWS for tool, _ in row)
    return canvas.document(width, height, title, "".join(parts))


# ---- Stats strip ----


def _stat(
    canvas: Canvas, stat: Stat, x: float, y: float, w: float, h: float, *, scale: float
) -> str:
    """One stat tile. `scale` enlarges the type for the phone layout."""
    inner = w - 48
    size = fit("sans", stat.value, 34 * scale, inner, axes=display(700), tracking=-0.02)
    parts = [
        glass(canvas, x, y, w, h, 22),
        eyebrow(canvas, stat.eyebrow, x=x + 24, y=y + 38 * scale, size=12.5 * scale),
        canvas.text(
            "sans",
            stat.value,
            size,
            x=x + 24,
            y=y + 88 * scale,
            axes=display(700),
            tracking=-0.02,
            gradient=GRADIENT,
        ).markup,
    ]
    for index, line in enumerate(stat.caption):
        parts.append(
            canvas.text(
                "sans",
                line,
                17 * scale,
                x=x + 24,
                y=y + (124 + index * 24) * scale,
                fill=BODY,
                axes=reading(400),
            ).markup
        )
    return "".join(parts)


def stats(*, compact: bool) -> str:
    canvas = Canvas()
    gap = 14
    if compact:
        width, pad, columns, scale = 640, 20, 2, 1.2
    else:
        width, pad, columns, scale = 1200, 28, 4, 1.0
    tile_h = 176 * scale
    rows = len(STATS) // columns
    height = 2 * pad + rows * tile_h + (rows - 1) * gap
    tile_w = (width - 2 * pad - (columns - 1) * gap) / columns
    blobs = (
        Blob(width * 0.2, height * 0.3, width * 0.35, height * 0.9, GLOW_GREEN, 0.16),
        Blob(width * 0.85, height * 0.7, width * 0.35, height * 0.9, GLOW_BLUE, 0.18),
    )
    parts = [backdrop(canvas, width, height, 30, blobs, animate=False)]
    for index, stat in enumerate(STATS):
        row, col = divmod(index, columns)
        parts.append(
            _stat(
                canvas,
                stat,
                pad + col * (tile_w + gap),
                pad + row * (tile_h + gap),
                tile_w,
                tile_h,
                scale=scale,
            )
        )
    title = ". ".join(f"{s.value}: {' '.join(s.caption)}" for s in STATS)
    return canvas.document(width, height, title, "".join(parts))


# ---- Project previews, drawn in a 560 x 364 box ----


def _preview_frame(canvas: Canvas) -> str:
    grid = "".join(
        f'<path d="M{x} 0V364" stroke="#fff" stroke-opacity=".035"/>' for x in range(40, 560, 40)
    )
    grid += "".join(
        f'<path d="M0 {y}H560" stroke="#fff" stroke-opacity=".035"/>' for y in range(40, 364, 40)
    )
    return f'<rect width="560" height="364" rx="18" fill="#0a0a10"/>{grid}'


def _owl_art(canvas: Canvas) -> str:
    def signal(x: float, base: float, amplitude: float) -> float:
        return base + amplitude * (math.sin(x / 37) + 0.45 * math.sin(x / 13 + 1.3))

    xs = range(30, 531, 6)
    points = []
    for x in xs:
        y = signal(x, 196, 20)
        if 372 <= x <= 408:  # the anomaly
            y -= 110 * math.exp(-(((x - 390) / 9) ** 2))
        points.append((x, y))
    line = " ".join(f"{x},{y:.1f}" for x, y in points)
    area = f"M30 300L{line.replace(' ', 'L')}L530 300Z".replace(",", " ")
    fill = canvas.linear(((0, BLUE, 0.22), (1, BLUE, 0)), 0, 0, 0, 1)
    second = " ".join(f"{x},{signal(x + 90, 258, 9):.1f}" for x in xs)
    spike_y = min(y for x, y in points if 372 <= x <= 408)
    racks = "".join(
        f'<rect x="{34 + i * 50}" y="316" width="40" height="26" rx="6" '
        + (
            f'fill="{PEACH}" fill-opacity=".16" stroke="{PEACH}" stroke-opacity=".7"/>'
            f'<circle cx="{54 + i * 50}" cy="329" r="3" fill="{PEACH}"/>'
            if i == 7
            else 'fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".1"/>'
        )
        for i in range(10)
    )
    bars = "".join(
        f'<rect x="{58}" y="{y}" width="{w}" height="7" rx="3.5" fill="#fff" fill-opacity="{o}"/>'
        for y, w, o in ((46, 130, 0.22), (60, 150, 0.12), (74, 96, 0.12))
    )
    return (
        _preview_frame(canvas)
        + f'<path d="{area}" fill="url(#{fill})"/>'
        + f'<polyline points="{second}" fill="none" stroke="{MINT}" stroke-opacity=".45" '
        'stroke-width="1.6"/>'
        + f'<rect x="372" y="24" width="36" height="276" fill="{PEACH}" fill-opacity=".07"/>'
        + f'<path d="M390 28V300" stroke="{PEACH}" stroke-opacity=".6" stroke-dasharray="3 5"/>'
        + f'<polyline points="{line}" fill="none" stroke="{BLUE}" stroke-width="2.4" '
        'stroke-linejoin="round"/>'
        + status_dot(390, spike_y, 5, PEACH, pulse=True)
        + '<rect x="30" y="30" width="206" height="62" rx="14" fill="#fff" fill-opacity=".05" '
        'stroke="#fff" stroke-opacity=".12"/>'
        + f'<circle cx="46" cy="50" r="5" fill="{MINT}"/>'
        + bars
        + racks
    )


def _seshat_art(canvas: Canvas) -> str:
    nodes = (70, 146, 222, 298)
    parts = [
        _preview_frame(canvas),
        '<path d="M72 40V326" stroke="#fff" stroke-opacity=".14" stroke-width="2"/>',
    ]
    for index, y in enumerate(nodes):
        highlighted = index == 2
        parts.append(
            status_dot(
                72, y, 6 if highlighted else 5, MINT if highlighted else TEAL, pulse=highlighted
            )
        )
        stroke = (
            f'stroke="{MINT}" stroke-opacity=".6"'
            if highlighted
            else 'stroke="#fff" stroke-opacity=".1"'
        )
        parts.append(
            f'<rect x="94" y="{y - 24}" width="214" height="48" rx="11" fill="#fff" '
            f'fill-opacity="{0.08 if highlighted else 0.045}" {stroke}/>'
        )
        for row, (width, opacity) in enumerate(((150 - index * 12, 0.26), (104 + index * 9, 0.12))):
            parts.append(
                f'<rect x="110" y="{y - 11 + row * 14}" width="{width}" height="7" rx="3.5" '
                f'fill="#fff" fill-opacity="{opacity}"/>'
            )
    parts.append(
        '<rect x="336" y="40" width="196" height="286" rx="16" fill="#fff" '
        'fill-opacity=".04" stroke="#fff" stroke-opacity=".12"/>'
    )
    parts.append(
        f'<rect x="420" y="62" width="96" height="32" rx="12" fill="{ACCENT}" fill-opacity=".35"/>'
        '<rect x="352" y="110" width="164" height="112" rx="12" fill="#fff" fill-opacity=".07"/>'
    )
    for row, width in enumerate((128, 140, 96, 118)):
        parts.append(
            f'<rect x="366" y="{128 + row * 18}" width="{width}" height="7" rx="3.5" '
            'fill="#fff" fill-opacity=".2"/>'
        )
    parts.append(
        f'<rect x="366" y="236" width="72" height="24" rx="12" fill="{MINT}" fill-opacity=".12" '
        f'stroke="{MINT}" stroke-opacity=".7"/>'
        f'<circle cx="380" cy="248" r="3.5" fill="{MINT}"/>'
        '<rect x="390" y="245" width="38" height="6" rx="3" fill="#fff" fill-opacity=".45"/>'
    )
    parts.append(
        f'<path d="M366 248C340 248 334 222 308 222" fill="none" stroke="{MINT}" '
        'stroke-opacity=".7" stroke-dasharray="3 4" stroke-width="1.6"/>'
    )
    return "".join(parts)


def _argus_art(canvas: Canvas) -> str:
    left, top, size = 172, 30, 272

    def point(stated: float, observed: float) -> str:
        return f"{left + stated * size:.1f},{top + (1 - observed) * size:.1f}"

    parts = [
        _preview_frame(canvas),
        f'<rect x="{left}" y="{top}" width="{size}" height="{size}" fill="none" '
        'stroke="#fff" stroke-opacity=".16"/>',
    ]
    for step in (0.25, 0.5, 0.75):
        offset = step * size
        parts.append(
            f'<path d="M{left + offset:.1f} {top}V{top + size}'
            f'M{left} {top + offset:.1f}H{left + size}" '
            'stroke="#fff" stroke-opacity=".06"/>'
        )
    parts.append(
        f'<path d="M{left} {top + size}L{left + size} {top}" stroke="#fff" '
        'stroke-opacity=".35" stroke-dasharray="3 5"/>'
    )
    for series, colour in ((OVERTRUSTED, PEACH), (HONEST, MINT)):
        points = " ".join(point(*pair) for pair in series)
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-opacity=".25" '
            'stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="2.4" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        parts.extend(
            f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3.2" fill="{colour}"/>'
            for p in points.split()
        )
    for row, (text, colour) in enumerate((("honest", MINT), ("overtrusted", PEACH))):
        y = top + 28 + row * 22
        parts.append(
            f'<path d="M{left + 16} {y - 4.5}h18" stroke="{colour}" stroke-width="2.4" '
            'stroke-linecap="round"/>'
        )
        parts.append(canvas.text("mono", text, 13, x=left + 42, y=y, fill=BODY).markup)
    parts.append(
        canvas.text(
            "mono",
            "stated confidence",
            12.5,
            x=left + size,
            y=top + size + 22,
            fill=LABEL,
            anchor="end",
        ).markup
    )
    parts.append(
        f'<g transform="translate({left - 12} {top + size}) rotate(-90)">'
        + canvas.text("mono", "observed frequency", 12.5, x=0, y=0, fill=LABEL).markup
        + "</g>"
    )
    return "".join(parts)


ART: dict[str, Callable[[Canvas], str]] = {
    "owl": _owl_art,
    "seshat": _seshat_art,
    "argus": _argus_art,
}


def _tags(canvas: Canvas, tags: tuple[str, ...], x: float, cy: float, size: float) -> str:
    parts = []
    for tag in tags:
        markup, width = chip(canvas, x, cy, tag, positive=None, size=size)
        parts.append(markup)
        x += width + size * 0.8
    return "".join(parts)


def project_card(project: Project, *, compact: bool) -> str:
    canvas = Canvas()
    glow = {"owl": GLOW_BLUE, "seshat": GLOW_GREEN, "argus": GLOW_TEAL}[project.slug]
    if compact:
        width = 640
        art_x, art_y, art_scale = 20, 20, 600 / 560
        text_x, max_width = 44, 552
        title_y, blurb_y, blurb_size, line_gap = 474, 526, 29, 40
        tag_size, link_size = 16.5, 18
    else:
        width = 1200
        art_x, art_y, art_scale = 28, 28, 1.0
        text_x, max_width = 636, 516
        title_y, blurb_y, blurb_size, line_gap = 124, 180, 27, 38
        tag_size, link_size = 12.5, 14
    lines = wrap("sans", project.blurb, blurb_size, max_width, axes=reading(400))
    tags_y = blurb_y + len(lines) * line_gap + tag_size * 2.4
    link_y = 420 - 44 if not compact else tags_y + tag_size * 4.6
    height = 420 if not compact else link_y + 52
    blobs = (
        (Blob(300, 90, 420, 260, glow, 0.26), Blob(1040, 380, 380, 240, GLOW_GREEN, 0.12))
        if not compact
        else (
            Blob(520, 120, 360, 260, glow, 0.26),
            Blob(90, height - 90, 300, 220, GLOW_GREEN, 0.12),
        )
    )

    parts = [
        backdrop(canvas, width, height, 26, blobs, animate=False),
        glass(canvas, 0, 0, width, height, 26),
        f'<g transform="translate({art_x} {art_y}) scale({art_scale:.4f})">'
        f"{ART[project.slug](canvas)}</g>",
        canvas.text(
            "sans", project.name, 56, x=text_x, y=title_y, axes=display(700), tracking=-0.03
        ).markup,
    ]
    for index, line in enumerate(lines):
        parts.append(
            canvas.text(
                "sans",
                line,
                blurb_size,
                x=text_x,
                y=blurb_y + index * line_gap,
                fill=BODY,
                axes=reading(400),
            ).markup
        )
    parts.append(_tags(canvas, project.tags, text_x, tags_y, tag_size))
    link = canvas.text(
        "mono-medium", "REPOSITORY", link_size, x=text_x, y=link_y, fill=MINT, tracking=0.16
    )
    parts.append(
        link.markup
        + arrow(
            text_x + link.width + link_size * 1.4, link_y - link_size * 0.36, link_size * 0.86, MINT
        )
    )
    title = f"{project.name}: {project.blurb} {', '.join(project.tags).title()}. Repository."
    return canvas.document(width, height, title, "".join(parts))


# ---- Publications ----


def publication_row(pub: Publication, *, compact: bool) -> str:
    canvas = Canvas()
    if compact:
        width, title_size, line_gap = 640, 28, 37
        lines = wrap("sans", pub.title, title_size, 584, axes=display(600))
        venue_lines = wrap("sans", pub.venue, 20, 540, axes=reading(400))
        title_top = 112
        venue_y = title_top + (len(lines) - 1) * line_gap + 44
        height = venue_y + (len(venue_lines) - 1) * 28 + 34
        parts = [
            backdrop(
                canvas,
                width,
                height,
                22,
                (Blob(90, 40, 240, 120, GLOW_GREEN, 0.12),),
                animate=False,
            ),
            glass(canvas, 0, 0, width, height, 22, glare=False),
            eyebrow(canvas, pub.date, x=28, y=56, size=17),
        ]
        pill, _ = chip(
            canvas, width - 28, 50, pub.status, positive=pub.positive, size=15.5, anchor="end"
        )
        parts.append(pill)
        for index, line in enumerate(lines):
            parts.append(
                canvas.text(
                    "sans",
                    line,
                    title_size,
                    x=28,
                    y=title_top + index * line_gap,
                    axes=display(600),
                    tracking=-0.01,
                ).markup
            )
        for index, line in enumerate(venue_lines):
            parts.append(
                canvas.text(
                    "sans", line, 20, x=28, y=venue_y + index * 28, fill=LABEL, axes=reading(400)
                ).markup
            )
        parts.append(arrow(width - 40, venue_y + (len(venue_lines) - 1) * 28 - 7, 16, LABEL))
    else:
        width, height = 1200, 124
        parts = [
            backdrop(
                canvas,
                width,
                height,
                22,
                (Blob(120, 30, 300, 110, GLOW_GREEN, 0.12),),
                animate=False,
            ),
            glass(canvas, 0, 0, width, height, 22, glare=False),
            eyebrow(canvas, pub.date, x=32, y=height / 2 + 5, size=14.5),
        ]
        pill, pill_width = chip(
            canvas,
            width - 84,
            height / 2,
            pub.status,
            positive=pub.positive,
            size=12.5,
            anchor="end",
        )
        text_x = 168
        max_width = width - 84 - pill_width - 36 - text_x
        title_size = fit("sans", pub.title, 24, max_width, axes=display(600), tracking=-0.01)
        parts.append(
            canvas.text(
                "sans", pub.title, title_size, x=text_x, y=56, axes=display(600), tracking=-0.01
            ).markup
        )
        venue_size = fit("sans", pub.venue, 17, max_width, axes=reading(400))
        parts.append(
            canvas.text(
                "sans", pub.venue, venue_size, x=text_x, y=88, fill=LABEL, axes=reading(400)
            ).markup
        )
        parts.append(pill + arrow(width - 44, height / 2, 15, LABEL))
    title = f"{pub.date}, {pub.status.lower()}: {pub.title}. {pub.venue}."
    return canvas.document(width, height, title, "".join(parts))


# ---- Contact ----


def _mail_icon(x: float, cy: float, colour: str) -> str:
    return (
        f'<rect x="{x}" y="{cy - 8}" width="22" height="16" rx="3.5" fill="none" '
        f'stroke="{colour}" stroke-width="1.8"/>'
        f'<path d="M{x + 2} {cy - 5}L{x + 11} {cy + 1.5}L{x + 20} {cy - 5}" fill="none" '
        f'stroke="{colour}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def contact(*, compact: bool) -> str:
    canvas = Canvas()
    email = "duminduku.25@gmail.com"
    if compact:
        width, height, cx = 640, 480, 320
        blobs = (
            Blob(150, 110, 300, 200, GLOW_GREEN, 0.3),
            Blob(520, 400, 320, 220, GLOW_BLUE, 0.3),
        )
        panel = (18, 18, width - 36, height - 36, 32)
        heading_y, sub_lines, sub_y, button_cy, heading_size = (
            176,
            ("Open to ML roles and", "research collaboration."),
            232,
            368,
            60,
        )
        eyebrow_y = 96
    else:
        width, height, cx = 1200, 380, 600
        blobs = (
            Blob(260, 90, 440, 240, GLOW_GREEN, 0.3),
            Blob(960, 330, 460, 250, GLOW_BLUE, 0.3),
            Blob(640, 200, 320, 180, GLOW_TEAL, 0.12),
        )
        panel = (28, 28, width - 56, height - 56, 36)
        heading_y, sub_lines, sub_y, button_cy, heading_size = (
            172,
            ("Open to ML roles and research collaboration.",),
            216,
            290,
            62,
        )
        eyebrow_y = 94
    parts = [
        backdrop(canvas, width, height, 40, blobs, animate=True),
        glass(canvas, *panel),
        eyebrow(canvas, "CONTACT", x=cx, y=eyebrow_y, anchor="middle", size=16 if compact else 14),
        canvas.text(
            "sans",
            f"Let{APOSTROPHE}s talk.",
            heading_size,
            x=cx,
            y=heading_y,
            axes=display(700),
            tracking=-0.035,
            anchor="middle",
            gradient=GRADIENT,
        ).markup,
    ]
    for index, line in enumerate(sub_lines):
        parts.append(
            canvas.text(
                "sans",
                line,
                23 if compact else 21,
                x=cx,
                y=sub_y + index * 32,
                fill=BODY,
                axes=reading(400),
                anchor="middle",
            ).markup
        )
    email_width = measure("sans", email, 21, axes=reading(600))
    button_w = 24 + 22 + 14 + email_width + 26
    bx = cx - button_w / 2
    parts.append(
        f'<rect x="{bx:.1f}" y="{button_cy - 30}" width="{button_w:.1f}" height="60" '
        f'rx="14" fill="{ACCENT}"/>'
    )
    parts.append(_mail_icon(bx + 24, button_cy, BACKGROUND))
    parts.append(
        canvas.text(
            "sans",
            email,
            21,
            x=bx + 24 + 22 + 14,
            y=button_cy + 7.5,
            fill=BACKGROUND,
            axes=reading(600),
        ).markup
    )
    title = f"Let{APOSTROPHE}s talk. Open to ML roles and research collaboration. Email {email}."
    return canvas.document(width, height, title, "".join(parts))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ASSETS_DIR.mkdir(exist_ok=True)
    outputs = {
        "hero.svg": hero(compact=False),
        "hero-compact.svg": hero(compact=True),
        "quote.svg": quote(),
        "stack.svg": bento(compact=False),
        "stack-compact.svg": bento(compact=True),
        "stats.svg": stats(compact=False),
        "stats-compact.svg": stats(compact=True),
        "contact.svg": contact(compact=False),
        "contact-compact.svg": contact(compact=True),
    }
    for slug, label, primary in BUTTONS:
        outputs[f"button-{slug}.svg"] = button(label, primary=primary)
    for project in PROJECTS:
        outputs[f"project-{project.slug}.svg"] = project_card(project, compact=False)
        outputs[f"project-{project.slug}-compact.svg"] = project_card(project, compact=True)
    for pub in PUBLICATIONS:
        outputs[f"pub-{pub.slug}.svg"] = publication_row(pub, compact=False)
        outputs[f"pub-{pub.slug}-compact.svg"] = publication_row(pub, compact=True)

    for filename, svg in outputs.items():
        (ASSETS_DIR / filename).write_text(svg, encoding="utf-8", newline="\n")
        logger.info("wrote assets/%s (%.1f kB)", filename, len(svg.encode()) / 1024)


if __name__ == "__main__":
    main()
