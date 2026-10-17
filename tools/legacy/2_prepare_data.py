import random

from datasets import load_dataset
import pandas as pd
from sklearn.model_selection import train_test_split
from pathlib import Path

# Устаревшая Python-ветка проекта: детекторами C++/Java не используется, оставлена для истории
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "legacy"

random.seed(42)
MAX_CHARS = 1000


def clip_at_line_boundary(text, limit):
    if len(text) <= limit:
        return text
    cut = text.rfind("\n", 0, limit)
    return text[:cut] if cut > 0 else text[:limit]


print("Скачиваем AI-код...")
ai_dataset = load_dataset("sahil2801/CodeAlpaca-20k", split="train", streaming=True)

ai_samples = []
for i, sample in enumerate(ai_dataset):
    if len(ai_samples) >= 3000:
        break
    output = sample.get("output", "")
    if len(output) > 50:
        ai_samples.append({"code": clip_at_line_boundary(output, MAX_CHARS), "label": 1})
    if i % 300 == 0:
        print(f"  AI-код: {i}...")
print(f"AI-код готов: {len(ai_samples)} примеров")

print("Скачиваем человеческий код...")
human_dataset = load_dataset("codeparrot/codeparrot-clean-valid", split="train", streaming=True)

human_samples = []
for i, sample in enumerate(human_dataset):
    if len(human_samples) >= 3000:
        break
    code = sample.get("content", "")
    if len(code) > 50:
        # Реальные файлы почти всегда длиннее MAX_CHARS, а AI-примеры обычно короче
        # и заканчиваются "естественно". Если всегда резать по MAX_CHARS, длина текста
        # (~1000 символов, обрыв на середине строки) станет тривиальным признаком класса
        # "человек" вместо стиля кода — поэтому берём случайную длину среза.
        limit = random.randint(50, MAX_CHARS)
        human_samples.append({"code": clip_at_line_boundary(code, limit), "label": 0})
    if i % 300 == 0:
        print(f"  Человеческий код: {i}...")
print(f"Человеческий код готов: {len(human_samples)} примеров")

df = pd.DataFrame(ai_samples + human_samples).drop_duplicates(subset=["code"])
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])

train_df.to_csv(OUT_DIR / "train_data.csv", index=False)
test_df.to_csv(OUT_DIR / "test_data.csv", index=False)

print(f"✅ Готово! Обучение: {len(train_df)}, Тест: {len(test_df)}")
print("Эти данные (Python) детекторами C++/Java не используются")