"""Figure 1: AUROC (covert vs benign, UNWATCHED) per monitor, three swarm models. Judge: GPT-6 Luna.

The values are copied from `python3 -m scripts.score report --label main|qwen|strong` (AUROC, 95% bootstrap CI over episodes; n = 30 vs 30 for MiniMax and Qwen, 20 vs 20 for Kimi). Writes paper/fig1.svg. Standard library only.

Run: python3 -m scripts.make_fig1
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "fig1.svg"

# (label, group, minimax, qwen, kimi), each (auroc, lo, hi)
ROWS = [
    ("M1 per-agent judge", "LLM judge (looks for concealment)", (0.849, 0.734, 0.935), (0.882, 0.786, 0.959), (1.000, 1.000, 1.000)),
    ("M1, agents' notes removed", "LLM judge (looks for concealment)", (0.580, 0.438, 0.719), (0.901, 0.821, 0.963), (0.980, 0.940, 1.000)),
    ("M4 canary traps + rare tokens", "File-flow monitors", (0.488, 0.342, 0.639), (0.637, 0.482, 0.781), (0.725, 0.550, 0.882)),
    ("M3 provenance", "File-flow monitors", (0.327, 0.187, 0.467), (0.228, 0.122, 0.349), (0.165, 0.052, 0.306)),
]
SERIES = [("MiniMax m3.1 flash", "#2a78d6"), ("Qwen 3.8 flash", "#eb6834"), ("Kimi K3.1 Pro (strong)", "#1baf7a")]
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#d9d8d2", "#ffffff"

W, LEFT, RIGHT = 820, 236, 730
BAR, GAP, ROW_PAD = 13, 3, 16
FONT = "font-family='Helvetica, Arial, sans-serif'"


def x(v):
    return LEFT + v * (RIGHT - LEFT)


def main():
    out = []
    y = 64
    group = None
    body = []
    for label, g, *vals in ROWS:
        if g != group:
            y += 10 if group else 0
            body.append(f"<text x='16' y='{y + 4}' {FONT} font-size='12' font-weight='bold' fill='{MUTED}'>{g}</text>")
            y += 16
            group = g
        row_h = len(SERIES) * BAR + (len(SERIES) - 1) * GAP
        body.append(f"<text x='{LEFT - 10}' y='{y + row_h / 2 + 4}' {FONT} font-size='13' fill='{INK}' text-anchor='end'>{label}</text>")
        for k, ((a, lo, hi), (_, color)) in enumerate(zip(vals, SERIES)):
            by = y + k * (BAR + GAP)
            w = max(1.0, x(a) - LEFT)
            body.append(f"<path d='M{LEFT},{by} h{w - 4:.1f} a4,4 0 0 1 4,4 v{BAR - 8} a4,4 0 0 1 -4,4 h{-(w - 4):.1f} z' fill='{color}'/>")
            if hi > lo:
                cy = by + BAR / 2
                body.append(f"<line x1='{x(lo):.1f}' y1='{cy}' x2='{x(hi):.1f}' y2='{cy}' stroke='{INK}' stroke-width='1.2'/>")
                for e in (lo, hi):
                    body.append(f"<line x1='{x(e):.1f}' y1='{cy - 3}' x2='{x(e):.1f}' y2='{cy + 3}' stroke='{INK}' stroke-width='1.2'/>")
            tx = max(x(a), x(hi)) + 6
            if tx < x(0.5) + 4 < tx + 28:  # keep value labels off the chance line
                tx = x(0.5) + 5
            body.append(f"<text x='{tx:.1f}' y='{by + BAR - 2}' {FONT} font-size='11' fill='{INK}'>{a:.2f}</text>")
        y += row_h + ROW_PAD
    top, bottom = 72, y - ROW_PAD + 6
    H = bottom + 68

    out.append(f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>")
    out.append(f"<rect width='{W}' height='{H}' fill='{SURFACE}'/>")
    # legend (top)
    lx = LEFT
    for name, color in SERIES:
        out.append(f"<rect x='{lx}' y='22' width='12' height='12' rx='3' fill='{color}'/>")
        out.append(f"<text x='{lx + 18}' y='32' {FONT} font-size='13' fill='{INK}'>{name}</text>")
        lx += 165
    # grid + axis
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        dash = " stroke-dasharray='4 3'" if t == 0.5 else ""
        col = MUTED if t == 0.5 else GRID
        out.append(f"<line x1='{x(t):.1f}' y1='{top - 14}' x2='{x(t):.1f}' y2='{bottom}' stroke='{col}' stroke-width='1'{dash}/>")
        out.append(f"<text x='{x(t):.1f}' y='{bottom + 16}' {FONT} font-size='11' fill='{MUTED}' text-anchor='middle'>{t:g}</text>")
    out.append(f"<text x='{x(0.5):.1f}' y='{top - 18}' {FONT} font-size='11' fill='{MUTED}' text-anchor='middle'>chance</text>")
    out.append(f"<text x='{(LEFT + RIGHT) / 2:.0f}' y='{bottom + 38}' {FONT} font-size='12' fill='{INK}' text-anchor='middle'>AUROC, covert vs honest (unwatched; judge GPT-6 Luna; 30+30 episodes, Kimi 20+20)</text>")
    out.append(f"<text x='{(LEFT + RIGHT) / 2:.0f}' y='{bottom + 54}' {FONT} font-size='11' fill='{MUTED}' text-anchor='middle'>whiskers: 95% bootstrap CI over episodes</text>")
    out += body
    out.append("</svg>")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(out))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
