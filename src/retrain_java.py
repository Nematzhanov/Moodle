"""Переобучает ТОЛЬКО Java-модель на data/train/java_train.csv и java_test.csv.

C++-модель не трогает (экономит время). Данные Java должны быть предварительно
пересобраны из data/sources/javadata.csv скриптом tools/regenerate_java_split.py.

Запуск из корня проекта:  .venv/bin/python src/retrain_java.py
"""
import train as tm  # src/train.py: папка скрипта при запуске попадает в sys.path

tm.EPOCHS = 3  # train ~2400 строк — 3 эпох достаточно, на диск сохраняется лучшая по валидации

train_java = tm.read_csv_auto(tm.DATA_DIR / "java_train.csv")
test_java  = tm.read_csv_auto(tm.DATA_DIR / "java_test.csv")

print("=" * 50)
print("  ПЕРЕОБУЧЕНИЕ JAVA")
print("=" * 50)
print(f"  Java обучение: {len(train_java)} примеров, {dict(train_java['label'].value_counts())}")
print(f"  Java тест:     {len(test_java)} примеров, {dict(test_java['label'].value_counts())}")

tm.train_model(train_java, test_java, tm.SAVE_PATH_JAVA, "Java")

print("\n✅ Java-модель переобучена и сохранена в", tm.SAVE_PATH_JAVA)
