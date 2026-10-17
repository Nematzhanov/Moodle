#!/usr/bin/env python3
"""Собирает датасеты «человек (0) vs ИИ (1)» для Java, Kotlin и C#.

Запуск:
    .venv/bin/python tools/build_datasets.py                 # все три языка
    .venv/bin/python tools/build_datasets.py --lang java     # только один
    .venv/bin/python tools/build_datasets.py --no-codemirage # без CodeMirage (лицензия CC-BY-NC-ND)

Результат (ничего из существующих файлов проекта НЕ перезаписывается):
    data/pending/{java,kotlin,csharp}_{train,test,test_ood}.csv
    data/pending/DATASET_REPORT.md   — состав, лицензии, диагностика, примеры
    data/pending/manifest.json

Принципы (почему эти датасеты лучше прежних):
  1. ОДНО РАСПРЕДЕЛЕНИЕ для обоих классов. Человек и ИИ берутся из одних и тех же
     задач (Rosetta Code, LeetCode/Codeforces-подобные, учебники) — модель учит
     авторство, а не «откуда файл».
  2. Нормализация артефактов источника: лицензионные шапки, `package`, `@author`,
     табы, пробелы в конце строк, пустые строки подряд. Раньше «есть шапка Copyright
     → человек» — из-за этого любой студенческий код без шапки объявлялся ИИ.
  3. Подбор по длине (length-matching): в каждом диапазоне длин поровну людей и ИИ —
     иначе длина становится «шорткатом» (так уже было в первой версии проекта).
  4. Разбиение по ГРУППАМ (одна задача = одна группа): ни одна задача не попадает
     одновременно в train и test.
  5. test_ood — отдельный тест на НЕВИДЕННЫХ генераторах/источниках: честная оценка
     обобщения, а не запоминания.
  6. Диагностика шорткатов: простая модель на поверхностных признаках и на n-граммах;
     если она «угадывает» слишком хорошо — датасет всё ещё содержит утечку признака.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download, snapshot_download

ROOT = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
SOURCES = ROOT / "data" / "sources"
OUT = ROOT / "data" / "pending"
SEED = 42
MAX_CHARS = 2600          # хранимая длина (модель всё равно видит ~512 токенов ≈ 1800–2400 символов)
MIN_CHARS = 150
TEST_PERCENT = 15         # доля групп, уходящая в test

TARGETS = {               # размеры ПОСЛЕ балансировки (на класс = половина)
    "java":   dict(train=6000, test=800, ood=600),
    "kotlin": dict(train=5000, test=700, ood=500),
    "csharp": dict(train=5000, test=700, ood=500),
}

# генераторы CodeMirage, которые НЕ попадают в train (проверка на невиданных моделях)
CODEMIRAGE_HOLDOUT = {"llama3.3-70b", "gemini-2.0-flash-thinking-exp"}
# разрешённые лицензии человеческого Kotlin-кода (KStack-clean)
PERMISSIVE = ("Apache", "MIT", "Unlicense", "Creative Commons Zero", "ISC", "BSD")


# ───────────────────────── нормализация ─────────────────────────

LICENSE_RE = re.compile(
    r"copyright|licen[sc]e|all rights reserved|permission is hereby granted|spdx|"
    r"apache|gnu general|redistribut", re.I)
LEAK_RE = re.compile(r"\b(chat\s?gpt|openai|gpt-?\d|as an ai|language model|claude|gemini|copilot)\b", re.I)
META_LINE_RE = re.compile(r"^.*(@author|@since|@version|Created by|\bAuthor:|\bCreated on\b).*\n?", re.M)


def norm_ws(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


def code_hash(code: str) -> str:
    return hashlib.sha1(norm_ws(code).encode("utf-8", "ignore")).hexdigest()


def strip_leading_license(s: str) -> str:
    """Убирает ведущие комментарии-шапки с лицензией/копирайтом (но не javadoc класса)."""
    s = s.lstrip("﻿\n \t")
    while True:
        m = re.match(r"/\*.*?\*/[ \t]*\n*", s, re.S)
        if m and LICENSE_RE.search(m.group(0)):
            s = s[m.end():]
            continue
        m = re.match(r"(?:[ \t]*//[^\n]*\n)+", s)
        if m and LICENSE_RE.search(m.group(0)):
            s = s[m.end():]
            continue
        return s


# Шаблонные имена классов/пространств имён — прямой шорткат источника (LeetCode: `Solution`,
# учебник: `Exercise_8_5`, шаблон Visual Studio: `ConsoleApplication1`). Заменяются на случайное имя
# из общего списка НЕЗАВИСИМО от метки — иначе `class Main` → «ИИ», `class Solution` → «человек».
TEMPLATE_NAME_RE = re.compile(
    r"^(Solution|Main|Program|Test|Tests|Exercise\w*|ConsoleApplication\d*|ConsoleApp\d*|Class\d*|"
    r"HelloWorld|Example|Demo|App|Application)$")
GENERIC_NAMES = ["Main", "Solution", "Program", "Calculator", "Counter", "Checker", "Converter", "Sorter",
                 "Parser", "Helper", "Processor", "Manager", "Service", "Utils", "Handler", "Builder",
                 "Finder", "Matrix", "Stack", "Queue", "Graph", "Tree", "Account", "Student", "Library",
                 "Game", "Timer", "Cache", "Logger", "Validator", "Generator", "Reader", "Writer", "Task",
                 "Runner", "Shape", "Vector", "Order", "Product", "Employee"]
AOC_RE = re.compile(r"fun\s+part[12]\b|\bDay\d+\b|\breadInput\b|\bpart[12]\s*\(|\(\s*input\s*:")
KT_MODIFIER_RE = re.compile(r"^(\s*)(?:(?:private|internal|public|protected|override|inline|tailrec)\s+)+(?=(?:suspend\s+)?fun\b)", re.M)


def neutralize_names(code: str, lang: str) -> str:
    if lang not in ("java", "csharp"):
        return code
    rng = random.Random(int(hashlib.md5(code.encode("utf-8", "ignore")).hexdigest()[:8], 16))
    names = [n for n in dict.fromkeys(re.findall(r"\b(?:class|namespace)\s+([A-Za-z_]\w*)", code))
             if TEMPLATE_NAME_RE.match(n)]
    if not names:
        return code
    pool = [n for n in GENERIC_NAMES if n not in set(re.findall(r"\b[A-Z]\w+\b", code))]
    rng.shuffle(pool)
    for old, new in zip(names, pool):
        code = re.sub(rf"\b{re.escape(old)}\b", new, code)
    return code


def clean_code(code, lang: str):
    """Нормализует один пример. Возвращает None, если пример непригоден."""
    if not isinstance(code, str):
        return None
    c = code.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    if "<auto-generated" in c[:500].lower() or "generated by" in c[:300].lower():
        return None
    if "```" in c or LEAK_RE.search(c) or re.match(r"\s*(here|sure|certainly|below)\b", c, re.I):
        return None                      # markdown/самоссылки на ИИ — прямая утечка метки
    c = strip_leading_license(c)
    if lang in ("java", "kotlin"):
        c = re.sub(r"^\s*package\s+[\w.]+\s*;?[ \t]*\n", "", c, flags=re.M)
    c = META_LINE_RE.sub("", c)
    c = re.sub(r"^[ \t]*//\s*[Vv]ersion\s+[\d.]+.*\n?", "", c, flags=re.M)      # конвенция Rosetta (Kotlin)
    c = re.sub(r"^[ \t]*#(?:end)?region.*\n?", "", c, flags=re.M)                  # C#: #region/#endregion
    if lang == "kotlin":
        if AOC_RE.search(c):
            return None                                                             # Advent of Code — тематический шорткат
        c = KT_MODIFIER_RE.sub(r"\1", c)                                            # private/override/... — артефакт членов класса
    c = neutralize_names(c, lang)
    c = c.expandtabs(4)
    c = re.sub(r"[ \t]+\n", "\n", c)
    c = re.sub(r"\n{3,}", "\n\n", c).strip("\n")
    if len(c) < MIN_CHARS:
        return None
    # код с большим количеством не-ASCII (другие языки комментариев) — шорткат по языку текста
    if sum(ord(ch) > 127 for ch in c) / len(c) > 0.02:
        return None
    if max((len(line) for line in c.split("\n")), default=0) > 300:   # минифицированное/данные
        return None
    if len(c) > MAX_CHARS:
        cut = c.rfind("\n", 0, MAX_CHARS)
        c = c[: cut if cut > MAX_CHARS * 0.5 else MAX_CHARS].rstrip()
    return c


STUB_RE = re.compile(r"implementation goes here|your code here|todo: implement|\.\.\.\s*$|pass\s*$", re.I | re.M)
METHOD_RE = re.compile(r"[\w<>\[\],\s?]+\s+\w+\s*\([^)]*\)\s*(?:throws [\w.,\s]+)?\s*\{")


def looks_like_java_method(code: str) -> bool:
    """Отсекает заглушки и «примеры использования» в ИИ-выводе функционального уровня."""
    if STUB_RE.search(code) or not METHOD_RE.search(code):
        return False
    if code.count("{") != code.count("}") or code.count("\n") < 4:
        return False
    return True


# ───────────────────── извлечение функций (Kotlin) ─────────────────────

FUN_RE = re.compile(
    r"^(?P<indent>)(?:(?:private|public|internal|protected|override|inline|suspend|operator|"
    r"tailrec|open|abstract)\s+)*fun\s+(?:<[^>]+>\s+)?[\w.<>?]+\s*\(", re.M)


def extract_kotlin_functions(content: str, rng: random.Random, max_per_file: int = 2):
    lines = content.replace("\r\n", "\n").split("\n")
    starts = [i for i, l in enumerate(lines) if FUN_RE.match(l)]
    found = []
    for i in starts:
        # тянем KDoc/комментарий непосредственно над функцией
        j = i
        while j > 0 and lines[j - 1].lstrip().startswith(("*", "/**", "*/", "//")):
            j -= 1
        depth, opened, end = 0, False, None
        for k in range(i, min(i + 60, len(lines))):
            for ch in lines[k]:
                if ch == "{":
                    depth += 1
                    opened = True
                elif ch == "}":
                    depth -= 1
            if opened and depth == 0:
                end = k
                break
        if end is None:
            continue
        block = textwrap.dedent("\n".join(lines[j: end + 1]))
        n = block.count("\n") + 1
        if 4 <= n <= 45:
            found.append(block)
    rng.shuffle(found)
    return found[:max_per_file]


# ───────────────────── загрузка источников ─────────────────────

def hf(repo: str, filename: str) -> str:
    return hf_hub_download(repo, filename, repo_type="dataset")


def frame(rows, **const):
    df = pd.DataFrame(rows, columns=["code", "label", "source", "generator", "group"])
    for k, v in const.items():
        df[k] = v
    return df


def load_rosetta(lang_name: str, lang: str) -> pd.DataFrame:
    """Rosetta Code: человек vs StarCoder2, пары по задаче (task_name)."""
    p = hf("isThisYouLLM/H-AIRosettaMP", "data/train-00000-of-00001.parquet")
    df = pd.read_parquet(p, columns=["task_name", "language_name", "code", "target"])
    df = df[df.language_name == lang_name]
    rows = []
    for code, tgt, task in zip(df.code, df.target, df.task_name):
        c = clean_code(code, lang)
        if c:
            ai = tgt == "Ai_generated"
            rows.append((c, int(ai), "rosetta", "starcoder2" if ai else "human", f"rosetta:{task}"))
    return frame(rows)


def load_codemirage(cm_lang: str, lang: str) -> pd.DataFrame:
    """CodeMirage: 10 LLM (variant=Normal) + человеческие GitHub-файлы. Группа = номер задачи."""
    parts = []
    for fname in ("train.csv", "test.csv"):
        p = hf("HanxiGuo/CodeMirage", fname)
        for chunk in pd.read_csv(p, chunksize=20000, usecols=["code", "language", "source", "variant"]):
            chunk = chunk[(chunk.language == cm_lang) & (chunk.variant.isin(["Normal"]) | (chunk.source == "Human"))]
            chunk = chunk.assign(file=fname)
            parts.append(chunk)
    cm = pd.concat(parts, ignore_index=True)
    cm["idx"] = cm.groupby(["file", "source"]).cumcount()
    rows = []
    for code, src, file, idx in zip(cm.code, cm.source, cm.file, cm.idx):
        c = clean_code(code, lang)
        if c:
            ai = src != "Human"
            rows.append((c, int(ai), "codemirage", src if ai else "human", f"cm:{file}:{idx}"))
    return frame(rows)


def load_hvai_java(max_rows: int = 40000) -> pd.DataFrame:
    """HumanVsAICode: функции Java — человек vs ChatGPT/DeepSeek/Qwen (группа = hm_index)."""
    p = hf("OSS-forge/HumanVsAICode", "java_dataset.jsonl")
    rng = random.Random(SEED)
    rows = []
    with open(p, encoding="utf-8") as fh:
        for n, line in enumerate(fh):
            if n >= max_rows:
                break
            r = json.loads(line)
            h = clean_code(r.get("human_code"), "java")
            if h and looks_like_java_method(h):
                rows.append((h, 0, "hvai", "human", f"hvai:{r['hm_index']}"))
            gens = [(k, g) for k, g in (("chatgpt_code", "chatgpt"), ("dsc_code", "deepseek"), ("qwen_code", "qwen"))
                    if r.get(k)]
            rng.shuffle(gens)
            for key, g in gens:
                a = clean_code(r[key], "java")
                if a and looks_like_java_method(a):
                    rows.append((a, 1, "hvai", g, f"hvai:{r['hm_index']}"))
                    break
    return frame(rows)


def load_semeval_java() -> pd.DataFrame:
    """SemEval-2026 Task 13: решения задач (LeetCode/Codeforces-подобные) — человек vs ~35 открытых LLM."""
    rows = []
    for fname in ("task_a/task_a_training_set_1.parquet", "task_a/task_a_validation_set.parquet"):
        df = pd.read_parquet(hf("DaniilOr/SemEval-2026-Task13", fname), filters=[("language", "==", "Java")])
        for code, lab, gen in zip(df.code, df.label, df.generator):
            c = clean_code(code, "java")
            if c:
                rows.append((c, int(lab), "semeval", "human" if lab == 0 else gen, f"semeval:{code_hash(c)[:12]}"))
    return frame(rows)


def load_gptsniffer(split: str) -> pd.DataFrame:
    """GPTSniffer: студенческий/учебниковый Java vs ChatGPT. В их именах 0_=ChatGPT, 1_=человек."""
    root = snapshot_download("mahirlabibdihan/GPTSniffer", repo_type="dataset")
    rows = []
    for path in sorted(glob.glob(os.path.join(root, split, "*.java"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8", errors="ignore") as fh:
            c = clean_code(fh.read(), "java")
        if not c:
            continue
        ai = name.startswith("0_")
        rows.append((c, int(ai), "gptsniffer", "chatgpt" if ai else "human", f"gs:{name[2:]}"))
    return frame(rows)


def load_local_java() -> pd.DataFrame:
    """Свои данные проекта: javadata.csv (пары человек/ИИ) и java_ai_generated.csv (ИИ с нуля)."""
    rows = []
    p = SOURCES / "javadata.csv"
    if p.exists():
        df = pd.read_csv(p, sep=";", engine="python").rename(columns={"lable": "label"})
        for i, (code, lab) in enumerate(zip(df["code"], df["label"])):
            c = clean_code(code, "java")
            if c:
                rows.append((c, int(lab), "local_pairs", "human" if lab == 0 else "local_ai", f"local:{i // 2}"))
    p = SOURCES / "java_ai_generated.csv"
    if p.exists():
        df = pd.read_csv(p, sep=";", engine="python")
        for i, code in enumerate(df["code"]):
            c = clean_code(code, "java")
            if c:
                rows.append((c, 1, "claude_handwritten", "claude", f"claude:{i}"))
    return frame(rows)


def load_kstack_functions(rng: random.Random) -> pd.DataFrame:
    """KStack-clean: человеческие функции Kotlin из GitHub (только разрешающие лицензии)."""
    p = hf("JetBrains/KStack-clean", "data/train-00000-of-00001.parquet")
    df = pd.read_parquet(p, columns=["content", "repo_id", "license"])
    df = df[df.license.fillna("").str.contains("|".join(PERMISSIVE))]
    rows = []
    for content, repo in zip(df.content, df.repo_id):
        for fn in extract_kotlin_functions(content, rng):
            c = clean_code(fn, "kotlin")
            if c and len(c) >= 200:
                rows.append((c, 0, "kstack", "human", f"kstack:{repo}"))
    return frame(rows)


def load_kexercises() -> pd.DataFrame:
    """KExercises: функции Kotlin, сгенерированные GPT-3.5 (problem = сигнатура+KDoc, solution = тело)."""
    p = hf("JetBrains/KExercises", "data/train-00000-of-00001.parquet")
    df = pd.read_parquet(p)
    rows = []
    for prob, sol in zip(df.problem, df.solution):
        code = f"{prob.rstrip()}\n{sol.rstrip()}"
        if code.count("{") > code.count("}"):
            code += "\n}"
        c = clean_code(re.sub(r"^import .*\n", "", code, flags=re.M), "kotlin")
        if c and c.count("{") == c.count("}"):
            rows.append((c, 1, "kexercises", "gpt-3.5", f"kex:{code_hash(prob)[:12]}"))
    return frame(rows)


def load_rlvr_kotlin() -> pd.DataFrame:
    """rlvr-code-data-Kotlin: решения Kotlin, переведённые/сгенерированные современной LLM."""
    p = hf("saurabh5/rlvr-code-data-Kotlin", "data/train-00000-of-00002.parquet")
    df = pd.read_parquet(p, columns=["translated_problem", "translated_solution"])
    rows = []
    for prob, sol in zip(df.translated_problem, df.translated_solution):
        c = clean_code(re.sub(r"^import .*\n", "", str(sol), flags=re.M), "kotlin")
        if c and c.count("{") == c.count("}"):
            rows.append((c, 1, "rlvr", "llm-modern", f"rlvr:{code_hash(str(prob))[:12]}"))
    return frame(rows)


def load_lcc_csharp(max_rows: int = 12000) -> pd.DataFrame:
    """LCC_csharp: человеческие C#-файлы с GitHub (берём начало файла)."""
    p = hf("microsoft/LCC_csharp", "data/train-00000-of-00004-6cd7af23c16b0001.parquet")
    df = pd.read_parquet(p, columns=["context"]).head(max_rows)
    rows = []
    for ctx in df.context:
        c = clean_code(ctx, "csharp")
        if c:
            rows.append((c, 0, "lcc", "human", f"lcc:{code_hash(c)[:12]}"))
    return frame(rows)


