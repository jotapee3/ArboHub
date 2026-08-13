from __future__ import annotations

import os
import sys
from pathlib import Path

from app.core.caminhos import obter_raiz_projeto


PASTA_NAVEGADORES_PLAYWRIGHT = "ms-playwright"


def em_execucao_empacotada() -> bool:
    """Informa se o processo atual foi gerado pelo PyInstaller."""

    return bool(getattr(sys, "frozen", False))


def preparar_ambiente_execucao() -> Path | None:
    """
    Direciona o Playwright ao Chromium incluído na distribuição.

    Em desenvolvimento, mantém o comportamento padrão do Playwright.
    No executável, fixa o navegador na pasta interna do pacote para
    não depender de instalação ou download no computador do usuário.
    """

    if not em_execucao_empacotada():
        return None

    pasta_navegadores = (
        obter_raiz_projeto()
        / PASTA_NAVEGADORES_PLAYWRIGHT
    ).resolve()

    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
        pasta_navegadores
    )

    return pasta_navegadores
