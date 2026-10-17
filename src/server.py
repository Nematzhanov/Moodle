"""Веб-сервер CodeCheck: отдаёт сайт из website/ и проверяет код C++ моделью models/cpp.

    .venv/bin/python src/server.py                       # http://127.0.0.1:8000
    .venv/bin/python src/server.py --port 8080 --device cpu

API:
    POST /api/detect   {"code": "..."}  →  {"ai_pct", "human_pct", "tokens", "fragments", "seconds"}
    GET  /api/health                    →  {"ok": true, "model": "...", "device": "..."}

Без зависимостей сверх проекта: стандартный http.server, модель — общий модуль cpp_model.py.
"""
import argparse
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from cpp_model import MODEL_PATH, ROOT, CppDetector, pick_device

WEBSITE_DIR = ROOT / "website"
MAX_BODY    = 512 * 1024   # 512 КБ кода на запрос — с большим запасом для учебной работы


class Handler(SimpleHTTPRequestHandler):
    detector = None
    device = None
    lock = threading.Lock()   # модель на GPU обслуживает запросы по одному

    def do_GET(self):
        if self.path == "/api/health":
            return self.reply(200, {"ok": True, "model": str(MODEL_PATH.name), "device": str(self.device)})
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/detect":
            return self.reply(404, {"error": "Неизвестный адрес"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return self.reply(400, {"error": "Пустой запрос"})
        if length > MAX_BODY:
            return self.reply(413, {"error": "Код слишком большой (больше 512 КБ)"})
        try:
            code = str(json.loads(self.rfile.read(length)).get("code", "")).strip()
        except (ValueError, AttributeError):
            return self.reply(400, {"error": "Некорректный JSON"})
        if len(code) < 10:
            return self.reply(400, {"error": "Вставьте код — хотя бы несколько строк"})

        started = time.monotonic()
        try:
            with self.lock:
                result = self.detector.analyze(code)
        except Exception as error:
            return self.reply(500, {"error": f"Ошибка проверки: {error}"})
        result["seconds"] = round(time.monotonic() - started, 2)
        result["language"] = "C++"
        return self.reply(200, result)

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser(description="Сайт CodeCheck с проверкой кода C++")
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 — открыть доступ из локальной сети")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--device", default="auto", help="auto (CUDA → MPS → CPU), cpu, mps, cuda")
    ap.add_argument("--model", default=str(MODEL_PATH), help=f"папка модели (по умолчанию {MODEL_PATH})")
    args = ap.parse_args()

    device = pick_device(args.device)
    print(f"Загрузка модели {args.model} на {device}…", flush=True)
    Handler.detector = CppDetector(args.model, device)
    Handler.device = device

    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(WEBSITE_DIR)))
    print(f"CodeCheck: http://{args.host}:{args.port}  (Ctrl+C — остановить)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
