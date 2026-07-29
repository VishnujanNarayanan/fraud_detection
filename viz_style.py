"""Shared plotting style for the fraud-detection notebook.

One place for every visual decision: colours, type, grid, spines, tick
formatting and figure furniture (title / subtitle / source line).

Import it once at the top of the notebook::

    import viz_style as vs
    vs.apply()

then build every figure through :func:`figure` and close it with
:func:`finish`, which lays out the text furniture and returns the same
Figure object you pass to :func:`save`. Figures are 8x5in at 200dpi,
i.e. exactly 1600x1000px, and are never plotted twice.
"""

from __future__ import annotations

import os
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

SURFACE = "#fcfcfb"      # plot area
PAGE = "#f9f9f7"         # figure background
INK = "#0b0b0b"          # titles
INK_2 = "#52514e"        # subtitles, axis labels
MUTED = "#898781"        # ticks, source line
GRID = "#e1e0d9"         # gridlines
AXIS = "#c3c2b7"         # spines, baselines

#: Categorical hues, assigned in this fixed order. Never cycled.
CAT = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow
    "#e87ba4",  # 5 magenta
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = CAT

#: Sequential ramp - one blue hue, light to dark.
SEQ = ["#cde2fb", "#86b6ef", "#3987e5", "#2a78d6", "#1c5cab", "#0d366b"]

#: Discrete ordered categories start no lighter than SEQ[1].
SEQ_DISCRETE = SEQ[1:]

#: Status colours. Reserved - never used as a series colour.
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

NEUTRAL_MID = "#f0efec"

#: Sequential colormap, for magnitude.
CMAP_SEQ = LinearSegmentedColormap.from_list("seq_blue", SEQ)

#: Diverging colormap, blue <-> red through a neutral grey midpoint. Pair it
#: with :func:`diverging_norm` so the grey lands exactly on zero.
CMAP_DIV = LinearSegmentedColormap.from_list(
    "div_blue_red", ["#0d366b", "#2a78d6", "#86b6ef", NEUTRAL_MID,
                     "#eb8b8a", "#e34948", "#a02020"],
)

FIGSIZE = (8, 5)
DPI = 200
FIGDIR = "figures"


# ---------------------------------------------------------------------------
# rcParams
# ---------------------------------------------------------------------------

def apply() -> None:
    """Install the style. Call once, before building any figure."""
    mpl.rcParams.update({
        # -- canvas -----------------------------------------------------
        "figure.figsize": FIGSIZE,
        "figure.dpi": 110,
        "savefig.dpi": DPI,
        "figure.facecolor": PAGE,
        "savefig.facecolor": PAGE,
        "axes.facecolor": SURFACE,
        "savefig.edgecolor": "none",
        # bbox_inches is deliberately NOT 'tight': tight cropping would
        # change the pixel dimensions per figure. Margins are fixed in
        # finish() instead so every PNG is exactly 1600x1000.
        "savefig.bbox": None,

        # -- type. No semibold face exists in Liberation/DejaVu Sans, so
        # hierarchy comes from size and colour only, never weight. -------
        "font.family": "sans-serif",
        "font.sans-serif": ["Liberation Sans", "DejaVu Sans", "sans-serif"],
        "font.weight": "normal",
        "axes.titleweight": "normal",
        "axes.labelweight": "normal",
        "axes.titlesize": 13.5,
        "axes.labelsize": 10.5,
        "axes.titlecolor": INK,
        "axes.labelcolor": INK_2,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": MUTED,
        "ytick.labelcolor": MUTED,
        "text.color": INK_2,

        # -- grid: solid hairlines, y only, behind the data --------------
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linestyle": "-",
        "grid.linewidth": 0.6,
        "grid.alpha": 1.0,

        # -- spines: bottom only -----------------------------------------
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": True,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.minor.size": 0,
        "ytick.minor.size": 0,
        "xtick.major.pad": 6,
        "ytick.major.pad": 6,

        # -- marks --------------------------------------------------------
        "axes.prop_cycle": mpl.cycler(color=CAT),
        "lines.linewidth": 2.0,
        "lines.markersize": 8,
        "lines.solid_capstyle": "round",
        "patch.linewidth": 0.0,      # bars have no stroke
        "patch.edgecolor": "none",
        "patch.force_edgecolor": False,

        # -- legend: frameless ---------------------------------------------
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "legend.labelcolor": INK_2,
        "legend.handlelength": 1.4,
        "legend.handleheight": 0.9,
        "legend.borderaxespad": 0.0,
        "legend.columnspacing": 1.6,
        "legend.handletextpad": 0.6,
    })


