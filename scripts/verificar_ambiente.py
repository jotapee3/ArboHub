from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


VERSAO_PYTHON_VALIDADA = (3, 14)

PACOTES_OBRIGATORIOS = {
    "customtkinter": "6.0.0",
    "pillow": "12.3.0",
    "playwright": "1.61.0",
}

PACOTES_DESENVOLVIMENTO = {
    "watchfiles": "1.2.0",
}


def verificar_pacotes(
    pacotes: dict[str, str],
    *,
    obrigatorios: bool,
) -> list[str]:
    problemas: list[str] = []

    for nome, esperada in pacotes.items():
        try:
            instalada = version(nome)
        except PackageNotFoundError:
            if obrigatorios:
                problemas.append(
                    f"{nome}: não instalado (esperado {esperada})"
                )
            else:
                print(
                    f"[AVISO] {nome}: não instalado; necessário "
                    "somente para desenvolvimento."
                )
            continue

        if instalada != esperada:
            problemas.append(
                f"{nome}: versão {instalada}; esperada {esperada}"
            )
            continue

        print(f"[OK] {nome} {instalada}")

    return problemas


def verificar_chromium() -> str | None:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            executavel = Path(
                playwright.chromium.executable_path
            )
    except Exception as erro:
        return f"Playwright não pôde localizar o Chromium: {erro}"

    if not executavel.is_file():
        return (
            "Chromium do Playwright não encontrado. Execute: "
            "python -m playwright install chromium"
        )

    print(f"[OK] Chromium: {executavel}")
    return None


def main() -> int:
    print("Verificação do ambiente do ArboHub")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Executável: {sys.executable}")

    problemas: list[str] = []

    if sys.version_info[:2] != VERSAO_PYTHON_VALIDADA:
        problemas.append(
            "Python incompatível com o ambiente validado: "
            f"esperado {VERSAO_PYTHON_VALIDADA[0]}."
            f"{VERSAO_PYTHON_VALIDADA[1]}.x"
        )
    else:
        print(
            "[OK] Série do Python: "
            f"{VERSAO_PYTHON_VALIDADA[0]}."
            f"{VERSAO_PYTHON_VALIDADA[1]}.x"
        )

    problemas.extend(
        verificar_pacotes(
            PACOTES_OBRIGATORIOS,
            obrigatorios=True,
        )
    )
    problemas.extend(
        verificar_pacotes(
            PACOTES_DESENVOLVIMENTO,
            obrigatorios=False,
        )
    )

    problema_chromium = verificar_chromium()
    if problema_chromium:
        problemas.append(problema_chromium)

    if problemas:
        print("\nAmbiente não validado:")
        for problema in problemas:
            print(f"- {problema}")
        return 1

    print("\nAmbiente validado para o ArboHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
