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

import functools
import io
import logging
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
LANGUAGES = "PYTHON · TYPESCRIPT · SQL"
APOSTROPHE = "\u2019"  # typographic, for display text


@dataclass(frozen=True)
class Skill:
    """One area of work, the tools behind it, and the projects that show it."""

    motif: str
    name: str
    blurb: str
    tools: tuple[str, ...]
    seen_in: tuple[str, ...]


SKILLS = (
    Skill(
        "ollama",
        "LLM systems",
        "RAG, tool-using agents, model routing and grounded extraction.",
        ("GEMINI", "OLLAMA", "CHROMADB", "PGVECTOR", "MCP"),
        ("OWL", "TENAX", "FULYN", "DOC_EXTRACT"),
    ),
    Skill(
        "pytorch",
        "Scientific ML",
        "Epidemic models with learned parts, survival analysis and calibration checks.",
        ("PYTORCH", "CUDA", "TORCHDIFFEQ", "SCIKIT-SURVIVAL", "XGBOOST"),
        ("DENGUE", "ONCOLOGY", "ARGUS"),
    ),
    Skill(
        "opencv",
        "Vision and sensors",
        "Real-time detection and tracking, and a wearable IMU rig for gait data.",
        ("YOLOV8", "OPENCV", "BYTETRACK", "C++", "PLATFORMIO"),
        ("PEOPLE COUNTER", "GAIT"),
    ),
    Skill(
        "postgres",
        "Data engineering",
        "Postgres warehouses and pipelines for messy research data.",
        ("POSTGRESQL", "POLARS", "SQLALCHEMY", "ALEMBIC", "PLOTLY"),
        ("ALLEN BRAIN", "GAIT ANALYTICS"),
    ),
    Skill(
        "lock",
        "Privacy-first tools",
        "Analysis that runs locally, with differential privacy and PII detection.",
        ("OPENDP", "PRESIDIO", "OLLAMA", "SQLITE"),
        ("DATASENSE", "SESHAT"),
    ),
    Skill(
        "react",
        "Full-stack apps",
        "APIs, web apps and a packaged desktop app, with tests and type checks.",
        ("FASTAPI", "REACT", "TYPESCRIPT", "NEXT.JS", "DOCKER"),
        ("FULYN", "SESHAT", "TENAX"),
    ),
)


@dataclass(frozen=True)
class Stat:
    eyebrow: str
    value: str
    caption: tuple[str, str]