# ───────────────────── сборка ─────────────────────

def stable_pct(lang: str, group: str) -> int:
    return int(hashlib.sha1(f"{lang}:{group}".encode()).hexdigest(), 16) % 100


def dedup_and_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["h"] = df.code.map(code_hash)
    both = set(df[df.label == 0].h) & set(df[df.label == 1].h)     # ДО дедупликации
    df = df[~df.h.isin(both)].drop_duplicates("h")
    return df


def balanced_take(df: pd.DataFrame, n: int, by: str, rng: np.random.Generator) -> pd.DataFrame:
    """Берёт n строк, выравнивая вклад категорий `by` (water-filling)."""
    if n >= len(df):
        return df
    groups = {k: g.sample(frac=1, random_state=int(rng.integers(1 << 30))) for k, g in df.groupby(by)}
    take = {k: 0 for k in groups}
    left = n
    while left > 0 and any(take[k] < len(groups[k]) for k in groups):
        active = [k for k in groups if take[k] < len(groups[k])]
        share = max(left // len(active), 1)
        for k in active:
            add = min(share, len(groups[k]) - take[k], left)
            take[k] += add
            left -= add
            if left == 0:
                break
    return pd.concat([groups[k].iloc[: take[k]] for k in groups])


def length_match(df: pd.DataFrame, rng: np.random.Generator, bins: int = 14) -> pd.DataFrame:
    """В каждом диапазоне длины оставляет поровну людей и ИИ (колонка `_bin` сохраняется)."""
    if df.label.nunique() < 2:
        return df.iloc[0:0]
    L = df.code.str.len().to_numpy()
    edges = np.unique(np.quantile(L, np.linspace(0, 1, bins + 1)))
    df = df.assign(_bin=np.clip(np.searchsorted(edges, L, side="right") - 1, 0, len(edges) - 2))
    out = []
    for _, g in df.groupby("_bin"):
        h, a = g[g.label == 0], g[g.label == 1]
        k = min(len(h), len(a))
        if k:
            out += [h.sample(k, random_state=int(rng.integers(1 << 30))),
                    a.sample(k, random_state=int(rng.integers(1 << 30)))]
    return pd.concat(out) if out else df.iloc[0:0]


def water_fill(total: int, weights: dict, caps: dict) -> dict:
    """Делит `total` между семьями пропорционально весам, не превышая лимиты (остаток перераспределяется)."""
    alloc = {k: 0 for k in caps}
    left = total
    for _ in range(50):
        active = {k: weights.get(k, 0.02) for k in caps if alloc[k] < caps[k]}
        if not active or left <= 0:
            break
        tw = sum(active.values())
        gave = 0
        for k, w in active.items():
            add = min(caps[k] - alloc[k], max(int(round(left * w / tw)), 1))
            add = min(add, left - gave)
            alloc[k] += add
            gave += add
        left -= gave
        if gave == 0:
            break
    return alloc


def sample_matched(m: pd.DataFrame, k: int, rng: np.random.Generator) -> pd.DataFrame:
    """k людей + k ИИ из уже подобранного по длине набора, с сохранением распределения по бинам."""
    n_pairs = int((m.label == 0).sum())
    if k >= n_pairs:
        return m
    frac = k / n_pairs
    out = []
    for _, g in m.groupby("_bin"):
        for lab in (0, 1):
            gl = g[g.label == lab]
            out.append(gl.sample(min(len(gl), int(round(len(gl) * frac))), random_state=int(rng.integers(1 << 30))))
    res = pd.concat(out)
    kk = min((res.label == 0).sum(), (res.label == 1).sum())
    return pd.concat([res[res.label == lab].iloc[:kk] for lab in (0, 1)])


def compose(pool: pd.DataFrame, n_total: int, weights: dict, seed: int) -> pd.DataFrame:
    """Сбалансированная выборка. Внутри каждой СЕМЬИ источников людей и ИИ поровну и с одинаковым
    распределением длин; ИИ внутри семьи выровнен по генераторам. Семьи смешиваются по весам."""
    rng = np.random.default_rng(seed)
    per_class = n_total // 2
    matched = {}
    for fam, g in pool.groupby("family"):
        h, a = g[g.label == 0], g[g.label == 1]
        if h.empty or a.empty:
            continue
        a = balanced_take(a, min(len(a), len(h) * 2), "generator", rng)      # запас под length_match
        m = length_match(pd.concat([h, a]), rng)
        if len(m):
            matched[fam] = m
    caps = {f: int((m.label == 0).sum()) for f, m in matched.items()}
    alloc = water_fill(per_class, weights, caps)
    parts = [sample_matched(matched[f], alloc[f], rng) for f in matched if alloc[f] > 0]
    df = pd.concat(parts).drop(columns="_bin", errors="ignore")
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


# ───────────────────── диагностика ─────────────────────

def surface_features(code: str) -> dict:
    lines = code.split("\n")
    n = max(len(lines), 1)
    comment = sum(1 for l in lines if l.strip().startswith(("//", "/*", "*", "#")))
    return {
        "len": len(code),
        "lines": n,
        "comment_ratio": comment / n,
        "blank_ratio": sum(1 for l in lines if not l.strip()) / n,
        "avg_line": float(np.mean([len(l) for l in lines])),
        "max_line": max(len(l) for l in lines),
        "indent_avg": float(np.mean([len(l) - len(l.lstrip()) for l in lines if l.strip()] or [0])),
        "has_doc": int("/**" in code),
        "has_import": int(bool(re.search(r"^\s*(import|using)\s", code, re.M))),
        "has_namespace": int("namespace " in code),
        "has_main": int(bool(re.search(r"\bmain\s*\(", code))),
        "has_class": int(bool(re.search(r"\bclass\s+\w+", code))),
        "inline_comment": int(bool(re.search(r"\S\s+//", code))),
        "has_todo": int("TODO" in code),
        "digits_ratio": sum(ch.isdigit() for ch in code) / len(code),
        "upper_ratio": sum(ch.isupper() for ch in code) / len(code),
    }


def diagnostics(train: pd.DataFrame, test: pd.DataFrame, ood: pd.DataFrame) -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    ftr = pd.DataFrame([surface_features(c) for c in train.code])
    fte = pd.DataFrame([surface_features(c) for c in test.code])
    sc = StandardScaler().fit(ftr)
    lr = LogisticRegression(max_iter=2000).fit(sc.transform(ftr), train.label)
    auc_surface = roc_auc_score(test.label, lr.predict_proba(sc.transform(fte))[:, 1])

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, max_features=60000, sublinear_tf=True)
    xtr = vec.fit_transform(train.code)
    lr2 = LogisticRegression(max_iter=1000, C=2.0).fit(xtr, train.label)
    auc_ngram = roc_auc_score(test.label, lr2.predict_proba(vec.transform(test.code))[:, 1])
    # главный тест на шорткаты: качество на НЕВИДЕННЫХ генераторах/источниках. Если AUC здесь сильно
    # ниже, чем на test, модель учила артефакты источника, а не авторство.
    auc_ood = float(roc_auc_score(ood.label, lr2.predict_proba(vec.transform(ood.code))[:, 1])) if len(ood) else float("nan")

    rates = pd.concat([ftr.assign(label=train.label.values)]).groupby("label").mean().T
    rates.columns = ["human", "ai"]
    return {"auc_surface": float(auc_surface), "auc_ngram": float(auc_ngram), "auc_ood": auc_ood, "rates": rates}


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, [df.index.name or ""] + cols)) + " |",
           "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        out.append("| " + " | ".join([str(idx)] + [f"{v:.3f}" if isinstance(v, float) else str(v) for v in row]) + " |")
    return "\n".join(out)


