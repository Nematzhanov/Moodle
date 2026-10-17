"""Обучение детекторов ИИ-кода (дообучение microsoft/codebert-base).

Основная платформа — видеокарты NVIDIA (CUDA): смешанная точность (bf16 на Ampere и новее,
fp16 на более старых картах), TF32, крупные батчи, параллельная подготовка батчей.
Без NVIDIA скрипт работает и на Apple Silicon (MPS) или CPU — медленнее.

Запуск из корня проекта:
    python src/train.py                       # C++ и Java, параметры по устройству
    python src/train.py --lang cpp --epochs 4
    python src/train.py --device cuda:1 --batch-size 32
    python src/train.py --lang java --max-train 200 --epochs 1   # быстрая проверка

Данные берутся из data/train/, модели сохраняются в models/<язык>/.
Пути можно переопределить переменными окружения (используется в Docker):
    CODECHECK_ROOT        — корень проекта (по умолчанию папка над src/)
    CODECHECK_DATA_DIR    — где лежат *_train.csv / *_test.csv
    CODECHECK_MODELS_DIR  — куда сохранять модели
"""
import argparse
import gc
import json
import math
import os
import random
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # токенизация идёт в воркерах DataLoader

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          get_linear_schedule_with_warmup)

# ── Пути ───────────────────────────────────────────────────────────────────
ROOT       = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
DATA_DIR   = Path(os.environ.get("CODECHECK_DATA_DIR") or ROOT / "data" / "train")
MODELS_DIR = Path(os.environ.get("CODECHECK_MODELS_DIR") or ROOT / "models")

# ── Настройки ──────────────────────────────────────────────────────────────
MODEL_NAME      = "microsoft/codebert-base"
SAVE_PATH_CPP   = str(MODELS_DIR / "cpp")
SAVE_PATH_JAVA  = str(MODELS_DIR / "java")
# язык → (train, test, test_ood или None, папка модели в models/, название). Kotlin и C#
# появляются после tools/build_datasets.py + tools/apply_datasets.py.
LANGUAGES = {
    "cpp":    ("cpp_train.csv",    "cpp_test.csv",    None,                  "cpp",    "C++"),
    "java":   ("java_train.csv",   "java_test.csv",   "java_test_ood.csv",   "java",   "Java"),
    "kotlin": ("kotlin_train.csv", "kotlin_test.csv", "kotlin_test_ood.csv", "kotlin", "Kotlin"),
    "csharp": ("csharp_train.csv", "csharp_test.csv", "csharp_test_ood.csv", "csharp", "C#"),
}

# Параметры по типу устройства (любой можно переопределить флагами командной строки).
# NVIDIA: батч 16 целиком помещается в память карты от 8 ГБ на 512 токенах в смешанной
# точности. Mac 8 ГБ: GPU и система делят одну память — маленький батч + аккумуляция
# (2 × 3 = 6), иначе система уходит в своп.
DEVICE_DEFAULTS = {
    "cuda": {"batch_size": 16, "grad_accum": 1, "eval_batch_size": 64, "num_workers": 4},
    "mps":  {"batch_size": 2,  "grad_accum": 3, "eval_batch_size": 4,  "num_workers": 0},
    "cpu":  {"batch_size": 8,  "grad_accum": 1, "eval_batch_size": 16, "num_workers": 0},
}

EPOCHS          = 3
MAX_LENGTH      = 512   # codebert-base поддерживает до 512 токенов (max_position_embeddings=514)
LEARNING_RATE   = 2e-5
WARMUP_RATIO    = 0.1   # доля шагов линейного «разогрева» learning rate
MAX_GRAD_NORM   = 1.0
# Эпоха выбирается по валидации, отрезанной от train. Раньше лучшая эпоха выбиралась по
# test, и итоговая «точность на тесте» получалась завышенной: тест участвовал в выборе модели.
VAL_FRACTION    = 0.1
USE_AMP         = True  # смешанная точность на CUDA
LOG_EVERY       = 50
SEED            = 42
# ───────────────────────────────────────────────────────────────────────────


def pick_device(name="auto"):
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def apply_device_defaults(dev):
    global BATCH_SIZE, GRAD_ACCUM, EVAL_BATCH_SIZE, NUM_WORKERS
    d = DEVICE_DEFAULTS[dev.type]
    BATCH_SIZE, GRAD_ACCUM = d["batch_size"], d["grad_accum"]
    EVAL_BATCH_SIZE, NUM_WORKERS = d["eval_batch_size"], d["num_workers"]


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)  # сидирует и все CUDA-устройства


