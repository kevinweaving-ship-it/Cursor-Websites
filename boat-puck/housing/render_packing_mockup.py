#!/usr/bin/env python3
"""Render 2D packing mockups: Puck vs Screen inside H9-13 cavity (mm)."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
ART = Path("/opt/cursor/artifacts")
ART.mkdir(parents=True, exist_ok=True)

# Cavity = camera positive
W, H, D = 71.8, 50.8, 33.6
LENS_D, LENS_T = 33.0, 5.5
WINDOW_W, WINDOW_H = 62.7, 41.7


def cavity_side(ax, title):
    """XZ: X=width, Z=depth. Left=lens (−Z), right=backdoor (+Z)."""
    ax.set_title(title, fontsize=11, pad=8)
    # cavity outline
    ax.add_patch(
        Rectangle((-D / 2, -W / 2), D, W, fill=False, lw=2, ec="#222")
    )
    # lens boss
    ax.add_patch(
        Rectangle((-D / 2, -LENS_D / 2), LENS_T, LENS_D, fill=True, fc="#f5a62355", ec="#f5a623")
    )
    ax.set_xlim(-D / 2 - 4, D / 2 + 4)
    ax.set_ylim(-W / 2 - 6, W / 2 + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("depth Z (mm)  lens ← → backdoor")
    ax.set_ylabel("width X (mm)")
    ax.grid(True, alpha=0.25)
    ax.axvline(D / 2, color="#888", ls="--", lw=1, label="backdoor")
    ax.axvline(-D / 2, color="#f5a623", ls=":", lw=1)


def cavity_rear(ax, title):
    """XY looking in from backdoor."""
    ax.set_title(title, fontsize=11, pad=8)
    ax.add_patch(Rectangle((-W / 2, -H / 2), W, H, fill=False, lw=2, ec="#222"))
    ax.add_patch(
        Rectangle(
            (-WINDOW_W / 2, -WINDOW_H / 2),
            WINDOW_W,
            WINDOW_H,
            fill=False,
            lw=1.5,
            ec="#2a9d8f",
            ls="--",
            label="backdoor window",
        )
    )
    ax.set_xlim(-W / 2 - 6, W / 2 + 6)
    ax.set_ylim(-H / 2 - 6, H / 2 + 6)
    ax.set_aspect("equal")
    ax.set_xlabel("width X (mm)")
    ax.set_ylabel("height Y (mm)")
    ax.grid(True, alpha=0.25)


def label(ax, x, y, text, color="#111"):
    ax.text(x, y, text, fontsize=7, ha="center", va="center", color=color)


def draw_puck(fig):
    ax1 = fig.add_subplot(2, 2, 1)
    cavity_side(ax1, "1. PUCK — side (depth pack)")
    # GPS in lens
    ax1.add_patch(Rectangle((-D / 2 + 0.5, -12.5), 4.0, 25, fc="#ddd", ec="#333"))
    label(ax1, -D / 2 + 2.5, 18, "GPS Ø25×4", "#333")
    # GNSS
    ax1.add_patch(Rectangle((-D / 2 + LENS_T, -14), 3.0, 28, fc="#2d6a4f", ec="#1b4332"))
    label(ax1, -D / 2 + LENS_T + 1.5, -22, "GNSS", "#1b4332")
    # MCU / LoRa stack mid
    ax1.add_patch(Rectangle((-6, -20), 3, 18, fc="#264653", ec="#000"))
    ax1.add_patch(Rectangle((-6, 4), 3, 16, fc="#264653", ec="#000"))
    label(ax1, -4.5, 24, "MCU/LoRa", "#264653")
    # LiPo
    ax1.add_patch(Rectangle((2, -30), 8, 60, fc="#212529", ec="#000"))
    label(ax1, 6, 0, "LiPo\n60×40×8", "#fff")
    # depth budget text
    ax1.text(
        0,
        -W / 2 - 4.5,
        f"cavity D={D} mm · lens pocket {LENS_T} mm · battery 8 mm fits",
        ha="center",
        fontsize=7,
        color="#444",
    )

    ax2 = fig.add_subplot(2, 2, 2)
    cavity_rear(ax2, "1. PUCK — rear view (no LCD)")
    ax2.add_patch(Circle((0, 0), 15, fc="#f5a62333", ec="#f5a623", lw=1))
    label(ax2, 0, 0, "GPS\npocket\n(front)", "#b36b00")
    ax2.add_patch(Rectangle((-30, -20), 60, 40, fc="#21252988", ec="#000"))
    label(ax2, 0, -28, "LiPo 60×40 (fits in 71.8×50.8)", "#111")
    ax2.add_patch(Rectangle((-32.5, -22.5), 65, 45, fill=False, lw=1, ec="#2d6a4f", ls=":"))
    label(ax2, 0, 26, "carrier PCB ≤65×45", "#2d6a4f")
    ax2.text(
        0,
        -H / 2 - 4.5,
        "NO screen — full cavity for RF + battery",
        ha="center",
        fontsize=8,
        color="#c1121f",
        fontweight="bold",
    )


def draw_screen(fig):
    ax1 = fig.add_subplot(2, 2, 3)
    cavity_side(ax1, "2a. SCREEN — side (LCD on backdoor)")
    # small battery forward
    ax1.add_patch(Rectangle((-8, -22.5), 6, 45, fc="#212529", ec="#000"))
    label(ax1, -5, 0, "LiPo\n45×30×6", "#fff")
    # MCU
    ax1.add_patch(Rectangle((2, -18), 3, 16, fc="#264653", ec="#000"))
    label(ax1, 3.5, -24, "MCU", "#264653")
    # LCD against backdoor
    ax1.add_patch(Rectangle((D / 2 - 2.5, -29), 2.5, 58, fc="#0077b6", ec="#023e8a"))
    label(ax1, D / 2 - 1.2, 0, "LCD\n58×35", "#fff")
    ax1.text(
        0,
        -W / 2 - 4.5,
        "board 58 mm ≤ window 62.7 mm · flush to backdoor",
        ha="center",
        fontsize=7,
        color="#444",
    )

    ax2 = fig.add_subplot(2, 2, 4)
    cavity_rear(ax2, "2a. SCREEN — rear (through lid window)")
    # LCD board
    ax2.add_patch(Rectangle((-29, -17.5), 58, 35, fc="#0077b6", ec="#023e8a", lw=1.5))
    # AA 40.8 x 30.6 on Waveshare 2" (AA along board)
    ax2.add_patch(Rectangle((-20.4, -15.3), 40.8, 30.6, fc="#90e0ef", ec="#0077b6"))
    label(ax2, 0, 0, "AA 40.8×30.6\n(~2.0\")", "#023e8a")
    label(ax2, 0, -28, "board 58×35  ✓ in window 62.7×41.7", "#023e8a")
    # margins
    mx = (WINDOW_W - 58) / 2
    my = (WINDOW_H - 35) / 2
    ax2.text(
        0,
        H / 2 + 3.5,
        f"board margin in window: {mx:.1f} mm L/R · {my:.1f} mm T/B",
        ha="center",
        fontsize=7,
        color="#2a9d8f",
    )
    ax2.text(
        0,
        -H / 2 - 4.5,
        "SPI module only (no ESP32 kit) · MCU+battery behind glass",
        ha="center",
        fontsize=7,
        color="#444",
    )


def main():
    fig = plt.figure(figsize=(11, 9), dpi=140)
    fig.suptitle(
        "Boat Puck — H9–13 housing fit mockup (cavity 71.8 × 50.8 × 33.6 mm)",
        fontsize=13,
        fontweight="bold",
        y=0.98,
    )
    draw_puck(fig)
    draw_screen(fig)
    fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    paths = [
        OUT / "packing-mockup-puck-screen.png",
        ART / "packing-mockup-puck-screen.png",
    ]
    for p in paths:
        fig.savefig(p, bbox_inches="tight", facecolor="white")
        print("wrote", p)
    plt.close(fig)

    # Fit checklist image
    fig2, ax = plt.subplots(figsize=(9, 4.2), dpi=140)
    ax.axis("off")
    ax.set_title("Fit checklist vs H9–13 cavity", fontsize=12, fontweight="bold", pad=12)
    rows = [
        ["Part", "Size (mm)", "Budget", "Fit?"],
        ["Cavity (camera positive)", "71.8 × 50.8 × 33.6", "—", "envelope"],
        ["Puck LiPo", "60 × 40 × 8", "≤71.8×50.8×~20", "YES"],
        ["Puck GPS in lens pocket", "Ø25 × 4", "Ø30 × 5.5", "YES"],
        ["Screen LCD board (2.0\" SPI)", "58 × 35 × 2.5", "window 62.7×41.7", "YES"],
        ["Screen AA", "40.8 × 30.6", "inside board", "YES"],
        ["Screen LiPo", "45 × 30 × 6", "forward of LCD", "YES"],
        ["ESP32-devkit / ESP32-LCD kit", "~55×28+ / ~70+", "too long/thick", "NO"],
        ["4.2\" RLCD AA", "63.6 × 84.8", "71.8×50.8 face", "NO"],
    ]
    table = ax.table(cellText=rows, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.45)
    for (r, c), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor("#264653")
            cell.set_text_props(color="white", fontweight="bold")
        elif rows[r][3] == "YES":
            cell.set_facecolor("#d8f3dc" if c == 3 else "#f8fff9")
        elif rows[r][3] == "NO":
            cell.set_facecolor("#f8d7da" if c == 3 else "#fff5f5")
    fig2.tight_layout()
    for p in [OUT / "packing-mockup-fit-table.png", ART / "packing-mockup-fit-table.png"]:
        fig2.savefig(p, bbox_inches="tight", facecolor="white")
        print("wrote", p)
    plt.close(fig2)


if __name__ == "__main__":
    main()