def sample_block(df: pd.DataFrame, label: int, k: int, seed: int) -> str:
    sub = df[df.label == label]
    parts = []
    for _, r in sub.sample(min(k, len(sub)), random_state=seed).iterrows():
        snippet = "\n".join(r.code.split("\n")[:22])
        parts.append(f"*источник: {r.source} / {r.generator}*\n```\n{snippet}\n```")
    return "\n\n".join(parts)


# ───────────────────── языки ─────────────────────

FAMILY = {"local_pairs": "local", "claude_handwritten": "local",
          "kstack": "kt_functions", "rlvr": "kt_functions", "kexercises": "kt_functions"}


def build_language(lang: str, args) -> dict:
    rng = random.Random(SEED)
    tg = TARGETS[lang]
    ood_extra = pd.DataFrame(columns=["code", "label", "source", "generator", "group"])
    licenses = []

    if lang == "java":
        srcs = [load_rosetta("Java", "java"), load_hvai_java(), load_semeval_java(), load_local_java(),
                load_gptsniffer("train")]
        licenses += [("Rosetta Code / H-AIRosettaMP", "MIT (данные Rosetta — GFDL)", "isThisYouLLM/H-AIRosettaMP"),
                     ("HumanVsAICode", "CC-BY-SA-4.0", "OSS-forge/HumanVsAICode"),
                     ("SemEval-2026 Task 13", "Apache-2.0", "DaniilOr/SemEval-2026-Task13"),
                     ("GPTSniffer", "не указана (исследовательский)", "mahirlabibdihan/GPTSniffer"),
                     ("Собственные данные проекта", "—", "javadata.csv, java_ai_generated.csv")]
        weights = {"rosetta": 0.16, "hvai": 0.20, "semeval": 0.18, "codemirage": 0.26,
                   "gptsniffer": 0.10, "local": 0.10}
        ood_extra = load_gptsniffer("test")
        cm_lang = "Java"
    elif lang == "kotlin":
        srcs = [load_rosetta("Kotlin", "kotlin"), load_kstack_functions(rng), load_kexercises(), load_rlvr_kotlin()]
        licenses += [("Rosetta Code / H-AIRosettaMP", "MIT (данные Rosetta — GFDL)", "isThisYouLLM/H-AIRosettaMP"),
                     ("KStack-clean (человек)", "Apache-2.0/MIT/Unlicense/CC0/ISC/BSD — берутся только они", "JetBrains/KStack-clean"),
                     ("KExercises (ИИ, GPT-3.5)", "CC-BY-NC-SA-4.0 (некоммерческая)", "JetBrains/KExercises"),
                     ("rlvr-code-data-Kotlin (ИИ)", "не указана", "saurabh5/rlvr-code-data-Kotlin")]
        weights = {"rosetta": 0.40, "kt_functions": 0.60}
        cm_lang = None
    else:
        srcs = [load_rosetta("C#", "csharp"), load_lcc_csharp()]
        licenses += [("Rosetta Code / H-AIRosettaMP", "MIT (данные Rosetta — GFDL)", "isThisYouLLM/H-AIRosettaMP"),
                     ("LCC_csharp (человек)", "не указана (GitHub, The Stack)", "microsoft/LCC_csharp")]
        weights = {"rosetta": 0.55, "cs_files": 0.45}
        cm_lang = "CSharp"

    if cm_lang and not args.no_codemirage:
        srcs.append(load_codemirage(cm_lang, lang))
        licenses.append(("CodeMirage (человек + 10 LLM)", "CC-BY-NC-ND-4.0 (некоммерческая, без производных!)", "HanxiGuo/CodeMirage"))
    elif cm_lang:
        weights.pop("codemirage", None)

    raw = pd.concat([s for s in srcs if len(s)], ignore_index=True)
    raw["lang"] = lang
    fam = dict(FAMILY)
    if lang == "csharp":
        fam.update({"lcc": "cs_files", "codemirage": "cs_files"})
    raw["family"] = raw.source.map(lambda x: fam.get(x, x))
    n_raw = len(raw)
    pool = dedup_and_conflicts(raw)
    pool["pct"] = pool.group.map(lambda g: stable_pct(lang, g))
    pool["holdout_gen"] = pool.generator.isin(CODEMIRAGE_HOLDOUT)

    # test_ood: невиданные генераторы (и внешний источник) против человека из ТЕХ ЖЕ источников;
    # только группы-задачи из test-части — то есть и задачи, и генераторы не виделись при обучении
    heldout = pool[pool.holdout_gen]
    if lang == "kotlin":
        heldout = pd.concat([heldout, pool[pool.source == "kexercises"]])
    train_pool = pool[~pool.index.isin(heldout.index) & (pool.pct >= TEST_PERCENT)]
    test_pool = pool[~pool.index.isin(heldout.index) & (pool.pct < TEST_PERCENT)]
    ood_ai = heldout[heldout.pct < TEST_PERCENT] if lang != "kotlin" else heldout
    ood_srcs = set(ood_ai.source)
    if lang == "kotlin":
        ood_srcs = {"kstack"}
    ood_h = pool[(pool.label == 0) & (pool.pct < TEST_PERCENT) & pool.source.isin(ood_srcs)]
    ood_pool = pd.concat([ood_ai, ood_h])
    if len(ood_extra):
        e = ood_extra.copy()
        e["family"] = e.source
        e["h"] = e.code.map(code_hash)
        e = e[~e.h.isin(set(train_pool.h))]
        ood_pool = pd.concat([ood_pool, e])

    train = compose(train_pool, tg["train"], weights, SEED)
    test = compose(test_pool, tg["test"], weights, SEED + 1)
    ood = compose(ood_pool, tg["ood"], {f: 1.0 for f in ood_pool.family.unique()}, SEED + 2)
    for name, d in (("train", train), ("test", test), ("test_ood", ood)):
        d[["code", "label"]].to_csv(OUT / f"{lang}_{name}.csv", sep=";", index=False, lineterminator="\r\n")

    diag = diagnostics(train, test, ood)
    composition = {
        n: d.groupby(["source", "label"]).size().unstack(fill_value=0).rename(columns={0: "человек", 1: "ИИ"})
        for n, d in (("train", train), ("test", test), ("test_ood", ood))
    }
    gens = train[train.label == 1].generator.value_counts()
    return dict(lang=lang, raw=n_raw, pool=len(pool), train=train, test=test, ood=ood, diag=diag,
                composition=composition, licenses=licenses, gens=gens)


