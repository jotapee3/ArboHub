from pathlib import Path

from watchfiles import PythonFilter, run_process

from main import main


RAIZ_PROJETO = Path(__file__).resolve().parent


if __name__ == "__main__":
    run_process(
        RAIZ_PROJETO / "app",
        RAIZ_PROJETO / "main.py",
        target=main,
        target_type="function",
        watch_filter=PythonFilter(),
        debounce=500
    )