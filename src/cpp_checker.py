"""Терминальное приложение для проверки кода C++ на ИИ-авторство.

    .venv/bin/python src/cpp_checker.py                 # пустой редактор
    .venv/bin/python src/cpp_checker.py solution.cpp    # открыть файл
    .venv/bin/python src/cpp_checker.py --device cpu    # не занимать видеокарту

Вставьте код и нажмите Enter дважды подряд (или F5) — запустится проверка.
Клавиши: F5 / Ctrl+R — проверить, Ctrl+O — открыть файл, Ctrl+L — очистить, Ctrl+Q — выход.

Длинный код проверяется целиком: модель видит 512 токенов за раз, поэтому код режется
на перекрывающиеся фрагменты, и итог — средняя вероятность по фрагментам.
"""
import argparse
import os
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Digits, Footer, Header, Input, Label, Static, TextArea

from cpp_model import MODEL_PATH, CppDetector, pick_device

SHORT_TOKENS     = 40    # короче — оценка ненадёжна (модель путает короткий аккуратный код с ИИ)
DOUBLE_ENTER_SEC = 0.45  # два Enter быстрее этого интервала — запуск проверки
BAR_WIDTH        = 30
TOP_FRAGMENTS    = 5     # сколько самых «ИИ-шных» фрагментов длинного файла показывать


def verdict_for(ai_pct):
    """Те же пороги, что в detect.py; второй элемент — класс оформления."""
    if ai_pct >= 80:
        return "Почти точно написан ИИ", "danger"
    if ai_pct >= 60:
        return "Скорее всего написан ИИ", "danger"
    if ai_pct >= 40:
        return "Сложно определить", "warn"
    if ai_pct >= 20:
        return "Скорее всего написан человеком", "ok"
    return "Почти точно написан человеком", "ok"


def language_warning(code):
    """Грубая эвристика: модель обучена только на C++, о другом языке предупреждаем."""
    cpp_marks = ("#include", "std::", "cout", "cin", "int main", "nullptr", "template<", "template <")
    if any(m in code for m in cpp_marks):
        return None
    if "System.out" in code or "public static void main" in code:
        return "Похоже на Java — модель обучена только на C++, результат ненадёжен."
    if "def " in code and ":" in code and "{" not in code:
        return "Похоже на Python — модель обучена только на C++, результат ненадёжен."
    return None


def first_code_line(code):
    """Первая строка с кодом (без комментариев и #include) — подпись в истории проверок."""
    for line in code.splitlines():
        line = line.strip()
        if line and not line.startswith(("//", "/*", "*", "#")):
            return line[:40]
    return code.strip().splitlines()[0][:40] if code.strip() else ""


class CppEditor(TextArea):
    """Редактор с подсветкой C++; два Enter подряд запускают проверку."""

    class CheckRequested(Message):
        pass

    def __init__(self, **kwargs):
        super().__init__(theme="monokai", soft_wrap=False, tab_behavior="indent",
                         show_line_numbers=True,
                         placeholder="Вставьте код C++ и нажмите Enter дважды (или F5)", **kwargs)
        self._last_enter = 0.0

    def on_mount(self):
        try:
            import tree_sitter_c
            import tree_sitter_cpp
            from tree_sitter import Language
            # грамматика C++ расширяет C, поэтому правила подсветки C тоже применимы
            query = tree_sitter_c.HIGHLIGHTS_QUERY + "\n" + tree_sitter_cpp.HIGHLIGHTS_QUERY
            self.register_language("cpp", Language(tree_sitter_cpp.language()), query)
            self.language = "cpp"
        except Exception:
            pass   # без подсветки редактор тоже работает

    async def _on_key(self, event):
        if event.key == "enter" and not self.read_only:
            now = time.monotonic()
            if now - self._last_enter < DOUBLE_ENTER_SEC:
                # первый Enter уже вставил перевод строки, второй не вставляем
                self._last_enter = 0.0
                event.stop()
                event.prevent_default()
                self.post_message(self.CheckRequested())
                return
            self._last_enter = now
        await super()._on_key(event)


