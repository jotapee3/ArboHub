from __future__ import annotations

import os
import sys
from pathlib import Path


NOME_APLICATIVO = "ArboHub"


def obter_raiz_projeto() -> Path:
    """Retorna a raiz dos recursos da execução atual do ArboHub."""

    if getattr(sys, "frozen", False):
        raiz_empacotada = getattr(
            sys,
            "_MEIPASS",
            Path(sys.executable).resolve().parent
        )
        return Path(raiz_empacotada).resolve()

    return Path(__file__).resolve().parents[2]


def obter_pasta_local_appdata() -> Path:
    """Retorna a pasta local de dados do usuário no Windows."""

    caminho = os.environ.get("LOCALAPPDATA")

    if caminho:
        return Path(caminho).expanduser().resolve()

    return (
        Path.home() / "AppData" / "Local"
    ).expanduser().resolve()


def obter_pasta_local_arbohub() -> Path:
    """Retorna a pasta privada desta instalação para o usuário atual."""

    return obter_pasta_local_appdata() / NOME_APLICATIVO


def obter_pasta_dados_arbohub() -> Path:
    """Retorna a pasta destinada aos dados operacionais locais."""

    return obter_pasta_local_arbohub() / "dados"


def obter_pasta_temporaria_arbohub() -> Path:
    """Retorna a pasta destinada a arquivos locais temporários."""

    return obter_pasta_local_arbohub() / "temp"