def setup_cuda():
    # TF32 на Ampere+ ускоряет матричные операции в fp32-части вычислений без заметной потери точности
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


device = pick_device(os.environ.get("CODECHECK_DEVICE", "auto"))
apply_device_defaults(device)
set_seed(SEED)


def free_device_memory():
    """Возвращает системе память, которую CUDA/MPS держит в кэше."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif torch.backends.mps.is_available():
        torch.mps.empty_cache()


def amp_dtype_for(dev):
    """bf16 — если карта поддерживает (Ampere и новее), иначе fp16; вне CUDA — без AMP."""
    if dev.type != "cuda" or not USE_AMP:
        return None
    return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16


# Функция для правильного чтения CSV (запятая или точка с запятой)
def read_csv_auto(path):
    try:
        df = pd.read_csv(path, sep=",")
        if df.shape[1] < 2:
            df = pd.read_csv(path, sep=";")
    except Exception:
        df = pd.read_csv(path, sep=";")
    df.columns = [c.replace("﻿", "") for c in df.columns]
    if "lable" in df.columns:
        df = df.rename(columns={"lable": "label"})
    df = df.dropna(subset=["code", "label"])
    df["code"]  = df["code"].astype(str)
    df["label"] = df["label"].astype(int)
    # убираем дубли текста, иначе одна и та же строка кода может оказаться
    # и в train, и в test после разбиения
    df = df.drop_duplicates(subset=["code"]).reset_index(drop=True)
    # group — номер пары «оригинал / ИИ-вариант» (пишется tools/regenerate_cpp_split.py);
    # по нему валидация отрезается так, чтобы пара не разрывалась
    if "group" in df.columns:
        df["group"] = df["group"].astype(str)
        return df[["code", "label", "group"]]
    return df[["code", "label"]]


# data/train/cpp_*.csv генерируются из data/sources/cppdata.csv скриптом tools/regenerate_cpp_split.py
# (group-aware split: пара «оригинал/ИИ-вариант» целиком на одной стороне),
# data/train/java_*.csv — скриптом tools/regenerate_java_split.py.
# Загрузка датасетов и запуск обучения вынесены в main(), чтобы функции этого модуля можно
# было импортировать (retrain_java.py и др.) без запуска всего обучения.


# ── КЛАСС ДАТАСЕТА ─────────────────────────────────────────────────────────
class CodeDataset(torch.utils.data.Dataset):
    """Токенизирует весь датасет один раз при создании (а не каждую эпоху)
    и НЕ паддит примеры заранее: паддинг делается динамически в collate —
    только до самого длинного примера в батче."""

    def __init__(self, dataframe, tokenizer, max_length):
        self.encodings = tokenizer(
            dataframe["code"].tolist(),
            max_length=max_length,
            truncation=True,
        )
        self.labels = dataframe["label"].tolist()

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids":      self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "label":          self.labels[idx],
        }


class PadCollator:
    """Собирает батч, паддя до длины самого длинного примера в нём.
    Класс, а не замыкание, — чтобы его можно было передать в процессы-воркеры DataLoader."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, batch):
        features = [{"input_ids": b["input_ids"], "attention_mask": b["attention_mask"]} for b in batch]
        padded = self.tokenizer.pad(features, return_tensors="pt")
        padded["label"] = torch.tensor([b["label"] for b in batch], dtype=torch.long)
        return padded


def make_loader(dataset, collate_fn, batch_size, shuffle):
    workers = NUM_WORKERS
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, collate_fn=collate_fn,
                      num_workers=workers, persistent_workers=workers > 0,
                      pin_memory=device.type == "cuda")


# ── ФУНКЦИЯ ОЦЕНКИ ─────────────────────────────────────────────────────────
def evaluate(model, loader, device, loss_fn=None):
    """Возвращает (предсказания, истинные метки, средний loss или None)."""
    model.eval()
    amp_dtype = amp_dtype_for(device)
    all_preds, all_labels = [], []
    loss_sum, n = 0.0, 0
    with torch.inference_mode(), torch.autocast(device_type=device.type, dtype=amp_dtype,
                                                enabled=amp_dtype is not None):
        for batch in loader:
            input_ids      = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            logits         = model(input_ids=input_ids, attention_mask=attention_mask).logits
            if loss_fn is not None:
                labels    = batch["label"].to(device, non_blocking=True)
                loss_sum += loss_fn(logits.float(), labels).item() * len(labels)
                n        += len(labels)
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(batch["label"].numpy())  # метки не гоняем на GPU
    return all_preds, all_labels, (loss_sum / n if n else None)