# ---------------------------------------------------------------------------
# Tick formatters
# ---------------------------------------------------------------------------

def _trim(s: str) -> str:
    """Drop trailing zeros only after a decimal point ('10' stays '10')."""
    return s.rstrip("0").rstrip(".") if "." in s else s


def _compact(v: float, currency: bool = False, places: int = 1) -> str:
    """1234567 -> '1.2M'. With currency=True, '$1.2M'."""
    sign = "-" if v < 0 else ""
    v = abs(float(v))
    for cut, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= cut:
            return f"{sign}{'$' if currency else ''}{_trim(f'{v / cut:.{places}f}')}{suf}"
    s = f"{v:,.0f}" if v >= 1 else f"{v:g}"
    return f"{sign}{'$' if currency else ''}{s}"


def fmt_thousands(places: int = 0) -> FuncFormatter:
    """1234567 -> '1,234,567'."""
    return FuncFormatter(lambda v, _p: f"{v:,.{places}f}")


def fmt_compact(places: int = 1) -> FuncFormatter:
    """1234567 -> '1.2M'."""
    return FuncFormatter(lambda v, _p: _compact(v, False, places))


def fmt_currency(places: int = 1) -> FuncFormatter:
    """1234567 -> '$1.2M'."""
    return FuncFormatter(lambda v, _p: _compact(v, True, places))


def fmt_percent(places: int = 1) -> FuncFormatter:
    """13.24 -> '13.2%'. Expects values already scaled to 0-100."""
    return FuncFormatter(lambda v, _p: f"{v:,.{places}f}%")


def fmt_log_compact() -> FuncFormatter:
    """Compact labels for a log axis: 1000 -> '1K'."""
    return FuncFormatter(lambda v, _p: _compact(v, False, 0))


def diverging_norm(vmin: float, vmax: float) -> TwoSlopeNorm:
    """TwoSlopeNorm centred on zero, so the neutral grey lands on zero."""
    vmin = min(vmin, -1e-9)
    vmax = max(vmax, 1e-9)
    return TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)


def ordered_blues(n: int) -> list[str]:
    """`n` steps of the blue ramp for genuinely ordered categories.

    Starts no lighter than SEQ[1] so every step stays legible on the surface.
    """
    if n <= 1:
        return [BLUE]
    idx = np.linspace(0, len(SEQ_DISCRETE) - 1, n)
    return [SEQ_DISCRETE[int(round(i))] for i in idx]


# ---------------------------------------------------------------------------
# Figure furniture
# ---------------------------------------------------------------------------

def figure(figsize=FIGSIZE):
    """A single-axes figure at the standard size."""
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


#: Characters that fit across the plot width at the title / subtitle / source
#: sizes. Used to wrap rather than let text run off the canvas.
_WRAP = {"title": 76, "subtitle": 104, "source": 124}


def esc(text: str) -> str:
    """Escape dollar signs so matplotlib does not read them as mathtext.

    A string containing two '$' (``"$442K against $74K"``) is otherwise parsed
    as a LaTeX math span and rendered in italics with the dollars eaten.
    """
    return text.replace("$", r"\$")


def _wrap(text: str, kind: str) -> list[str]:
    # Wrap on the unescaped text so the widths are right, escape afterwards.
    return [esc(line) for line in textwrap.wrap(text, _WRAP[kind])] or [""]


def headroom(ax, frac: float = 0.12, log: bool = False) -> None:
    """Open space above the data so direct labels are never clipped."""
    lo, hi = ax.get_ylim()
    if log:
        ax.set_ylim(lo, hi * (10 ** (np.log10(hi / lo) * frac)))
    else:
        ax.set_ylim(lo, hi + (hi - lo) * frac)


