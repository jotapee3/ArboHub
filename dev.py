from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import IO

from watchfiles import awatch


RAIZ_PROJETO = Path(__file__).resolve().parent
ARQUIVO_PRINCIPAL = RAIZ_PROJETO / "main.py"
ARQUIVO_LOCK = RAIZ_PROJETO / ".arbohub-dev.lock"

EXTENSOES_MONITORADAS = {
    ".py",
    ".json",
    ".png",
    ".ico"
}

PASTAS_IGNORADAS = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "__pycache__",
    "data",
    "dist",
    "build"
}


def arquivo_relevante(
    _mudanca,
    caminho: str
) -> bool:
    """
    Reinicia apenas quando um arquivo relevante do projeto muda.

    Bancos locais, arquivos temporários e conteúdos da pasta data
    não disparam recarregamento.
    """

    arquivo = Path(caminho)

    partes = {
        parte.casefold()
        for parte in arquivo.parts
    }

    if partes.intersection(
        {
            pasta.casefold()
            for pasta in PASTAS_IGNORADAS
        }
    ):
        return False

    return (
        arquivo.suffix.casefold()
        in EXTENSOES_MONITORADAS
    )


def adquirir_lock() -> IO[str]:
    """
    Impede que dois processos dev.py sejam executados ao mesmo tempo.
    """

    arquivo = ARQUIVO_LOCK.open(
        "a+",
        encoding="utf-8"
    )

    arquivo.seek(0)
    arquivo.write("1")
    arquivo.flush()
    arquivo.seek(0)

    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(
                arquivo.fileno(),
                msvcrt.LK_NBLCK,
                1
            )
        else:
            import fcntl

            fcntl.flock(
                arquivo.fileno(),
                fcntl.LOCK_EX
                | fcntl.LOCK_NB
            )

    except OSError as erro:
        arquivo.close()

        raise RuntimeError(
            "Já existe outro dev.py executando o ArboHub. "
            "Feche o terminal antigo antes de iniciar novamente."
        ) from erro

    return arquivo


def iniciar_aplicativo() -> subprocess.Popen:
    """
    Abre uma única instância do main.py.
    """

    ambiente = os.environ.copy()
    ambiente["PYTHONDONTWRITEBYTECODE"] = "1"

    flags = 0

    if os.name == "nt":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
        )

    processo = subprocess.Popen(
        [
            sys.executable,
            str(ARQUIVO_PRINCIPAL)
        ],
        cwd=RAIZ_PROJETO,
        env=ambiente,
        creationflags=flags
    )

    print(
        f"[ArboHub Dev] Aplicativo iniciado "
        f"(PID {processo.pid})."
    )

    return processo


def encerrar_aplicativo(
    processo: subprocess.Popen | None
):
    """
    Encerra toda a árvore do aplicativo antes de iniciar outra.

    No Windows, taskkill /T remove também eventuais processos filhos,
    evitando que a janela antiga permaneça aberta após o reload.
    """

    if processo is None:
        return

    if processo.poll() is not None:
        return

    print(
        f"[ArboHub Dev] Encerrando PID "
        f"{processo.pid}..."
    )

    if os.name == "nt":
        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(processo.pid),
                "/T",
                "/F"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False
        )
    else:
        try:
            os.killpg(
                os.getpgid(processo.pid),
                signal.SIGTERM
            )
        except ProcessLookupError:
            pass

    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=5)


async def executar_recarregamento():
    """
    Mantém exatamente uma janela aberta e reinicia após alterações.
    """

    if not ARQUIVO_PRINCIPAL.exists():
        raise FileNotFoundError(
            f"main.py não encontrado em: "
            f"{ARQUIVO_PRINCIPAL}"
        )

    processo: subprocess.Popen | None = None

    try:
        processo = iniciar_aplicativo()

        async for alteracoes in awatch(
            RAIZ_PROJETO,
            watch_filter=arquivo_relevante,
            debounce=700,
            step=150
        ):
            caminhos = sorted(
                {
                    Path(caminho)
                    .relative_to(RAIZ_PROJETO)
                    for _, caminho in alteracoes
                },
                key=str
            )

            print()
            print(
                "[ArboHub Dev] Alteração detectada:"
            )

            for caminho in caminhos:
                print(f"  - {caminho}")

            encerrar_aplicativo(
                processo
            )

            await asyncio.sleep(0.25)

            processo = iniciar_aplicativo()

    finally:
        encerrar_aplicativo(
            processo
        )


def main():
    lock = None

    try:
        lock = adquirir_lock()

        print(
            "[ArboHub Dev] Recarregamento automático ativo."
        )
        print(
            "[ArboHub Dev] Use Ctrl+C para encerrar."
        )
        print()

        asyncio.run(
            executar_recarregamento()
        )

    except KeyboardInterrupt:
        print()
        print(
            "[ArboHub Dev] Encerrado pelo usuário."
        )

    except RuntimeError as erro:
        print()
        print(f"[ArboHub Dev] {erro}")

    finally:
        if lock is not None:
            lock.close()

        try:
            ARQUIVO_LOCK.unlink(
                missing_ok=True
            )
        except OSError:
            pass


if __name__ == "__main__":
    main()