def write_report(results: list, args) -> None:
    lines = ["# Отчёт по новым датасетам (на утверждение)", "",
             "Файлы лежат в `data/pending/` — **существующие датасеты проекта не тронуты**. "
             "После утверждения их можно подключить к обучению.", "",
             "Метки: `0` — человек, `1` — ИИ. Формат: `code;label`, разделитель `;`, CRLF.", ""]
    for r in results:
        d, lang = r["diag"], r["lang"]
        lines += [f"## {lang.upper()}", "",
                  f"Собрано сырых примеров: {r['raw']:,} → после нормализации/дедупликации/удаления противоречий: {r['pool']:,}.",
                  "", "| набор | строк | человек | ИИ |", "|---|---|---|---|"]
        for name in ("train", "test", "ood"):
            df = r[name]
            lines.append(f"| {lang}_{'test_ood' if name == 'ood' else name}.csv | {len(df)} | "
                         f"{(df.label == 0).sum()} | {(df.label == 1).sum()} |")
        lines += ["", "### Состав по источникам", ""]
        for n, comp in r["composition"].items():
            lines += [f"**{n}**", "", md_table(comp), ""]
        lines += ["### Генераторы ИИ в train", "", ", ".join(f"{k} ({v})" for k, v in r["gens"].items()), "",
                  "### Лицензии источников", "", "| источник | лицензия | где |", "|---|---|---|"]
        lines += [f"| {a} | {b} | `{c}` |" for a, b, c in r["licenses"]]
        lines += ["", "### Диагностика шорткатов",
                  "",
                  f"- AUC простой модели на **поверхностных признаках** (длина, комментарии, отступы…): **{d['auc_surface']:.3f}**",
                  f"- AUC линейной модели на **символьных n-граммах** (test): **{d['auc_ngram']:.3f}**",
                  f"- AUC той же модели на **OOD** (невиданные генераторы/источники): **{d['auc_ood']:.3f}**"
                  " — если близко к test, сигнал настоящий (стиль), а не артефакт источника",
                  "",
                  "Поверхностные признаки не должны выдавать класс почти идеально (ориентир: AUC < 0.80). "
                  "n-граммы — это нижняя граница «сложности» задачи; нейросеть должна заметно её превзойти.",
                  "", md_table(d["rates"]), "",
                  "### Примеры (случайные)", "", "**Человек (0):**", "", sample_block(r["train"], 0, 2, SEED), "",
                  "**ИИ (1):**", "", sample_block(r["train"], 1, 2, SEED), ""]
    (OUT / "DATASET_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["java", "kotlin", "csharp"], action="append")
    ap.add_argument("--no-codemirage", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    results = []
    for lang in (args.lang or ["java", "kotlin", "csharp"]):
        print(f"\n=== {lang} ===", flush=True)
        r = build_language(lang, args)
        print(f"  raw={r['raw']} pool={r['pool']} train={len(r['train'])} test={len(r['test'])} ood={len(r['ood'])}"
              f" | AUC surface={r['diag']['auc_surface']:.3f} ngram={r['diag']['auc_ngram']:.3f} ood={r['diag']['auc_ood']:.3f}", flush=True)
        results.append(r)
    write_report(results, args)
    (OUT / "manifest.json").write_text(json.dumps(
        {r["lang"]: dict(train=len(r["train"]), test=len(r["test"]), ood=len(r["ood"]),
                         auc_surface=r["diag"]["auc_surface"], auc_ngram=r["diag"]["auc_ngram"],
                         auc_ood=r["diag"]["auc_ood"]) for r in results},
        indent=2), encoding="utf-8")
    print("\nГотово →", OUT)


if __name__ == "__main__":
    main()
