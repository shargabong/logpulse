"""Рисует docs/architecture.png — иллюстрацию схемы LogPulse для отчёта.

Редактируемый исходник схемы лежит в architecture.drawio; этот скрипт
готовит растровую картинку для report.pdf.

Запуск: python tools/gen_architecture.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.png"

GREEN = "#d5e8d4"
GREEN_E = "#82b366"
ORANGE = "#ffe6cc"
ORANGE_E = "#d79b00"
YELLOW = "#fff2cc"
YELLOW_E = "#d6b656"
RED = "#f8cecc"
RED_E = "#b85450"
BLUE = "#dae8fc"


def box(ax, x, y, w, h, text, fc, ec, rounded=0.06, fontsize=9):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={rounded}",
        linewidth=1.2, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, wrap=True)


def arrow(ax, p1, p2, label="", dashed=False, color="#333333", dy=0.28, fontsize=7.5):
    style = "--" if dashed else "-"
    ax.add_patch(FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=14, linewidth=1.3,
        color=color, linestyle=style, shrinkA=2, shrinkB=2,
    ))
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx, my + dy, label, ha="center", va="bottom", fontsize=fontsize, color="#222222")


def main() -> None:
    fig, ax = plt.subplots(figsize=(14, 6.4))
    ax.set_xlim(0, 15.6)
    ax.set_ylim(0, 7.4)
    ax.axis("off")

    # Контейнер docker compose
    ax.add_patch(FancyBboxPatch(
        (2.0, 3.5), 13.3, 3.4,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.0, edgecolor="#6c8ebf", facecolor=BLUE, alpha=0.35,
        linestyle="--",
    ))
    ax.text(2.2, 6.78, "docker compose (сеть logpulse_default)", fontsize=8.5,
            color="#33507a", va="center")

    box(ax, 0.05, 4.6, 1.7, 0.9, "Клиент\n(curl / Swagger UI)", "#f5f5f5", "#666666")
    box(ax, 2.3, 4.5, 2.0, 1.1, "api — FastAPI\nAPIRouter, Pydantic\nREDIS_URL", GREEN, GREEN_E)
    box(ax, 4.9, 4.5, 2.0, 1.1, "Redis Stream\nlogpulse:events\nXADD", ORANGE, ORANGE_E)
    box(ax, 7.5, 4.5, 2.1, 1.1, "worker\nXREADGROUP / XACK\nlogpulse-workers", GREEN, GREEN_E)
    box(ax, 10.3, 4.2, 2.5, 1.7,
        "Redis Hash / Sorted Set\nlogpulse:stats:level\nlogpulse:stats:service\n"
        "logpulse:stats:status\nlogpulse:slow\nHINCRBY / ZADD", ORANGE, ORANGE_E, fontsize=8)
    box(ax, 7.5, 1.9, 2.3, 1.0, "volume: redis-data\n(AOF, переживает рестарт)", YELLOW, YELLOW_E, fontsize=8)

    arrow(ax, (1.78, 5.05), (2.3, 5.05), "HTTP /ingest")
    arrow(ax, (4.3, 5.05), (4.9, 5.05), "XADD")
    arrow(ax, (6.9, 5.05), (7.5, 5.05), "XREADGROUP")
    arrow(ax, (9.6, 5.05), (10.3, 5.05), "HINCRBY / ZADD")
    # API читает статистику напрямую из Redis (нижняя пунктирная линия).
    arrow(ax, (3.3, 4.5), (11.5, 4.15), dashed=True, dy=-0.02, fontsize=7.5)
    ax.text(7.4, 4.02, "HGETALL / ZREVRANGE (/stats)", ha="center", va="top", fontsize=7.5)
    arrow(ax, (3.3, 4.5), (5.9, 4.5), "PING (/health)", dashed=True, dy=-0.42, fontsize=7.5)
    arrow(ax, (11.55, 4.2), (8.65, 2.95), "", dashed=True)

    box(ax, 2.0, 0.3, 13.3, 1.1,
        "Восстановление после сбоя: redis перезапускается из volume redis-data (AOF);\n"
        "api и worker переподключаются с backoff; статистика и очередь сохраняются",
        RED, RED_E, fontsize=9)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Сохранено: {OUT}")


if __name__ == "__main__":
    main()
