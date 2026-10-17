"""Пересобирает java_train.csv / java_test.csv.

Источники:
1. javadata.csv — чистые пары (человеческий оригинал=0; ИИ-вариант=1),
   654 строки, ноль противоречивых меток. База: делится group-aware
   сплитом 80/20 (пара всегда целиком на одной стороне, иначе оригинал и
   его почти-двойник утекли бы между train и test).
2. old_java_train.csv / old_java_test.csv (восстановлены из git) — другой
   набор пар с другим стилем ИИ-вариантов. Их метки были зашумлены
   (31 код размечен и как 0, и как 1) — противоречивые тексты выбрасываем,
   остальное добавляем ЦЕЛИКОМ в train (в test не попадают, чтобы тест
   остался чистым и сравнимым).
3. java_ai_generated.csv (создаётся make_java_ai_samples.py) — Java-код,
   сгенерированный ИИ «с нуля» по типовым задачам (label=1). Это главное,
   чего не хватало: в C++-датасете есть 162 таких примера и C++-детектор
   работает; в Java класс «ИИ» состоял только из переписанного чужого кода,
   поэтому настоящий сгенерированный код модель не распознавала. Только train.
4. Аугментация (только train): копия каждого примера без строк package/import.
   Без неё модель, обученная на полных файлах (100% с package), выдавала
   ~99.9% «ИИ» на любом сниппете без шапки — весь незнакомый формат
   сваливался в один класс.

Тест — только отложенные группы javadata.csv: чистый, сбалансированный.
"""
import os
import re
from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

# корень проекта: папка над tools/ (в Docker задаётся CODECHECK_ROOT)
ROOT    = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
SOURCES = ROOT / "data" / "sources"
TRAIN   = ROOT / "data" / "train"

SOURCE          = SOURCES / "javadata.csv"
OLD_TRAIN       = SOURCES / "old_java_train.csv"
OLD_TEST        = SOURCES / "old_java_test.csv"
AI_GENERATED    = SOURCES / "java_ai_generated.csv"   # см. make_java_ai_samples.py
TRAIN_OUT       = TRAIN / "java_train.csv"
TEST_OUT        = TRAIN / "java_test.csv"
TEST_SIZE       = 0.2
SEED            = 42


def normalize(code: str) -> str:
    """Нормализация для поиска почти-дублей: убираем все пробельные различия."""
    return re.sub(r"\s+", " ", code).strip()


def strip_header(code: str) -> str:
    """Убирает строки package/import — имитация вставки «голого» сниппета."""
    lines = [l for l in code.splitlines()
             if not re.match(r"\s*(package|import)\s", l)]
    return "\n".join(lines).strip()


def read_any(path):
    df = pd.read_csv(path, sep=";", engine="python")
    if "lable" in df.columns:
        df = df.rename(columns={"lable": "label"})
    df.columns = [c.replace("﻿", "") for c in df.columns]
    df = df.dropna(subset=["code", "label"]).reset_index(drop=True)
    df["code"]  = df["code"].astype(str)
    df["label"] = df["label"].astype(int)
    return df


def read_java_with_pair_groups(path):
    df = read_any(path)
    # group-id считаем ДО удаления дублей, чтобы позиции пар не «поплыли».
    df["group"] = [f"pair_{i // 2}" for i in range(len(df))]
    df = df.drop_duplicates(subset=["code"]).reset_index(drop=True)
    return df[["code", "label", "group"]]


