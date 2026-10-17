"""Проверяет все датасеты перед обучением. Запускать перед src/train.py:

    .venv/bin/python tools/check_datasets.py                    # data/train/
    .venv/bin/python tools/check_datasets.py --dir data/pending  # черновики до применения

Проверки для каждой пары train/test:
  1. файл читается, есть колонки code/label (или lable);
  2. метки только 0/1, пустых значений нет;
  3. нет точных дублей кода внутри файла;
  4. нет противоречивой разметки (один код и как 0, и как 1);
  5. нет утечки train<->test — ни точной, ни после нормализации пробелов;
  6. классы не слишком перекошены (предупреждение, если < 30% меньшинства).

Выход с кодом 0 = всё чисто, можно обучать. Иначе — список проблем.
"""
import os
import re
import sys
from pathlib import Path

import pandas as pd

# язык → (train, test, test_ood или None); отсутствующие файлы Kotlin/C# просто пропускаются
DATASETS = {
    "C++":    ("cpp_train.csv", "cpp_test.csv", None),
    "Java":   ("java_train.csv", "java_test.csv", "java_test_ood.csv"),
    "Kotlin": ("kotlin_train.csv", "kotlin_test.csv", "kotlin_test_ood.csv"),
    "C#":     ("csharp_train.csv", "csharp_test.csv", "csharp_test_ood.csv"),
}


def normalize(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


ROOT = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
DATA_DIR = str(ROOT / "data" / "train")   # --dir data/pending → проверять черновики до применения
CUSTOM_DIR = False


def read(path):
    df = pd.read_csv(os.path.join(DATA_DIR, path), sep=";", engine="python")
    if "lable" in df.columns:
        df = df.rename(columns={"lable": "label"})
    df.columns = [c.replace("﻿", "") for c in df.columns]
    return df


def check_file(path, problems):
    try:
        df = read(path)
    except Exception as e:
        problems.append(f"{path}: не читается — {e}")
        return None

    if "code" not in df.columns or "label" not in df.columns:
        problems.append(f"{path}: нет колонок code/label (найдено: {list(df.columns)})")
        return None

    n_nan = df[["code", "label"]].isna().any(axis=1).sum()
    if n_nan:
        problems.append(f"{path}: {n_nan} строк с пустым code/label")
    df = df.dropna(subset=["code", "label"])
    df["code"] = df["code"].astype(str)

    bad_labels = set(df["label"].unique()) - {0, 1, "0", "1"}
    if bad_labels:
        problems.append(f"{path}: недопустимые метки {bad_labels} (можно только 0/1)")
        return None
    df["label"] = df["label"].astype(int)

    n_dup = df.duplicated(subset=["code"]).sum()
    if n_dup:
        problems.append(f"{path}: {n_dup} точных дублей кода")

    c0 = set(df[df["label"] == 0]["code"])
    c1 = set(df[df["label"] == 1]["code"])
    n_contra = len(c0 & c1)
    if n_contra:
        problems.append(f"{path}: {n_contra} текстов размечены и как 0, и как 1")

    counts = df["label"].value_counts()
    minority = counts.min() / counts.sum()
    if minority < 0.3:
        problems.append(f"{path}: перекос классов {dict(counts)} (меньшинство {minority:.0%}) — предупреждение")

    return df


def main():
    global DATA_DIR, CUSTOM_DIR
    if "--dir" in sys.argv:
        DATA_DIR = sys.argv[sys.argv.index("--dir") + 1]
        CUSTOM_DIR = True
    problems = []
    for lang, (train_path, test_path, ood_path) in DATASETS.items():
        if not os.path.exists(os.path.join(DATA_DIR, train_path)) and (CUSTOM_DIR or lang in ("Kotlin", "C#")):
            print(f"── {lang} ── (файлов нет — пропуск)")
            continue
        print(f"── {lang} " + "─" * 40)
        tr = check_file(train_path, problems)
        te = check_file(test_path, problems)
        if tr is None or te is None:
            continue

        exact = set(tr["code"]) & set(te["code"])
        if exact:
            problems.append(f"{lang}: {len(exact)} одинаковых текстов в train и test (утечка!)")
        normed = {normalize(c) for c in tr["code"]} & {normalize(c) for c in te["code"]}
        if normed:
            problems.append(f"{lang}: {len(normed)} почти-дублей (по пробелам) между train и test (утечка!)")

        print(f"  {train_path}: {len(tr)} строк, метки {dict(tr['label'].value_counts())}")
        print(f"  {test_path}:  {len(te)} строк, метки {dict(te['label'].value_counts())}")

        if ood_path and os.path.exists(os.path.join(DATA_DIR, ood_path)):
            ood = check_file(ood_path, problems)
            if ood is not None:
                leak = {normalize(c) for c in tr["code"]} & {normalize(c) for c in ood["code"]}
                if leak:
                    problems.append(f"{lang}: {len(leak)} примеров OOD-теста есть в train (утечка!)")
                print(f"  {ood_path}: {len(ood)} строк, метки {dict(ood['label'].value_counts())}")

    print()
    if problems:
        print("❌ НАЙДЕНЫ ПРОБЛЕМЫ:")
        for p in problems:
            print("  •", p)
        print("\nПересоберите датасеты: tools/regenerate_cpp_split.py / tools/regenerate_java_split.py "
              "или tools/build_datasets.py + tools/apply_datasets.py")
        sys.exit(1)
    print("✅ Все датасеты чистые — можно обучать: .venv/bin/python src/train.py")
    sys.exit(0)


if __name__ == "__main__":
    main()
