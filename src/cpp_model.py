"""Модель C++ для проверки кода: загрузка и анализ с разбиением длинного кода на фрагменты.

Используется терминальным приложением (cpp_checker.py) и веб-сервером (server.py),
чтобы оба давали одинаковый результат.
"""
import os
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
import torch.nn.functional as F

ROOT       = Path(os.environ.get("CODECHECK_ROOT") or Path(__file__).resolve().parents[1])
MODEL_PATH = Path(os.environ.get("CODECHECK_MODELS_DIR") or ROOT / "models") / "cpp"

MAX_LENGTH  = 512              # как в train.py
WINDOW      = MAX_LENGTH - 2   # минус служебные токены <s> и </s>
STRIDE      = 256              # шаг окна: соседние фрагменты перекрываются наполовину
CHUNK_BATCH = 8


def pick_device(name):
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class CppDetector:
    """Модель C++ и разбиение длинного кода на фрагменты по 512 токенов."""

    def __init__(self, model_path, device):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        from transformers.utils import logging as hf_logging
        # полосы прогресса и предупреждения transformers пишут в терминал поверх интерфейса,
        # а под Textual полоса «Loading weights» вообще падает — отключаем их
        hf_logging.disable_progress_bar()
        hf_logging.set_verbosity_error()
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path).to(device).eval()

    def analyze(self, code):
        enc = self.tokenizer(code, add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = enc["input_ids"], enc["offset_mapping"]
        if not ids:
            raise ValueError("В коде нет токенов")

        starts = list(range(0, max(len(ids) - WINDOW, 0) + 1, STRIDE))
        if starts[-1] + WINDOW < len(ids):
            starts.append(len(ids) - WINDOW)   # последний фрагмент добирает хвост файла

        tok = self.tokenizer
        chunks = [[tok.cls_token_id] + ids[s:s + WINDOW] + [tok.sep_token_id] for s in starts]
        probs = []
        with torch.inference_mode():
            for i in range(0, len(chunks), CHUNK_BATCH):
                batch = tok.pad({"input_ids": chunks[i:i + CHUNK_BATCH]}, return_tensors="pt")
                batch = {k: v.to(self.device) for k, v in batch.items()}
                logits = self.model(**batch).logits.float()
                probs += F.softmax(logits, dim=1)[:, 1].cpu().tolist()

        fragments = []
        for s, p in zip(starts, probs):
            first_char = offsets[s][0]
            last_char = offsets[min(s + WINDOW, len(ids)) - 1][1]
            fragments.append({
                "lines": (code.count("\n", 0, first_char) + 1, code.count("\n", 0, last_char) + 1),
                "ai_pct": round(p * 100, 1),
            })
        ai_pct = round(sum(probs) / len(probs) * 100, 1)
        return {"ai_pct": ai_pct, "human_pct": round(100 - ai_pct, 1),
                "tokens": len(ids), "fragments": fragments}
