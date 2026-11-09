"""Figure 2: the adaptive red team, by round. Reads results/adaptive_analysis.txt (written by analysis.adaptive report).

  python3 -m analysis.fig_adaptive        # writes paper/fig2_adaptive.svg
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT = "font-family='Helvetica, Arial, sans-serif'"
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#d9d8d2"
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"


def rows():
    out = []
    for line in (ROOT / "results" / "adaptive_analysis.txt").read_text().splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 9 or not c[0].isdigit():
            continue
        m = re.match(r"([\d.]+) \[([\d.]+), ([\d.]+)\]", c[3])
        frac = lambda s: (int(s.split("/")[0]), int(s.split("/")[1].split()[0]))
        out.append({"round": int(c[0]), "m1": float(m.group(1)), "lo": float(m.group(2)), "hi": float(m.group(3)),
                    "m1s": float(c[5]), "m2": float(c[6]), "undet": frac(c[4]), "hidden": frac(c[7])})
    return out


def svg(rs) -> str:
    W, H = 820, 360
    o = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
         f"<rect width='{W}' height='{H}' fill='#ffffff'/>"]
    t = lambda x, y, s, size=12, fill=INK, anchor="start", weight="normal": o.append(
        f"<text x='{x}' y='{y}' {FONT} font-size='{size}' fill='{fill}' text-anchor='{anchor}' font-weight='{weight}'>{s}</text>")

    # Panel A: AUROC by round
    L, R, T, B = 60, 380, 70, 290
    xs = {r["round"]: L + 40 + (r["round"] - 1) * (R - L - 80) / 2 for r in rs}
    y = lambda a: B - a * (B - T)
    t(L - 50, 24, "A. Monitor AUROC, covert vs honest (watched MiniMax)", 13, weight="bold")
    for a in (0, 0.25, 0.5, 0.75, 1.0):
        dash = " stroke-dasharray='4 3'" if a == 0.5 else ""
        o.append(f"<line x1='{L}' y1='{y(a):.1f}' x2='{R}' y2='{y(a):.1f}' stroke='{MUTED if a == 0.5 else GRID}'{dash}/>")
        t(L - 8, f"{y(a) + 4:.1f}", f"{a:g}", 11, MUTED, "end")
    t(L + 4, f"{y(0.5) + 14:.1f}", "chance", 11, MUTED, "start")
    series = (("m1", BLUE, "M1 per-agent judge"), ("m1s", ORANGE, "M1, notes removed"), ("m2", GREEN, "M2 joint judge"))
    for r in rs:
        x = xs[r["round"]]
        o.append(f"<line x1='{x:.1f}' y1='{y(r['lo']):.1f}' x2='{x:.1f}' y2='{y(r['hi']):.1f}' stroke='{BLUE}' stroke-width='2'/>")
    dodge = {"m1": 0, "m1s": 16, "m2": -16}
    for k, col, _ in series:
        pts = [(xs[r["round"]] + dodge[k], y(r[k])) for r in rs]
        o.append(f"<polyline fill='none' stroke='{col}' stroke-width='2' points='" + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + "'/>")
        for a, b in pts:
            o.append(f"<circle cx='{a:.1f}' cy='{b:.1f}' r='4.5' fill='{col}' stroke='#ffffff' stroke-width='2'/>")
    for r in rs:
        t(f"{xs[r['round']]:.1f}", B + 18, f"round {r['round']}", 11, MUTED, "middle")
        t(f"{xs[r['round']]:.1f}", B + 32, "no briefing" if r["round"] == 1 else "briefed", 11, MUTED, "middle")
    for i, (_, col, name) in enumerate(series):
        lx, ly = (L, L + 160, L)[i], (38, 38, 56)[i]
        o.append(f"<rect x='{lx}' y='{ly}' width='12' height='12' rx='3' fill='{col}'/>")
        t(lx + 17, ly + 10, name, 11)

    # Panel B: outcomes by round
    L2, R2 = 470, 790
    t(L2 - 30, 24, "B. Attack outcomes by round", 13, weight="bold")
    for a in (0, 0.25, 0.5, 0.75, 1.0):
        o.append(f"<line x1='{L2}' y1='{y(a):.1f}' x2='{R2}' y2='{y(a):.1f}' stroke='{GRID}'/>")
        t(L2 - 8, f"{y(a) + 4:.1f}", f"{int(a * 100)}%", 11, MUTED, "end")
    bw, gap = 34, 2
    for i, r in enumerate(rs):
        cx = L2 + 55 + i * (R2 - L2 - 110) / 2
        for j, (k, col) in enumerate((("undet", BLUE), ("hidden", ORANGE))):
            n, d = r[k]
            x = cx - bw - gap / 2 + j * (bw + gap)
            h = n / d * (B - T)
            if h > 0:
                o.append(f"<path d='M{x:.1f},{B} V{B - h + 4:.1f} Q{x:.1f},{B - h:.1f} {x + 4:.1f},{B - h:.1f} "
                         f"H{x + bw - 4:.1f} Q{x + bw:.1f},{B - h:.1f} {x + bw:.1f},{B - h + 4:.1f} V{B} Z' fill='{col}'/>")
            t(f"{x + bw / 2:.1f}", f"{B - h - 6:.1f}", f"{n}/{d}", 11, INK, "middle")
        t(f"{cx:.1f}", B + 18, f"round {r['round']}", 11, MUTED, "middle")
        t(f"{cx:.1f}", B + 32, "no briefing" if r["round"] == 1 else "briefed", 11, MUTED, "middle")
    o.append(f"<rect x='{L2}' y='38' width='12' height='12' rx='3' fill='{BLUE}'/>")
    t(L2 + 17, 48, "succeeded and undetected (5% audit budget)", 11)
    o.append(f"<rect x='{L2}' y='56' width='12' height='12' rx='3' fill='{ORANGE}'/>")
    t(L2 + 17, 66, "wrote a hidden file", 11)
    t(W / 2, H - 8, "Round 1: 20 episodes; rounds 2-3: 10 each (seeds 1-10). Negatives: 20 honest watched episodes. Whiskers: 95% bootstrap CI.",
      11, MUTED, "middle")
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    (ROOT / "paper" / "fig2_adaptive.svg").write_text(svg(rows()))
    print("wrote paper/fig2_adaptive.svg")
