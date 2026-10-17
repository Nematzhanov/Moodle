# ШАГ 1: Скачиваем готовый датасет с HuggingFace
# Датасет содержит код написанный людьми и ИИ, с метками 0 (человек) и 1 (ИИ)

from datasets import load_dataset
import pandas as pd
from pathlib import Path

# Устаревшая Python-ветка проекта: детекторами C++/Java не используется, оставлена для истории
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "legacy"

print("Скачиваем датасет... (~200 MB, подожди)")

# Это публичный датасет с реальным кодом на C, C++, Java, C#, JS, HTML, CSS
dataset = load_dataset("iamtarun/python_code_instructions_18k_alpaca", split="train")

# Альтернативный датасет специально для детекции AI-кода
# dataset = load_dataset("Hello-SimpleAI/HC3-ChatGPT-Detection", split="train")

print(f"Скачано! Примеров: {len(dataset)}")
print("Пример записи:")
print(dataset[0])

# Сохраняем в CSV файл чтобы посмотреть
df = pd.DataFrame(dataset)
df.to_csv(OUT_DIR / "dataset_raw.csv", index=False)
print("\nСохранено в data/legacy/dataset_raw.csv")
print("Теперь запусти: python tools/legacy/2_prepare_data.py")
