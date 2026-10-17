# Запуск в Docker на видеокарте NVIDIA

В проекте два образа:

| образ | что внутри | зачем |
|---|---|---|
| `codecheck-web:cuda` (`web.Dockerfile`) | сайт, сервер проверки и обученная модель C++ | готовый сервис: открыл в браузере — проверяешь код |
| `codecheck:cuda` (`Dockerfile`) | обучение (`src/train.py`), консольная проверка, скрипты данных | переобучение моделей |

## 1. Что нужно на компьютере

- Видеокарта NVIDIA и драйвер версии **525.60 или новее**. Проверка: `nvidia-smi` должна показать карту.
- Docker с Compose v2 (Docker Desktop или Docker Engine 23+).
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), он даёт контейнерам доступ к видеокарте:
  - **Linux:** установить пакет `nvidia-container-toolkit` по ссылке выше, затем выполнить:
    ```bash
    sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
    ```
  - **Windows:** Docker Desktop с WSL 2 и свежий драйвер NVIDIA для Windows. Поддержка GPU уже встроена, ставить Toolkit отдельно не нужно.
- На Mac видеокарты NVIDIA нет. Там запускайте без Docker: `.venv/bin/python src/server.py`, модель сама выберет видеокарту Apple.

Проверка, что Docker видит видеокарту:

```bash
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

Если появилась таблица с вашей картой, всё готово.

## 2. Сайт с моделью C++

Модель (`models/cpp`, около 480 МБ) вшивается в образ при сборке. Контейнер работает сам по себе, папка проекта ему не нужна.

### Запуск

Из корня проекта:

```bash
docker compose up -d --build
```

Первая сборка занимает 5–15 минут: скачивается PyTorch с библиотеками CUDA, образ весит около 6–7 ГБ. Потом откройте в браузере:

```
http://localhost:8000
```

Внизу страницы должно быть написано **«Модель C++ подключена · cuda»**. Если там `cpu`, контейнер не получил видеокарту, см. раздел «Если что-то не работает».

### Управление

```bash
docker compose logs -f web     # журнал сервера
```
```bash
docker compose ps              # статус; healthy — сервер отвечает
```
```bash
docker compose down            # остановить
```

Контейнер перезапускается сам после перезагрузки компьютера (`restart: unless-stopped`).

### Обновить модель или сайт

После переобучения модели или правок сайта пересоберите образ:

```bash
docker compose up -d --build web
```

Модель лежит в отдельном слое образа. При правке только сайта она не пересобирается, и сборка проходит быстро.

### Проверка через API

```bash
curl http://localhost:8000/api/health
```
```bash
curl -X POST http://localhost:8000/api/detect -H "Content-Type: application/json" -d '{"code": "#include <iostream>\nint main() { std::cout << 42; }"}'
```

Ответ: `ai_pct` — вероятность ИИ в процентах, `fragments` — оценки по фрагментам с номерами строк, `seconds` — время проверки.

### Другой порт или доступ из сети

Порт меняется в `docker-compose.yml`, строка `"8000:8000"`. Например, `"80:8000"` откроет сайт на обычном адресе `http://<ip-компьютера>/`. Контейнер слушает все сетевые интерфейсы, поэтому сайт сразу доступен с других устройств в сети.

### Запуск без Compose

```bash
docker build -f web.Dockerfile -t codecheck-web:cuda .
```
```bash
docker run -d --gpus all -p 8000:8000 --name codecheck codecheck-web:cuda
```

## 3. Обучение моделей

Образ обучения подключает папку проекта как `/workspace`, поэтому обученные модели сразу оказываются в `models/` на компьютере.

```bash
docker compose --profile tools build
```
```bash
docker compose run --rm train --lang cpp
```
```bash
docker compose run --rm train --lang cpp --epochs 4 --batch-size 32
```

Модель сохраняется в `models/cpp/` вместе с `metrics.json`. **Старая модель перезаписывается**, поэтому сделайте копию папки заранее. Параметры на NVIDIA по умолчанию: батч 16, смешанная точность (bf16 на RTX 30xx/40xx/A100 и новее, fp16 на старых картах). Все флаги: `docker compose run --rm train --help`.

При первом запуске скачивается базовая модель `microsoft/codebert-base` (около 500 МБ), она кэшируется в томе `hf-cache`. Файлы создаются от пользователя с UID 1000. Если у вас другой (`id -u`), запускайте так:

```bash
LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose run --rm train --lang cpp
```

Обученную модель затем можно вшить в сайт: `docker compose up -d --build web`.

Другие скрипты из образа обучения:

```bash
docker compose run --rm --entrypoint python train /app/tools/check_datasets.py
```
```bash
docker compose run --rm detect --lang cpp --file /workspace/solution.cpp
```

## 4. Если что-то не работает

| симптом | причина и решение |
|---|---|
| `could not select device driver "nvidia"` | не установлен NVIDIA Container Toolkit или Docker не перезапущен после установки (раздел 1) |
| внизу сайта `· cpu` вместо `· cuda` | контейнер запущен без видеокарты: используйте `docker compose up`, а не `docker run` без `--gpus all` |
| `CUDA driver version is insufficient` | драйвер старше 525.60, обновите драйвер NVIDIA |
| очень новая карта (RTX 50xx) не работает | соберите образ под CUDA 13: `docker compose build --build-arg TORCH_CUDA=cu130 web` |
| порт 8000 занят | поменяйте левую часть в `"8000:8000"`, например `"8080:8000"` |
| нужно запустить без видеокарты | удалите блок `<<: *gpu` у сервиса `web`, и модель будет работать на CPU (около 1–3 с на файл) |