def finish(fig, ax, *, title, xlabel, ylabel, subtitle=None, source=None,
           legend=False, legend_ncol=None, left=0.115, right=0.975, bottom=None):
    """Lay out the text furniture and fix the margins.

    Margins are set explicitly rather than by tight-layout, so every saved
    PNG comes out at exactly the same pixel size. Title, subtitle and source
    are wrapped to the plot width instead of overflowing the canvas.
    """
    title_lines = _wrap(title, "title")
    sub_lines = _wrap(subtitle, "subtitle") if subtitle else []
    src_lines = _wrap(source, "source") if source else []

    # Text furniture is laid out top-down from a cursor in figure coords.
    y = 0.965
    for line in title_lines:
        fig.text(left, y, line, ha="left", va="top", fontsize=13.5, color=INK)
        y -= 0.055
    y -= 0.008
    for line in sub_lines:
        fig.text(left, y, line, ha="left", va="top", fontsize=10, color=INK_2)
        y -= 0.044

    top = y - (0.085 if legend else 0.035)
    if bottom is None:
        bottom = 0.150 + 0.040 * (len(src_lines) - 1) if src_lines else 0.115
    fig.subplots_adjust(left=left, right=right, top=top, bottom=bottom)

    ax.set_xlabel(esc(xlabel), fontsize=10.5, color=INK_2, labelpad=8)
    ax.set_ylabel(esc(ylabel), fontsize=10.5, color=INK_2, labelpad=8)

    if legend:
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="lower left",
                      bbox_to_anchor=(0.0, 1.02),
                      ncol=legend_ncol or len(handles),
                      frameon=False, fontsize=9.5)

    ys = 0.032 + 0.040 * (len(src_lines) - 1)
    for line in src_lines:
        fig.text(left, ys, line, ha="left", va="center", fontsize=8.5, color=MUTED)
        ys -= 0.040
    return fig


def save(fig, name: str, figdir: str = FIGDIR) -> str:
    """Save `fig` to ``<figdir>/<name>.png`` at 1600x1000 and return the path.

    Saves the *same* Figure the notebook renders - the chart is never drawn
    a second time.
    """
    os.makedirs(figdir, exist_ok=True)
    path = os.path.join(figdir, f"{name}.png")
    fig.savefig(path, dpi=DPI, facecolor=PAGE, edgecolor="none")
    return path


def boxes(ax, groups, labels, colors):
    """A styled boxplot: filled boxes, no stroke, surface-coloured median."""
    bp = ax.boxplot(groups, tick_labels=labels, showfliers=False, widths=0.45,
                    patch_artist=True,
                    medianprops=dict(color=SURFACE, linewidth=1.6),
                    whiskerprops=dict(color=AXIS, linewidth=1.0),
                    capprops=dict(color=AXIS, linewidth=1.0),
                    boxprops=dict(linewidth=0))
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
    return bp


def contact_sheet(name="00-contact-sheet", figdir=FIGDIR, cols=3, thumb_width=520):
    """Tile every numbered figure in `figdir` into a single overview PNG.

    Lets the whole set be checked for consistency at a glance, and gives the
    README one image that stands in for all fifteen.
    """
    from PIL import Image

    paths = sorted(p for p in os.listdir(figdir)
                   if p.endswith(".png") and p[:2].isdigit() and not p.startswith("00"))
    if not paths:
        return None
    tw = thumb_width
    th = round(tw * FIGSIZE[1] / FIGSIZE[0])
    rows = -(-len(paths) // cols)
    sheet = Image.new("RGB", (cols * tw, rows * th), (232, 232, 228))
    for i, p in enumerate(paths):
        thumb = Image.open(os.path.join(figdir, p)).convert("RGB").resize(
            (tw, th), Image.LANCZOS)
        sheet.paste(thumb, ((i % cols) * tw, (i // cols) * th))
    out = os.path.join(figdir, f"{name}.png")
    sheet.save(out, format="PNG", compress_level=6)
    return out


def label_bar(ax, x, y, text, *, color=INK, dy=0.0, ha="center", va="bottom",
              fontsize=9.5):
    """Direct-label a single mark. Use for the max or the endpoint only."""
    ax.annotate(esc(text), (x, y), textcoords="offset points", xytext=(0, 4 + dy),
                ha=ha, va=va, fontsize=fontsize, color=color)


def baseline(ax):
    """Colour the x baseline to match the axis token."""
    ax.spines["bottom"].set_color(AXIS)
    ax.spines["bottom"].set_linewidth(0.8)
