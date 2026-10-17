# Сайт CodeCheck с обученной моделью C++ внутри — работает на видеокартах NVIDIA.
# CUDA-библиотеки приходят вместе с колесом PyTorch; на хосте нужны только драйвер NVIDIA
# (525.60 или новее) и NVIDIA Container Toolkit. Без видеокарты образ работает на CPU.
#
#   docker compose up -d --build        → http://localhost:8000
# Подробно — docs/DOCKER.md, раздел «Сайт с моделью C++».
FROM python:3.12-slim

ARG TORCH_VERSION=2.13.0
ARG TORCH_CUDA=cu126

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HUB_OFFLINE=1 \
    HOME=/tmp

RUN pip install "torch==${TORCH_VERSION}" --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}"
COPY requirements-web.txt /app/requirements-web.txt
RUN pip install -r /app/requirements-web.txt

# модель (~480 МБ) копируется отдельным слоем: при правке сайта или кода её слой не пересобирается
COPY models/cpp/ /app/models/cpp/
COPY website/ /app/website/
COPY src/server.py src/cpp_model.py /app/src/

# файлы модели в проекте доступны только владельцу — открываем на чтение, сервер работает не от root
RUN chmod -R a+rX /app && useradd --system --no-create-home codecheck
USER codecheck

WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
ENTRYPOINT ["python", "/app/src/server.py", "--host", "0.0.0.0", "--port", "8000"]