class OpenFileScreen(ModalScreen):
    BINDINGS = [Binding("escape", "cancel", "Отмена")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Путь к файлу C++ (.cpp, .cc, .h, .hpp)")
            yield Input(placeholder="~/projects/lab1/main.cpp", id="path")
            yield Label("Enter — открыть, Esc — отмена", classes="muted")

    @on(Input.Submitted)
    def submitted(self, event):
        self.dismiss(event.value.strip() or None)

    def action_cancel(self):
        self.dismiss(None)


class CppCheckerApp(App):
    TITLE = "CodeCheck · C++"
    CSS = """
    #main { height: 1fr; }
    #editor-pane { width: 2fr; border: round $primary; }
    CppEditor { height: 1fr; border: none; }
    #side { width: 1fr; min-width: 42; padding: 0 1; }
    .card { border: round $panel-lighten-2; padding: 0 1; height: auto; margin-bottom: 1; }
    #percent-row { height: auto; align: center middle; }
    #percent { width: auto; }
    #percent-sign { padding: 1 0 0 1; }
    #verdict { text-style: bold; content-align: center middle; width: 100%; }
    #bar { width: 100%; content-align: center middle; }
    .danger { color: $error; }
    .warn { color: $warning; }
    .ok { color: $success; }
    .muted { color: $text-muted; }
    #dialog { width: 64; height: auto; padding: 1 2; border: thick $primary; background: $surface; }
    OpenFileScreen { align: center middle; }
    """
    BINDINGS = [
        Binding("f5", "check", "Проверить"),
        Binding("ctrl+r", "check", "Проверить", show=False),
        Binding("ctrl+o", "open", "Открыть файл"),
        Binding("ctrl+l", "clear", "Очистить"),
        Binding("ctrl+q", "quit", "Выход"),
    ]

    def __init__(self, file=None, device="auto", model_path=MODEL_PATH):
        super().__init__()
        self.initial_file = file
        self.device = pick_device(device)
        self.model_path = Path(model_path)
        self.detector = None
        self.history = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="editor-pane"):
                yield CppEditor(id="editor")
            with Vertical(id="side"):
                with Vertical(id="result-card", classes="card"):
                    yield Label("Вероятность ИИ", classes="muted")
                    with Horizontal(id="percent-row"):
                        yield Digits("--", id="percent")
                        yield Label("%", id="percent-sign")
                    yield Static("", id="bar")
                    yield Static("Вставьте код и нажмите Enter дважды", id="verdict")
                yield Static("", id="details", classes="card")
                yield Static("Проверок пока нет", id="history", classes="card")
                yield Static("Результат — подсказка для проверки, а не доказательство. "
                             "Модель обучена только на C++.", classes="muted")
        yield Footer()

    def on_mount(self):
        self.query_one("#editor-pane").border_title = "Код C++"
        self.query_one("#result-card").border_title = "Результат"
        self.query_one("#details").border_title = "Подробности"
        self.query_one("#history").border_title = "История"
        self.sub_title = f"загрузка модели · {self.device}"
        self.query_one("#editor").focus()
        if self.initial_file:
            self.load_file(self.initial_file)
        self.load_model()

    # ── модель ──────────────────────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="model")
    def load_model(self):
        try:
            detector = CppDetector(self.model_path, self.device)
        except Exception as error:
            self.call_from_thread(self.model_failed, error)
            return
        self.call_from_thread(self.model_ready, detector)

    def model_ready(self, detector):
        self.detector = detector
        self.sub_title = f"модель {self.model_path.name} · устройство {self.device} · готово"

    def model_failed(self, error):
        self.sub_title = "модель не загружена"
        self.notify(f"Не удалось загрузить модель из {self.model_path}:\n{error}",
                    severity="error", timeout=15)

    # ── действия ────────────────────────────────────────────────────────────
    @on(CppEditor.CheckRequested)
    def on_check_requested(self):
        self.action_check()

    def action_check(self):
        code = self.query_one("#editor", CppEditor).text.strip()
        if len(code) < 10:
            self.notify("Вставьте код C++ — хотя бы несколько строк", severity="warning")
            return
        if self.detector is None:
            self.notify("Модель ещё загружается, подождите несколько секунд", severity="warning")
            return
        self.query_one("#result-card").loading = True
        self.run_check(code)

    @work(thread=True, exclusive=True, group="check")
    def run_check(self, code):
        started = time.monotonic()
        try:
            result = self.detector.analyze(code)
        except Exception as error:
            self.call_from_thread(self.check_failed, error)
            return
        result["seconds"] = time.monotonic() - started
        result["warning"] = language_warning(code)
        result["first_line"] = first_code_line(code)
        self.call_from_thread(self.show_result, result)

    def check_failed(self, error):
        self.query_one("#result-card").loading = False
        self.notify(f"Ошибка проверки: {error}", severity="error", timeout=10)

    def show_result(self, r):
        self.query_one("#result-card").loading = False
        ai = r["ai_pct"]
        verdict, tone = verdict_for(ai)

        percent = self.query_one("#percent", Digits)
        percent.update(str(round(ai)))
        for widget in (percent, self.query_one("#percent-sign"), self.query_one("#verdict")):
            widget.set_classes(tone)
        self.query_one("#verdict", Static).update(verdict)

        filled = round(ai / 100 * BAR_WIDTH)
        style = {"danger": "red", "warn": "yellow", "ok": "green"}[tone]
        bar = Text("человек ", style="dim")
        bar.append("█" * filled, style=style)
        bar.append("░" * (BAR_WIDTH - filled), style="dim")
        bar.append(" ИИ", style="dim")
        self.query_one("#bar", Static).update(bar)

        details = Text()
        details.append(f"ИИ {ai}% · человек {r['human_pct']}%\n")
        details.append(f"Токенов: {r['tokens']} · фрагментов: {len(r['fragments'])} · "
                       f"{r['seconds']:.1f} с\n")
        if len(r["fragments"]) > 1:
            top = sorted(r["fragments"], key=lambda f: f["ai_pct"], reverse=True)[:TOP_FRAGMENTS]
            details.append("Самые похожие на ИИ фрагменты:\n")
            for frag in sorted(top, key=lambda f: f["lines"]):
                a, b = frag["lines"]
                details.append(f"  строки {a}–{b}: ИИ {frag['ai_pct']}%\n", style="dim")
        if r["tokens"] < SHORT_TOKENS:
            details.append("Короткий фрагмент — оценка ненадёжна.\n", style="yellow")
        if r["warning"]:
            details.append(r["warning"] + "\n", style="yellow")
        self.query_one("#details", Static).update(details)

        self.history.insert(0, f"{datetime.now():%H:%M:%S}  {round(ai):>3}%  {r['first_line']}")
        self.query_one("#history", Static).update("\n".join(self.history[:8]))

    def action_open(self):
        self.push_screen(OpenFileScreen(), callback=self.load_file)

    def load_file(self, path):
        if not path:
            return
        p = Path(path).expanduser()
        try:
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = p.read_text(encoding="latin-1")
        except OSError as error:
            self.notify(f"Не удалось открыть файл: {error}", severity="error")
            return
        self.query_one("#editor", CppEditor).load_text(text)
        self.query_one("#editor-pane").border_title = f"Код C++ · {p.name}"
        self.notify(f"Открыт {p.name} — нажмите F5 для проверки")

    def action_clear(self):
        self.query_one("#editor", CppEditor).clear()
        self.query_one("#editor-pane").border_title = "Код C++"


def main():
    ap = argparse.ArgumentParser(description="Проверка кода C++ на ИИ-авторство")
    ap.add_argument("file", nargs="?", help="файл .cpp для проверки")
    ap.add_argument("--device", default="auto", help="auto (CUDA → MPS → CPU), cpu, mps, cuda")
    ap.add_argument("--model", default=str(MODEL_PATH), help=f"папка модели (по умолчанию {MODEL_PATH})")
    args = ap.parse_args()
    CppCheckerApp(args.file, args.device, args.model).run()


if __name__ == "__main__":
    main()
