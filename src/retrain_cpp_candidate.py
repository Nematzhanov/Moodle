"""Переобучает C++-модель на data/train/cpp_train.csv и cpp_test.csv
(с добавленными человеческими решениями из CodeContests, см. README.md,
раздел «Ограничения») и сохраняет результат в models/cpp_candidate/ — НЕ перезаписывая
рабочую модель models/cpp/, пока результат не подтверждён.

Запуск из корня проекта:  .venv/bin/python src/retrain_cpp_candidate.py
"""
import train as tm  # src/train.py: папка скрипта при запуске попадает в sys.path

CANDIDATE_PATH = str(tm.MODELS_DIR / "cpp_candidate")

train_cpp = tm.read_csv_auto(tm.DATA_DIR / "cpp_train.csv")
test_cpp  = tm.read_csv_auto(tm.DATA_DIR / "cpp_test.csv")

print("=" * 50)
print("  ПЕРЕОБУЧЕНИЕ C++ (кандидат, в отдельную папку)")
print("=" * 50)
print(f"  C++ обучение: {len(train_cpp)} примеров, {dict(train_cpp['label'].value_counts())}")
print(f"  C++ тест:     {len(test_cpp)} примеров, {dict(test_cpp['label'].value_counts())}")

tm.train_model(train_cpp, test_cpp, CANDIDATE_PATH, "C++ (candidate)")

print(f"\n✅ Кандидат сохранён в {CANDIDATE_PATH} — рабочая модель models/cpp/ не тронута.")