def main():
    # ── база: чистые пары javadata ─────────────────────────────────────────
    data = read_java_with_pair_groups(SOURCE)
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    train_idx, test_idx = next(splitter.split(data, groups=data["group"]))
    # group сохраняем в train: по нему src/train.py отрезает валидацию, не разрывая пары
    # и не разводя пример с его копией без package/import
    train = data.iloc[train_idx][["code", "label", "group"]].reset_index(drop=True)
    test  = data.iloc[test_idx][["code", "label"]].reset_index(drop=True)

    test_norms = {normalize(c) for c in test["code"]}

    # ── старые данные: чистим и добавляем только в train ───────────────────
    # файлы восстановлены из git (git show d4627d5:java_train.csv и т.д.);
    # если их нет — пропускаем с предупреждением, а не падаем
    if os.path.exists(OLD_TRAIN) and os.path.exists(OLD_TEST):
        old = pd.concat([read_any(OLD_TRAIN), read_any(OLD_TEST)], ignore_index=True)
        # ВАЖНО: противоречия ищем ДО дедупликации — иначе dedup оставит одну
        # копию с произвольной меткой и конфликт станет невидимым
        o0 = set(old[old["label"] == 0]["code"])
        o1 = set(old[old["label"] == 1]["code"])
        contradictory = o0 & o1
        old = old[~old["code"].isin(contradictory)]
        old = old.drop_duplicates(subset=["code"])
        # не допускаем почти-дублей с тестом (после нормализации пробелов)
        old = old[~old["code"].map(normalize).isin(test_norms)]
        print(f"старые данные: добавляем {len(old)} строк в train "
              f"(выброшено противоречивых текстов: {len(contradictory)})")
        old = old.assign(group=[f"old_{i}" for i in range(len(old))])
        train = pd.concat([train, old[["code", "label", "group"]]], ignore_index=True)
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {OLD_TRAIN}/{OLD_TEST} не найдены — пропускаем. "
              f"Восстановить из коммита d4627d5: git show d4627d5:java_train.csv > {OLD_TRAIN} "
              f"&& git show d4627d5:java_test.csv > {OLD_TEST}")

    # ── ИИ-код, сгенерированный с нуля: только в train ──────────────────────
    if os.path.exists(AI_GENERATED):
        ai_gen = read_any(AI_GENERATED)
        ai_gen = ai_gen.drop_duplicates(subset=["code"])
        ai_gen = ai_gen[~ai_gen["code"].map(normalize).isin(test_norms)]
        print(f"ИИ-код с нуля: добавляем {len(ai_gen)} строк в train")
        ai_gen = ai_gen.assign(group=[f"aigen_{i}" for i in range(len(ai_gen))])
        train = pd.concat([train, ai_gen[["code", "label", "group"]]], ignore_index=True)
    else:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {AI_GENERATED} не найден — сгенерируйте: "
              f".venv/bin/python tools/make_java_ai_samples.py")

    # ── аугментация train: варианты без package/import ─────────────────────
    aug = train.copy()   # копия наследует group оригинала
    aug["code"] = aug["code"].map(strip_header)
    aug = aug[aug["code"].str.len() > 50]              # пустышки не берём
    aug = aug[~aug["code"].isin(set(train["code"]))]   # только реально новые
    aug = aug[~aug["code"].map(normalize).isin(test_norms)]
    print(f"аугментация: +{len(aug)} вариантов без package/import")
    train = pd.concat([train, aug], ignore_index=True)

    train = train.drop_duplicates(subset=["code"]).reset_index(drop=True)
    # финальная страховка: в javadata изредка встречаются почти-дубли между
    # разными парами — убираем из train всё, что нормализованно совпадает с тестом
    train = train[~train["code"].map(normalize).isin(test_norms)].reset_index(drop=True)
    train = train.sample(frac=1, random_state=SEED).reset_index(drop=True)  # перемешиваем

    train.to_csv(TRAIN_OUT, sep=";", index=False, lineterminator="\r\n")
    test.to_csv(TEST_OUT, sep=";", index=False, lineterminator="\r\n")

    overlap = {normalize(c) for c in train["code"]} & test_norms
    c0 = set(train[train["label"] == 0]["code"]) | set(test[test["label"] == 0]["code"])
    c1 = set(train[train["label"] == 1]["code"]) | set(test[test["label"] == 1]["code"])

    print()
    print(f"{TRAIN_OUT.name}: {len(train)} строк, {dict(train['label'].value_counts())}")
    print(f"{TEST_OUT.name}: {len(test)} строк, {dict(test['label'].value_counts())}")
    print(f"Пересечение (нормализ.) train/test (должно быть 0): {len(overlap)}")
    print(f"Противоречивых меток (код и как 0, и как 1): {len(c0 & c1)}")


if __name__ == "__main__":
    main()
