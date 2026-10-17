"""Пересобирает cpp_train.csv / cpp_test.csv из cppdata.csv.

Запускать заново, если cppdata.csv изменился (добавились новые строки).

Начиная со строки N_SINGLETON_ROWS, cppdata.csv состоит из пар
(оригинальный код; его переписанный ИИ-вариант одного и того же файла),
добавленных подряд. Обычный train_test_split может развести пару по разным
сторонам train/test — модель будет "подсматривать" почти тот же код и
давать завышенную, недостоверную точность. Поэтому используется
group-aware split (GroupShuffleSplit): каждая пара всегда целиком остаётся
на одной стороне разбиения. Строки до N_SINGLETON_ROWS не имеют известной
пары и разбиваются по отдельности.

Дополнительно:
- тексты с противоречивой разметкой (один код и как 0, и как 1) выбрасываются
  целиком (ищутся ДО дедупликации, иначе конфликт маскируется);
- из train убираются почти-дубли теста (совпадение после нормализации
  пробелов) — иначе тестовая точность завышается;
- EXTRA_HUMAN_SOURCES добавляются ТОЛЬКО в train (см. README.md, раздел «Ограничения»):
  cppdata.csv почти не содержит короткого, чисто написанного человеческого
  кода — модель научилась путать "аккуратно" с "ИИ". cpp_human_codecontests.csv
  (fetch_human_cpp_codecontests.py) — реальные решения с судей Codeforces/
  CodeChef/… из датасета DeepMind CodeContests (релиз февраль 2022, до ChatGPT —
  авторство человека гарантировано датой), все с label=0. Test не трогаем,
  чтобы метрики на нём оставались сравнимы с прошлым прогоном.
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

SOURCE             = SOURCES / "cppdata.csv"
EXTRA_HUMAN_SOURCES = [SOURCES / "cpp_human_codecontests.csv"]
TRAIN_OUT          = TRAIN / "cpp_train.csv"
TEST_OUT           = TRAIN / "cpp_test.csv"
N_SINGLETON_ROWS   = 293  # исходные строки cppdata.csv до появления пар оригинал/ИИ-вариант
TEST_SIZE          = 0.2
SEED               = 42


def normalize(code: str) -> str:
    """Нормализация для поиска почти-дублей: убираем все пробельные различия."""
    return re.sub(r"\s+", " ", code).strip()


def read_cpp_with_pair_groups(path, n_singleton_rows):
    df = pd.read_csv(path, sep=";", engine="python")
    if "lable" in df.columns:
        df = df.rename(columns={"lable": "label"})
    df.columns = [c.replace("﻿", "") for c in df.columns]
    df = df.dropna(subset=["code", "label"]).reset_index(drop=True)
    df["code"]  = df["code"].astype(str)
    df["label"] = df["label"].astype(int)

    # group-id считаем ДО удаления дублей, чтобы позиции совпадали со
    # структурой файла (иначе индексы пар "поплывут")
    groups = []
    for i in range(len(df)):
        if i < n_singleton_rows:
            groups.append(f"single_{i}")
        else:
            pair_idx = (i - n_singleton_rows) // 2
            groups.append(f"pair_{pair_idx}")
    df["group"] = groups

    # противоречивая разметка: один и тот же код и как 0, и как 1 —
    # выбрасываем такие тексты целиком (проверка ДО дедупликации)
    c0 = set(df[df["label"] == 0]["code"])
    c1 = set(df[df["label"] == 1]["code"])
    contradictory = c0 & c1
    if contradictory:
        print(f"выброшено текстов с противоречивой разметкой: {len(contradictory)}")
        df = df[~df["code"].isin(contradictory)]

    df = df.drop_duplicates(subset=["code"]).reset_index(drop=True)
    return df[["code", "label", "group"]]


def read_extra_human(path, exclude_codes):
    """Доп. источник человеческого кода (только label=0). exclude_codes —
    множество кодов, уже встреченных где-либо (из cppdata.csv), чтобы не
    задублировать то, что уже есть."""
    df = pd.read_csv(path, sep=";", engine="python")
    df.columns = [c.replace("﻿", "") for c in df.columns]
    df = df.dropna(subset=["code", "label"]).reset_index(drop=True)
    df["code"]  = df["code"].astype(str).str.strip()
    df["label"] = df["label"].astype(int)
    df = df[df["label"] == 0]
    df = df.drop_duplicates(subset=["code"])
    df = df[~df["code"].isin(exclude_codes)]
    return df[["code", "label"]]


def main():
    cpp_all = read_cpp_with_pair_groups(SOURCE, N_SINGLETON_ROWS)

    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    train_idx, test_idx = next(splitter.split(cpp_all, groups=cpp_all["group"]))
    # group сохраняем в train: по нему src/train.py отрезает валидацию, не разрывая пары
    train_cpp = cpp_all.iloc[train_idx][["code", "label", "group"]].reset_index(drop=True)
    test_cpp  = cpp_all.iloc[test_idx][["code", "label"]].reset_index(drop=True)

    # почти-дубли теста (после нормализации пробелов) убираем из train
    test_norms = {normalize(c) for c in test_cpp["code"]}
    before = len(train_cpp)
    train_cpp = train_cpp[~train_cpp["code"].map(normalize).isin(test_norms)].reset_index(drop=True)
    if before != len(train_cpp):
        print(f"убрано из train почти-дублей теста: {before - len(train_cpp)}")

    # ── доп. источники человеческого кода — только в train (test не трогаем) ──
    all_known_codes = set(cpp_all["code"])
    for extra_path in EXTRA_HUMAN_SOURCES:
        if not os.path.exists(extra_path):
            print(f"ПРЕДУПРЕЖДЕНИЕ: {extra_path.name} не найден — пропускаем "
                  f"(создать: .venv/bin/python tools/fetch_human_cpp_codecontests.py)")
            continue
        extra = read_extra_human(extra_path, all_known_codes)
        extra = extra[~extra["code"].map(normalize).isin(test_norms)]
        extra = extra.assign(group=[f"{extra_path.stem}_{i}" for i in range(len(extra))])  # у каждого своя группа
        print(f"{extra_path.name}: добавляем {len(extra)} человеческих строк в train")
        train_cpp = pd.concat([train_cpp, extra], ignore_index=True)
        all_known_codes |= set(extra["code"])

    train_cpp = train_cpp.drop_duplicates(subset=["code"]).reset_index(drop=True)
    train_cpp = train_cpp.sample(frac=1, random_state=SEED).reset_index(drop=True)

    train_cpp.to_csv(TRAIN_OUT, sep=";", index=False, lineterminator="\r\n")
    test_cpp.to_csv(TEST_OUT, sep=";", index=False, lineterminator="\r\n")

    overlap = {normalize(c) for c in train_cpp["code"]} & test_norms

    print(f"{TRAIN_OUT.name}: {len(train_cpp)} строк, {dict(train_cpp['label'].value_counts())}")
    print(f"{TEST_OUT.name}: {len(test_cpp)} строк, {dict(test_cpp['label'].value_counts())}")
    print(f"Пересечение (нормализ.) train/test (должно быть 0): {len(overlap)}")


if __name__ == "__main__":
    main()