STATS = (
    Stat("BUILT", "4 systems", ("end to end, from data", "to deployment")),
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
    link: str = "REPOSITORY"  # the DataSense repo is private, so it links to its system page


PROJECTS = (
    Project(
        "datasense",
        "DataSense",
        "Audits a data file and suggests a model, without sending raw rows to an LLM.",
        ("POLARS", "OPENDP", "OLLAMA"),
        link="CASE STUDY",
    ),
    Project(
        "seshat",
        "Seshat",
        "Remembers what you tried in research, and why.",
        ("OLLAMA", "SQLITE", "REACT"),
    ),
    Project(
        "fulyn",
        "Fulyn",
        "Turns plain notes about your day into records you can ask about later.",
        ("OLLAMA", "PGVECTOR", "NEXT.JS"),
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
)

BUTTONS = (
    ("portfolio", "Portfolio", True),
    ("cv", "CV", False),
    ("linkedin", "LinkedIn", False),
    ("email", "Email", False),
)

# One stylesheet for every asset. Durations follow the spec: the aurora drifts
# over 24 to 32 seconds, status dots pulse every 2 seconds.
STYLE = """
.d1,.d2,.d3,.halo,.ring{transform-box:fill-box;transform-origin:center}
.d1{animation:d1 27s ease-in-out infinite alternate}
.d2{animation:d2 31s ease-in-out infinite alternate}
.d3{animation:d3 24s ease-in-out infinite alternate}
@keyframes d1{to{transform:translate(90px,36px) scale(1.18)}}
@keyframes d2{to{transform:translate(-120px,28px) scale(.9)}}
@keyframes d3{to{transform:translate(70px,-48px) scale(1.14)}}
.halo{animation:halo 2s ease-out infinite}
@keyframes halo{from{transform:scale(1);opacity:.6}to{transform:scale(2.8);opacity:0}}
.spin{animation:spin 6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.ring{animation:ring 2.4s ease-out infinite}
@keyframes ring{from{transform:scale(.2);opacity:.9}to{transform:scale(1);opacity:0}}
.blink{animation:blink 1.8s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:.16}50%{opacity:1}}
.scan{animation:scan 2.6s ease-in-out infinite alternate}
@keyframes scan{from{transform:translateY(-24px)}to{transform:translateY(24px)}}
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


def chip_width(text: str, size: float, *, dot: bool) -> float:
    """Outer width of the pill that `chip` draws for `text`."""
    text_width = measure("mono-medium", text, size, tracking=0.12)
    return (size * 2.8 if dot else size * 1.6) + text_width + size * 1.3


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
    height = size * 2.35
    has_dot = positive is not None
    width = chip_width(text, size, dot=has_dot)
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


def hero(*, compact: bool) -> str:
    canvas = Canvas()
    if compact:
        width, height, radius, cx = 640, 592, 36, 320
        blobs = (
            Blob(150, 130, 330, 240, GLOW_GREEN, 0.34),
            Blob(520, 100, 300, 220, GLOW_TEAL, 0.26),
            Blob(330, 530, 420, 260, GLOW_BLUE, 0.32),
        )
        parts = [
            backdrop(canvas, width, height, radius, blobs, animate=True),
            glass(canvas, 18, 18, width - 36, height - 36, 32),
        ]
        badge, _ = chip(
            canvas, cx, 100, BADGE, positive=True, size=14.5, pulse=True, anchor="middle"
        )
        parts.append(badge)
        for line, baseline in (("Dumindu", 212), ("Kumarapeli", 286)):
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
        for line, baseline in (("I build research prototypes", 362), ("that ship.", 406)):
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
            ("DATA SCIENCE UNDERGRADUATE", 490),
            ("NSBM GREEN UNIVERSITY · SRI LANKA", 524),
        ):
            parts.append(eyebrow(canvas, line, x=cx, y=baseline, anchor="middle", size=17))
    else:
        width, height, radius, cx = 1200, 442, 40, 600
        blobs = (
            Blob(280, 110, 480, 260, GLOW_GREEN, 0.32),
            Blob(940, 100, 430, 240, GLOW_TEAL, 0.24),
            Blob(640, 400, 580, 240, GLOW_BLUE, 0.3),
        )
        parts = [
            backdrop(canvas, width, height, radius, blobs, animate=True),
            glass(canvas, 28, 28, width - 56, height - 56, 36),
        ]
        badge, _ = chip(
            canvas, cx, 120, BADGE, positive=True, size=13.5, pulse=True, anchor="middle"
        )
        parts.append(badge)
        parts.append(
            canvas.text(
                "sans", NAME, 74, x=cx, y=228, axes=display(700), tracking=-0.035, anchor="middle"
            ).markup
        )
        parts.append(
            canvas.text(
                "sans",
                TAGLINE,
                31,
                x=cx,
                y=282,
                axes=display(600),
                tracking=-0.01,
                anchor="middle",
                gradient=GRADIENT,
            ).markup
        )
        parts.append(eyebrow(canvas, AFFILIATION, x=cx, y=342, anchor="middle"))
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


# ---- Skill motifs, each drawn in a 100 x 100 box centred on 0,0 ----


def _pytorch() -> str:
    return (
        '<circle r="26" fill="none" stroke="#fff" stroke-opacity=".2" stroke-dasharray="2 5"/>'
        f'<circle r="7" fill="{PEACH}"/>'
        f'<g class="spin" style="animation-duration:4.5s"><circle cx="26" r="5.5" '
        f'fill="{MINT}"/></g>'
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


def _lock() -> str:
    shackle = (
        '<path d="M-16 -6V-16A16 16 0 0 1 16 -16V-6" fill="none" stroke="#fff" '
        'stroke-opacity=".5" stroke-width="5" stroke-linecap="round"/>'
    )
    body = (
        f'<rect x="-26" y="-8" width="52" height="40" rx="9" fill="{MINT}" fill-opacity=".14" '
        f'stroke="{MINT}" stroke-opacity=".6" stroke-width="1.8"/>'
    )
    keyhole = (
        f'<g class="blink"><circle cy="8" r="5" fill="{MINT}"/>'
        f'<rect x="-2" y="10" width="4" height="11" rx="2" fill="{MINT}"/></g>'
    )
    return shackle + body + keyhole


MOTIFS: dict[str, Callable[[], str]] = {
    "ollama": _ollama,
    "pytorch": _pytorch,
    "opencv": _opencv,
    "postgres": _postgres,
    "lock": _lock,
    "react": _react,
}


# ---- Skills: what I build, the tools behind it, and where to see it ----


ChipRows = list[list[tuple[str, float]]]


@dataclass(frozen=True)
class CardType:
    """Sizes for one skills layout. Vertical spacing is derived from these."""

    pad: float
    title: float
    body: float
    line: float
    chip: float
    seen: float
    motif: float  # scale applied to the 100 x 100 motif box


def _flow(tags: tuple[str, ...], size: float, max_width: float) -> ChipRows:
    """Wrap chips into rows that fit `max_width`."""
    gap = size * 0.7
    rows: ChipRows = [[]]
    used = 0.0
    for tag in tags:
        width = chip_width(tag, size, dot=False)
        if rows[-1] and used + gap + width > max_width:
            rows.append([])
            used = 0.0
        used += (gap if rows[-1] else 0) + width
        rows[-1].append((tag, width))
    return rows


def _skill_offsets(
    skill: Skill, w: float, t: CardType
) -> tuple[list[str], ChipRows, dict[str, float]]:
    """Lines, chip rows and baselines (relative to the card top) for one card."""
    inner = w - 2 * t.pad
    lines = wrap("sans", skill.blurb, t.body, inner, axes=reading(400))
    rows = _flow(skill.tools, t.chip, inner)
    title_y = t.pad + t.title * 1.5
    body_y = title_y + t.body * 2.1
    chips_y = body_y + (len(lines) - 1) * t.line + t.chip * 3.1
    rule_y = chips_y + (len(rows) - 1) * t.chip * 3.1 + t.chip * 2.8
    seen_y = rule_y + t.seen * 2.5
    offsets = {
        "title": title_y,
        "body": body_y,
        "chips": chips_y,
        "rule": rule_y,
        "seen": seen_y,
        "height": seen_y + t.pad * 0.95,
    }
    return lines, rows, offsets


def _skill_card(
    canvas: Canvas, skill: Skill, x: float, y: float, w: float, h: float, t: CardType
) -> str:
    lines, rows, at = _skill_offsets(skill, w, t)
    half = 50 * t.motif
    motif_x, motif_y = x + w - t.pad - half + 4, y + t.pad + half - 2
    title_room = w - 2 * t.pad - 2 * half - 8
    title_size = fit("sans", skill.name, t.title, title_room, axes=display(700), tracking=-0.02)
    motif = (
        f'<g transform="translate({_number(motif_x)} {_number(motif_y)}) scale({t.motif})">'
        f"{MOTIFS[skill.motif]()}</g>"
    )
    parts = [
        glass(canvas, x, y, w, h, 22, strength=0.9),
        motif,
        canvas.text(
            "sans",
            skill.name,
            title_size,
            x=x + t.pad,
            y=y + at["title"],
            axes=display(700),
            tracking=-0.02,
        ).markup,
    ]
    for index, line in enumerate(lines):
        parts.append(
            canvas.text(
                "sans",
                line,
                t.body,
                x=x + t.pad,
                y=y + at["body"] + index * t.line,
                fill=BODY,
                axes=reading(400),
            ).markup
        )
    for row_index, row in enumerate(rows):
        cx = x + t.pad
        cy = y + at["chips"] + row_index * t.chip * 3.1
        for tag, width in row:
            markup, _ = chip(canvas, cx, cy, tag, positive=None, size=t.chip)
            parts.append(markup)
            cx += width + t.chip * 0.7
    # The "seen in" line sits on the card's bottom edge, so it lines up across a row.
    seen_y = y + h - (at["height"] - at["seen"])
    rule = seen_y - (at["seen"] - at["rule"])
    parts.append(
        f'<path d="M{_number(x + t.pad)} {_number(rule)}H{_number(x + w - t.pad)}" '
        'stroke="#fff" stroke-opacity=".09"/>'
    )
    text_x = x + t.pad + t.seen * 1.6
    names = " · ".join(skill.seen_in)
    size = fit("mono-medium", names, t.seen, x + w - t.pad - text_x, tracking=0.12)
    parts.append(arrow(x + t.pad + t.seen * 0.45, seen_y - t.seen * 0.36, t.seen * 0.85, MINT))
    parts.append(
        canvas.text("mono-medium", names, size, x=text_x, y=seen_y, fill=MINT, tracking=0.12).markup
    )
    return "".join(parts)


def skills(*, compact: bool) -> str:
    canvas = Canvas()
    gap = 14
    if compact:
        width, pad, top, columns = 640, 20, 74, 1
        card = CardType(pad=30, title=32, body=21, line=30, chip=14.5, seen=16, motif=0.72)
        header_size = 15
    else:
        width, pad, top, columns = 1200, 28, 80, 3
        card = CardType(pad=26, title=26, body=18, line=26, chip=12.5, seen=13.5, motif=0.56)
        header_size = 14
    card_w = (width - 2 * pad - (columns - 1) * gap) / columns
    needed = [_skill_offsets(s, card_w, card)[2]["height"] for s in SKILLS]
    # In a grid every card takes the height of the tallest, so the rows line up.
    # A single column has nothing to line up with, so each card fits its content.
    heights = needed if columns == 1 else [max(needed)] * len(SKILLS)
    tops, cursor = [], float(top)
    for index in range(len(heights)):
        if index % columns == 0 and index:
            cursor += heights[index - 1] + gap
        tops.append(cursor)
    height = tops[-1] + heights[-1] + pad
    blobs = (
        Blob(width * 0.17, height * 0.25, width * 0.36, height * 0.4, GLOW_GREEN, 0.2),
        Blob(width * 0.83, height * 0.75, width * 0.38, height * 0.42, GLOW_BLUE, 0.22),
        Blob(width * 0.53, height * 0.5, width * 0.32, height * 0.3, GLOW_TEAL, 0.12),
    )
    header_y = 54 if not compact else 50
    parts = [
        backdrop(canvas, width, height, 36 if not compact else 32, blobs, animate=False),
        eyebrow(canvas, "WHAT I BUILD", x=pad + 6, y=header_y, size=header_size),
        eyebrow(canvas, LANGUAGES, x=width - pad - 6, y=header_y, anchor="end", size=header_size),
    ]
    for index, skill in enumerate(SKILLS):
        col = index % columns
        x = pad + col * (card_w + gap)
        parts.append(_skill_card(canvas, skill, x, tops[index], card_w, heights[index], card))
    title = "What I build. " + " ".join(
        f"{s.name}: {s.blurb} Tools: {', '.join(s.tools).title()}. "
        f"Seen in {', '.join(s.seen_in).title()}."
        for s in SKILLS
    )
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


def _datasense_art(canvas: Canvas) -> str:
    """A data file under audit. Only computed facts cross the lock to the model."""
    left, top, cell_w, col_step, row_step = 30, 34, 44, 52, 27
    skewed, missing = 2, {(1, 1), (4, 3), (6, 1), (7, 3)}
    # The skewed column is tinted behind its cells.
    column_tint = (
        f'<rect x="{left + skewed * col_step - 5}" y="{top - 6}" width="{cell_w + 10}" '
        f'height="268" rx="10" fill="{TEAL}" fill-opacity=".08" stroke="{TEAL}" '
        'stroke-opacity=".35"/>'
    )
    parts = [_preview_frame(canvas), column_tint]
    for col in range(4):
        x = left + col * col_step
        parts.append(
            f'<rect x="{x}" y="{top}" width="30" height="8" rx="4" fill="#fff" fill-opacity=".3"/>'
        )
        for row in range(9):
            y = top + 22 + row * row_step
            if (row, col) in missing:
                parts.append(
                    f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{cell_w - 1}" height="17" rx="5" '
                    f'fill="none" stroke="{PEACH}" stroke-opacity=".75" stroke-dasharray="3 3"/>'
                )
                continue
            bar = 14 + (row * 7 + col * 13) % 22
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w}" height="18" rx="5" fill="#fff" '
                f'fill-opacity=".045"/><rect x="{x + 7}" y="{y + 6}" width="{bar}" height="6" '
                'rx="3" fill="#fff" fill-opacity=".22"/>'
            )
        # A quality meter under each column: full, missing values, or skewed.
        colour, share = (
            (PEACH, 0.56) if col in (1, 3) else (TEAL, 0.8) if col == skewed else (MINT, 1.0)
        )
        parts.append(
            f'<rect x="{x}" y="306" width="{cell_w}" height="6" rx="3" fill="#fff" '
            f'fill-opacity=".08"/><rect x="{x}" y="306" width="{cell_w * share:.1f}" '
            f'height="6" rx="3" fill="{colour}"/>'
        )
    parts.append(
        '<g class="scan">'
        f'<rect x="24" y="150" width="212" height="22" fill="{MINT}" fill-opacity=".08"/>'
        f'<rect x="24" y="160" width="212" height="1.5" fill="{MINT}" fill-opacity=".55"/></g>'
    )

    # The privacy boundary: raw rows stay on the left.
    parts.append(
        '<path d="M266 30V334" stroke="#fff" stroke-opacity=".16" stroke-dasharray="3 5"/>'
        '<circle cx="266" cy="182" r="21" fill="#0a0a10" stroke="#fff" stroke-opacity=".16"/>'
        f'<g transform="translate(266 183) scale(.42)">{_lock()}</g>'
    )

    # Right: the distribution it found, the facts it sends, the advice it gets back.
    parts.append(
        '<rect x="296" y="30" width="234" height="136" rx="14" fill="#fff" fill-opacity=".04" '
        'stroke="#fff" stroke-opacity=".1"/>'
        '<path d="M308 150.5H518" stroke="#fff" stroke-opacity=".2"/>'
    )
    for index, bar in enumerate((34, 80, 96, 84, 62, 44, 30, 19, 11)):
        parts.append(
            f'<rect x="{312 + index * 20}" y="{150 - bar}" width="14" height="{bar}" rx="3" '
            f'fill="{TEAL}" fill-opacity=".8"/>'
        )
    parts.append(
        f'<rect x="500" y="136" width="14" height="14" rx="3" fill="{PEACH}"/>'
        + status_dot(507, 122, 4, PEACH, pulse=True)
    )
    for index, (colour, bar) in enumerate(((PEACH, 96), (TEAL, 74), (PEACH, 86))):
        cy = 198 + index * 32
        parts.append(
            f'<rect x="296" y="{cy - 12}" width="170" height="24" rx="12" fill="#fff" '
            f'fill-opacity=".05" stroke="#fff" stroke-opacity=".12"/>'
            f'<circle cx="311" cy="{cy}" r="4" fill="{colour}"/>'
            f'<rect x="323" y="{cy - 3}" width="{bar}" height="6" rx="3" fill="#fff" '
            'fill-opacity=".3"/>'
            f'<path d="M466 {cy}H486" stroke="{MINT}" stroke-opacity=".5" '
            'stroke-dasharray="3 4"/>'
        )
    parts.append(
        f'<path d="M486 198V280M480 274L486 280L492 274" fill="none" stroke="{MINT}" '
        'stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<rect x="296" y="288" width="234" height="46" rx="14" fill="{ACCENT}" '
        f'fill-opacity=".22" stroke="{MINT}" stroke-opacity=".55"/>'
        f'<circle cx="314" cy="311" r="5" fill="{MINT}"/>'
        '<rect x="328" y="302" width="150" height="7" rx="3.5" fill="#fff" fill-opacity=".55"/>'
        '<rect x="328" y="315" width="104" height="7" rx="3.5" fill="#fff" fill-opacity=".3"/>'
    )
    return "".join(parts)


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


def _record_icon(kind: str, cx: float, cy: float) -> str:
    """Small line icons for the records Fulyn keeps."""
    line = 'fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "expense":
        return (
            f'<circle cx="{cx}" cy="{cy}" r="10" fill="{PEACH}" fill-opacity=".16" '
            f'stroke="{PEACH}" stroke-width="1.6"/>'
            f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="none" stroke="{PEACH}" '
            'stroke-opacity=".75" stroke-width="1.4"/>'
        )
    if kind == "sleep":
        return (
            f'<path d="M{cx + 3} {cy - 9.5}A10 10 0 1 0 {cx + 9.5} {cy + 3}'
            f'A7.5 7.5 0 0 1 {cx + 3} {cy - 9.5}Z" fill="{BLUE}"/>'
        )
    if kind == "mood":
        return (
            f'<circle cx="{cx}" cy="{cy}" r="10" stroke="{MINT}" {line}/>'
            f'<circle cx="{cx - 3.5}" cy="{cy - 2.5}" r="1.4" fill="{MINT}"/>'
            f'<circle cx="{cx + 3.5}" cy="{cy - 2.5}" r="1.4" fill="{MINT}"/>'
            f'<path d="M{cx - 4.5} {cy + 2.5}Q{cx} {cy + 7} {cx + 4.5} {cy + 2.5}" '
            f'stroke="{MINT}" {line}/>'
        )
    if kind == "people":
        return (
            f'<circle cx="{cx - 4}" cy="{cy - 4}" r="3.6" fill="{TEAL}"/>'
            f'<circle cx="{cx + 5}" cy="{cy - 3}" r="3.2" fill="{TEAL}" fill-opacity=".7"/>'
            f'<path d="M{cx - 11} {cy + 9}A7 6.5 0 0 1 {cx + 3} {cy + 9}Z" fill="{TEAL}"/>'
            f'<path d="M{cx + 1} {cy + 9}A5.5 5.5 0 0 1 {cx + 11} {cy + 9}Z" fill="{TEAL}" '
            'fill-opacity=".7"/>'
        )
    return (  # journal
        f'<rect x="{cx - 7}" y="{cy - 10}" width="14" height="20" rx="2.5" stroke="#fff" '
        f'stroke-opacity=".6" {line}/>'
        f'<path d="M{cx - 3.5} {cy - 4}H{cx + 3.5}M{cx - 3.5} {cy}H{cx + 3.5}'
        f'M{cx - 3.5} {cy + 4}H{cx + 1}" stroke="#fff" stroke-opacity=".45" {line}/>'
    )


def _fulyn_art(canvas: Canvas) -> str:
    """A note typed into chat, split into the records Fulyn keeps."""
    records = (
        ("expense", PEACH, 64),
        ("sleep", BLUE, 48),
        ("mood", MINT, 40),
        ("people", TEAL, 56),
        ("journal", "#ffffff", 72),
    )
    chat_panel = (
        '<rect x="30" y="30" width="214" height="304" rx="16" fill="#fff" fill-opacity=".03" '
        'stroke="#fff" stroke-opacity=".1"/>'
    )
    sent_note = (
        f'<rect x="64" y="50" width="166" height="74" rx="14" fill="{ACCENT}" '
        f'fill-opacity=".32" stroke="{MINT}" stroke-opacity=".45"/>'
    )
    parts = [_preview_frame(canvas), chat_panel, sent_note]
    for y, w, opacity in ((66, 128, 0.6), (82, 112, 0.45), (98, 82, 0.45)):
        parts.append(
            f'<rect x="80" y="{y}" width="{w}" height="7" rx="3.5" fill="#fff" '
            f'fill-opacity="{opacity}"/>'
        )
    # The reply: one dot per record it logged.
    parts.append(
        '<rect x="44" y="140" width="150" height="58" rx="14" fill="#fff" fill-opacity=".07"/>'
        '<rect x="58" y="154" width="108" height="7" rx="3.5" fill="#fff" fill-opacity=".3"/>'
    )
    for index, (_, colour, _) in enumerate(records):
        parts.append(f'<circle cx="{63 + index * 16}" cy="182" r="4.5" fill="{colour}"/>')
    parts.append(
        f'<rect x="112" y="214" width="118" height="40" rx="14" fill="{ACCENT}" '
        'fill-opacity=".2"/>'
        '<rect x="126" y="225" width="84" height="7" rx="3.5" fill="#fff" fill-opacity=".45"/>'
        '<rect x="126" y="238" width="60" height="7" rx="3.5" fill="#fff" fill-opacity=".3"/>'
        '<rect x="44" y="290" width="186" height="30" rx="15" fill="#fff" fill-opacity=".05" '
        'stroke="#fff" stroke-opacity=".12"/>'
        f'<rect class="blink" x="60" y="298" width="2" height="14" rx="1" fill="{MINT}"/>'
        '<rect x="70" y="302" width="70" height="6" rx="3" fill="#fff" fill-opacity=".14"/>'
    )

    for index, (label, colour, bar) in enumerate(records):
        top = 34 + index * 58
        cy = top + 24
        highlighted = index == 0
        parts.append(
            f'<path d="M230 87C266 87 266 {cy} 300 {cy}" fill="none" stroke="{MINT}" '
            f'stroke-opacity="{0.8 if highlighted else 0.3}" stroke-width="1.4" '
            'stroke-dasharray="3 4"/>'
        )
        card = (
            f'fill="#fff" fill-opacity=".08" stroke="{MINT}" stroke-opacity=".6"'
            if highlighted
            else 'fill="#fff" fill-opacity=".045" stroke="#fff" stroke-opacity=".1"'
        )
        parts.append(f'<rect x="300" y="{top}" width="230" height="48" rx="12" {card}/>')
        parts.append(_record_icon(label, 324, cy))
        parts.append(
            canvas.text(
                "mono", label, 13, x=346, y=cy - 2, fill=TEXT if highlighted else BODY
            ).markup
        )
        parts.append(
            f'<rect x="346" y="{cy + 6}" width="{bar}" height="6" rx="3" fill="#fff" '
            'fill-opacity=".14"/>'
            f'<rect x="462" y="{cy - 10}" width="54" height="20" rx="10" fill="{colour}" '
            f'fill-opacity=".14" stroke="{colour}" stroke-opacity=".45"/>'
            f'<rect x="472" y="{cy - 3}" width="34" height="6" rx="3" fill="{colour}" '
            'fill-opacity=".8"/>'
        )
    parts.append(status_dot(300, 58, 4, MINT, pulse=True))
    return "".join(parts)


ART: dict[str, Callable[[Canvas], str]] = {
    "datasense": _datasense_art,
    "seshat": _seshat_art,
    "fulyn": _fulyn_art,
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
    glow = {"datasense": GLOW_BLUE, "seshat": GLOW_GREEN, "fulyn": GLOW_TEAL}[project.slug]
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
        "mono-medium", project.link, link_size, x=text_x, y=link_y, fill=MINT, tracking=0.16
    )
    parts.append(
        link.markup
        + arrow(
            text_x + link.width + link_size * 1.4, link_y - link_size * 0.36, link_size * 0.86, MINT
        )
    )
    title = f"{project.name}: {project.blurb} {', '.join(project.tags).title()}. {project.link.capitalize()}."
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
        "skills.svg": skills(compact=False),
        "skills-compact.svg": skills(compact=True),
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
