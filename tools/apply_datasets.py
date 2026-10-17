#!/usr/bin/env python3
"""Подключает УТВЕРЖДЁННЫЕ датасеты из data/pending/ к обучению.

    .venv/bin/python tools/apply_datasets.py            # применить (старые файлы → data/backup_<дата>/)
    .venv/bin/python tools/apply_datasets.py --dry-run  # только показать, что будет сделано

Что делает:
  1. Копирует {java,kotlin,csharp}_{train,test,test_ood}.csv из data/pending/ в data/train/.
  2. Если в data/train/ уже лежат такие файлы — сначала сохраняет их в data/backup_<дата>/.
  3. Запускает tools/check_datasets.py (валидатор) и сообщает результат.

Запускать ТОЛЬКО после того, как вы просмотрели data/pending/DATASET_REPORT.md.
"""
import argparse
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
PENDING = ROOT / "data" / "pending"
TRAIN = ROOT / "data" / "train"
NAMES = [f"{lang}_{part}.csv" for lang in ("java", "kotlin", "csharp") for part in ("train", "test", "test_ood")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not PENDING.exists():
        print("data/pending/ не найден — сначала запустите tools/build_datasets.py")
        return 1

    todo = [n for n in NAMES if (PENDING / n).exists()]
    if not todo:
        print("В data/pending/ нет файлов для применения")
        return 1

    backup = ROOT / "data" / f"backup_{datetime.date.today().isoformat()}"
    for name in todo:
        src, dst = PENDING / name, TRAIN / name
        if dst.exists():
            print(f"  резервная копия: {name} → data/{backup.name}/")
            if not args.dry_run:
                backup.mkdir(exist_ok=True)
                shutil.copy2(dst, backup / name)
        print(f"  применяю: {name}")
        if not args.dry_run:
            shutil.copy2(src, dst)

    if args.dry_run:
        print("\n(dry-run: ничего не изменено)")
        return 0

    print("\nПроверка датасетов…")
    return subprocess.call([sys.executable, str(Path(__file__).resolve().parent / "check_datasets.py")])


if __name__ == "__main__":
    raise SystemExit(main())
