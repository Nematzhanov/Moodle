# Образ для обучения детекторов и консольной проверки кода на видеокартах NVIDIA.
# CUDA-библиотеки приходят вместе с колесом PyTorch; на хосте нужны только драйвер NVIDIA
# и NVIDIA Container Toolkit. Код и модели в образ не копируются — папка проекта
# монтируется в /workspace (см. docker-compose.yml).
FROM python:3.12-slim

# cu126 работает с драйверами NVIDIA от 525.60 и выше; для свежих карт можно собрать
# с --build-arg TORCH_CUDA=cu130
ARG TORCH_VERSION=2.13.0
ARG TORCH_CUDA=cu126

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/cache/huggingface \
    HOME=/tmp \
    CODECHECK_ROOT=/workspace

RUN pip install "torch==${TORCH_VERSION}" --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}"

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# кэш базовой модели codebert-base и рабочая папка доступны на запись любому
# пользователю — контейнер запускается с UID хоста, чтобы модели не принадлежали root
RUN mkdir -p /cache/huggingface /workspace && chmod -R 777 /cache /workspace

COPY src/ /app/src/
COPY tools/ /app/tools/

WORKDIR /workspace
ENTRYPOINT ["python", "/app/src/train.py"]
