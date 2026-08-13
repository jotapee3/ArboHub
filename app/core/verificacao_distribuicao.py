from __future__ import annotations

import os
from pathlib import Path

from app.core.ambiente_execucao import (
    PASTA_NAVEGADORES_PLAYWRIGHT,
    em_execucao_empacotada,
)
from app.core.caminhos import obter_raiz_projeto


def executar_verificacao_distribuicao() -> int:
    """Verifica os recursos essenciais sem abrir a interface."""

    raiz = obter_raiz_projeto()
    erros: list[str] = []

    verificacoes = {
        "ícone principal": (
            raiz / "app" / "gui" / "assets" / "arbohub.ico"
        ),
        "logos dos sistemas": (
            raiz / "assets" / "sistemas" / "sinan_logo.png"
        ),
        "pasta do Chromium": (
            raiz / PASTA_NAVEGADORES_PLAYWRIGHT
        ),
    }

    print("Verificação da distribuição do ArboHub")
    print(
        "Execução empacotada: "
        f"{'sim' if em_execucao_empacotada() else 'não'}"
    )

    for descricao, caminho in verificacoes.items():
        if caminho.exists():
            print(f"[OK] {descricao}: {caminho}")
        else:
            erros.append(
                f"{descricao} não encontrado: {caminho}"
            )

    pasta_configurada = os.environ.get(
        "PLAYWRIGHT_BROWSERS_PATH"
    )
    if em_execucao_empacotada() and not pasta_configurada:
        erros.append(
            "PLAYWRIGHT_BROWSERS_PATH não foi configurado."
        )

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executavel = Path(
                playwright.chromium.executable_path
            )

        if executavel.is_file():
            print(f"[OK] Chromium: {executavel}")
        else:
            erros.append(
                f"executável do Chromium não encontrado: {executavel}"
            )
    except Exception as erro:
        erros.append(
            f"Playwright não iniciou: {erro}"
        )

    if erros:
        print("\nDistribuição inválida:")
        for erro in erros:
            print(f"[ERRO] {erro}")
        return 1

    print("\nDistribuição validada.")
    return 0