def class_weights(labels):
    """Веса классов обратно пропорционально частоте: n / (2 · n_класса).
    Без них на перекошенном train (например, C++: 935 «человек» / 408 «ИИ») модель
    смещается к большему классу."""
    counts = np.bincount(np.asarray(labels), minlength=2).astype(float)
    counts[counts == 0] = 1.0
    return torch.tensor(counts.sum() / (2 * counts), dtype=torch.float)


# ── ФУНКЦИЯ ОБУЧЕНИЯ ───────────────────────────────────────────────────────
def train_model(train_df, test_df, save_path, label, ood_df=None):
    print(f"\n{'=' * 50}")
    print(f"  ОБУЧЕНИЕ МОДЕЛИ: {label}")
    print(f"{'=' * 50}")

    # Валидация отрезается от train. Если в данных есть колонка group (пары «оригинал /
    # ИИ-вариант» одного файла), пара целиком уходит либо в обучение, либо в валидацию —
    # иначе модель видела бы на валидации почти копию обучающего примера.
    if "group" in train_df.columns:
        splitter = GroupShuffleSplit(n_splits=1, test_size=VAL_FRACTION, random_state=SEED)
        fit_idx, val_idx = next(splitter.split(train_df, groups=train_df["group"]))
        fit_df, val_df = train_df.iloc[fit_idx], train_df.iloc[val_idx]
    else:
        fit_df, val_df = train_test_split(train_df, test_size=VAL_FRACTION, random_state=SEED,
                                          stratify=train_df["label"])

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model     = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
    model     = model.to(device)

    collate_fn   = PadCollator(tokenizer)
    train_loader = make_loader(CodeDataset(fit_df,  tokenizer, MAX_LENGTH), collate_fn, BATCH_SIZE, True)
    val_loader   = make_loader(CodeDataset(val_df,  tokenizer, MAX_LENGTH), collate_fn, EVAL_BATCH_SIZE, False)
    test_loader  = make_loader(CodeDataset(test_df, tokenizer, MAX_LENGTH), collate_fn, EVAL_BATCH_SIZE, False)

    weights = class_weights(fit_df["label"])
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights.to(device))

    optimizer    = AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
    update_steps = math.ceil(len(train_loader) / GRAD_ACCUM) * EPOCHS
    scheduler    = get_linear_schedule_with_warmup(optimizer, int(WARMUP_RATIO * update_steps), update_steps)

    amp_dtype = amp_dtype_for(device)
    # GradScaler нужен только для fp16: у bf16 тот же диапазон чисел, что у fp32
    scaler = torch.amp.GradScaler("cuda") if amp_dtype == torch.float16 else None

    amp_name = {torch.bfloat16: "bf16", torch.float16: "fp16"}.get(amp_dtype, "выкл")
    gpu_name = f" ({torch.cuda.get_device_name(device)})" if device.type == "cuda" else ""
    print(f"  Устройство: {device}{gpu_name}, смешанная точность: {amp_name}")
    print(f"  train {len(fit_df)} / val {len(val_df)} / test {len(test_df)}; "
          f"веса классов: человек {weights[0]:.2f}, ИИ {weights[1]:.2f}")
    print(f"\nНачинаем обучение ({EPOCHS} эпохи, "
          f"батч {BATCH_SIZE} × аккумуляция {GRAD_ACCUM} = эффективный {BATCH_SIZE * GRAD_ACCUM})...\n")

    best_score = None   # (macro-F1, −loss) на валидации: F1 не поощряет больший класс,
    best_val   = 0.0    # loss разбивает ничьи, частые на маленькой валидации
    best_epoch = 0
    best_state = None
    n_steps    = len(train_loader)

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        optimizer.zero_grad(set_to_none=True)

        for step, batch in enumerate(train_loader):
            input_ids      = batch["input_ids"].to(device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(device, non_blocking=True)
            labels         = batch["label"].to(device, non_blocking=True)

            with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=amp_dtype is not None):
                logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            # loss считаем в fp32 — так стабильнее при fp16/bf16
            batch_loss = loss_fn(logits.float(), labels)
            # делим loss на число батчей в окне аккумуляции, чтобы суммарный градиент
            # соответствовал среднему по эффективному батчу; последнее окно эпохи бывает неполным
            window_start = step - step % GRAD_ACCUM
            loss = batch_loss / min(GRAD_ACCUM, n_steps - window_start)
            if scaler is not None:
                scaler.scale(loss).backward()
            else:
                loss.backward()

            # обновляем веса раз в GRAD_ACCUM шагов (и на последнем неполном)
            if (step + 1) % GRAD_ACCUM == 0 or (step + 1) == len(train_loader):
                if scaler is not None:
                    scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                if scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            total_loss += batch_loss.item()

            if step % LOG_EVERY == 0:
                print(f"  Эпоха {epoch+1}/{EPOCHS} | Шаг {step}/{len(train_loader)} | "
                      f"Loss: {batch_loss.item():.4f} | LR: {scheduler.get_last_lr()[0]:.2e}")

        preds, labels_true, val_loss = evaluate(model, val_loader, device, loss_fn)
        val_acc = accuracy_score(labels_true, preds)
        val_f1  = f1_score(labels_true, preds, average="macro")
        print(f"\n✅ Эпоха {epoch+1} | Loss: {total_loss/len(train_loader):.4f} | Валидация: "
              f"точность {val_acc*100:.1f}%, macro-F1 {val_f1:.3f}, loss {val_loss:.4f}\n")

        # запоминаем веса лучшей по валидации эпохи; копию держим на CPU, чтобы не занимать память GPU
        score = (val_f1, -val_loss)
        if best_score is None or score > best_score:
            best_score, best_val, best_epoch = score, val_acc, epoch + 1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

        free_device_memory()

    if best_state is not None:
        model.load_state_dict(best_state)

    # Тест смотрим один раз — уже после выбора эпохи, поэтому оценка честная
    preds, labels_true, _ = evaluate(model, test_loader, device)
    test_acc = accuracy_score(labels_true, preds)
    print(f"\n─── Финальный отчёт [{label}] (эпоха {best_epoch}, валидация {best_val*100:.1f}%, "
          f"тест {test_acc*100:.1f}%) ───")
    print(classification_report(labels_true, preds, target_names=["Человек", "ИИ"], digits=3))
    metrics = {"language": label, "base_model": MODEL_NAME, "best_epoch": best_epoch,
               "val_accuracy": round(best_val, 4), "val_macro_f1": round(best_score[0], 4),
               "test_accuracy": round(test_acc, 4),
               "test_macro_f1": round(f1_score(labels_true, preds, average="macro"), 4),
               "train_size": len(fit_df), "val_size": len(val_df), "test_size": len(test_df),
               "max_length": MAX_LENGTH, "device": str(device), "amp": amp_name}

    # OOD: невиданные генераторы/источники — самая правдоподобная оценка качества «в бою»
    if ood_df is not None and len(ood_df):
        ood_loader = make_loader(CodeDataset(ood_df, tokenizer, MAX_LENGTH), collate_fn, EVAL_BATCH_SIZE, False)
        o_preds, o_true, _ = evaluate(model, ood_loader, device)
        ood_acc = accuracy_score(o_true, o_preds)
        print(f"\n─── OOD-тест [{label}] (невиданные генераторы/источники, {len(ood_df)} примеров) ───")
        print(f"Точность: {ood_acc*100:.1f}%")
        print(classification_report(o_true, o_preds, target_names=["Человек", "ИИ"], digits=3))
        metrics.update(ood_accuracy=round(ood_acc, 4), ood_size=len(ood_df))
        del ood_loader

    # Сохраняем
    print(f"Сохраняем модель в '{save_path}'...")
    os.makedirs(save_path, exist_ok=True)
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    with open(os.path.join(save_path, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"✅ Модель [{label}] сохранена в '{save_path}'!\n")

    # освобождаем память перед следующей моделью
    del model, optimizer, scheduler, best_state, train_loader, val_loader, test_loader
    free_device_memory()
    return metrics


# ── ЗАПУСКАЕМ ОБУЧЕНИЕ ─────────────────────────────────────────────────────
def main():
    global EPOCHS, MAX_LENGTH, LEARNING_RATE, USE_AMP, device
    global BATCH_SIZE, GRAD_ACCUM, EVAL_BATCH_SIZE, NUM_WORKERS
    ap = argparse.ArgumentParser(description="Обучение детекторов ИИ-кода")
    ap.add_argument("--lang", action="append", choices=list(LANGUAGES),
                    help="какие языки обучать (по умолчанию: cpp и java; можно несколько раз)")
    ap.add_argument("--device", default=os.environ.get("CODECHECK_DEVICE", "auto"),
                    help="auto (CUDA → MPS → CPU), cuda, cuda:1, mps, cpu")
    ap.add_argument("--epochs", type=int, help=f"число эпох (по умолчанию {EPOCHS})")
    ap.add_argument("--batch-size", type=int, help="батч на шаг (по умолчанию зависит от устройства)")
    ap.add_argument("--grad-accum", type=int, help="шагов аккумуляции градиента")
    ap.add_argument("--eval-batch-size", type=int)
    ap.add_argument("--workers", type=int, help="процессов подготовки батчей DataLoader")
    ap.add_argument("--lr", type=float, help=f"learning rate (по умолчанию {LEARNING_RATE})")
    ap.add_argument("--max-length", type=int, help=f"длина в токенах, ≤ 512 (по умолчанию {MAX_LENGTH})")
    ap.add_argument("--no-amp", action="store_true", help="отключить смешанную точность на CUDA")
    ap.add_argument("--max-train", type=int,
                    help="ограничить размер train (быстрая пробная обучалка), сбалансировано по классам")
    args = ap.parse_args()

    device = pick_device(args.device)
    apply_device_defaults(device)
    if device.type == "cuda":
        setup_cuda()
    EPOCHS          = args.epochs or EPOCHS
    BATCH_SIZE      = args.batch_size or BATCH_SIZE
    GRAD_ACCUM      = args.grad_accum or GRAD_ACCUM
    EVAL_BATCH_SIZE = args.eval_batch_size or EVAL_BATCH_SIZE
    NUM_WORKERS     = NUM_WORKERS if args.workers is None else args.workers
    LEARNING_RATE   = args.lr or LEARNING_RATE
    MAX_LENGTH      = min(args.max_length or MAX_LENGTH, 512)
    USE_AMP         = not args.no_amp
    print(f"\nУстройство: {device}")

    langs = args.lang or ["cpp", "java"]
    results = {}
    for key in langs:
        train_f, test_f, ood_f, model_dir, label = LANGUAGES[key]
        train_f, test_f = DATA_DIR / train_f, DATA_DIR / test_f
        ood_f = DATA_DIR / ood_f if ood_f else None
        print("=" * 50)
        print(f"  ЗАГРУЗКА ДАННЫХ {label}")
        print("=" * 50)
        train_df = read_csv_auto(train_f)
        test_df  = read_csv_auto(test_f)
        ood_df   = read_csv_auto(ood_f) if ood_f and ood_f.exists() else None
        if args.max_train and len(train_df) > args.max_train:
            half = args.max_train // 2
            train_df = pd.concat([g.sample(min(half, len(g)), random_state=SEED) for _, g in train_df.groupby("label")])
            train_df = train_df.sample(frac=1, random_state=SEED).reset_index(drop=True)
        print(f"  {label} обучение: {len(train_df)} примеров, {dict(train_df['label'].value_counts())}")
        print(f"  {label} тест:     {len(test_df)} примеров, {dict(test_df['label'].value_counts())}")
        if ood_df is not None:
            print(f"  {label} OOD-тест: {len(ood_df)} примеров, {dict(ood_df['label'].value_counts())}")
        results[label] = train_model(train_df, test_df, str(MODELS_DIR / model_dir), label, ood_df)

    print("\n" + "=" * 50)
    print("  ВСЁ ГОТОВО!")
    for key in langs:
        label = LANGUAGES[key][4]
        m = results[label]
        ood = f", OOD {m['ood_accuracy']*100:.1f}%" if "ood_accuracy" in m else ""
        print(f"  {label}: тест {m['test_accuracy']*100:.1f}%{ood} → {MODELS_DIR / LANGUAGES[key][3]}/")
    print("=" * 50)


if __name__ == "__main__":
    main()
