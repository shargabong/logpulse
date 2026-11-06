"""Создаёт заглушки docs/screens/*.png.

Заглушки нужны, чтобы report.pdf собирался сразу. Перед сдачей замените их
на собственные скриншоты с теми же именами файлов.

Запуск: python tools/gen_placeholders.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "docs" / "screens"

PLACEHOLDERS = {
    "01-swagger.png": "Swagger UI (/docs)",
    "02-ingest.png": "Тестовый запрос POST /ingest из /docs",
    "03-redis-cli.png": "redis-cli: XINFO STREAM / HGETALL / ZREVRANGE",
    "04-compose.png": "docker compose ps и логи",
    "05-incident.png": "Инцидент: 503 и восстановление Redis",
    "06-pytest.png": "pytest: 37 passed",
}


def main() -> None:
    SCREENS.mkdir(parents=True, exist_ok=True)
    for name, caption in PLACEHOLDERS.items():
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 5)
        ax.axis("off")
        ax.add_patch(FancyBboxPatch(
            (0.3, 0.3), 9.4, 4.4,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.5, edgecolor="#b85c5c", facecolor="#f8e6e6",
            linestyle="--",
        ))
        ax.text(5, 2.9, "ЗАГЛУШКА", ha="center", va="center",
                fontsize=18, color="#b85c5c", fontweight="bold")
        ax.text(5, 2.2, caption, ha="center", va="center", fontsize=13)
        ax.text(5, 1.5, "Замените на собственный скриншот с этим именем файла",
                ha="center", va="center", fontsize=9, color="#666666")
        fig.savefig(SCREENS / name, dpi=130, bbox_inches="tight")
        plt.close(fig)
    print(f"Заглушки записаны в {SCREENS}")


if __name__ == "__main__":
    main()
