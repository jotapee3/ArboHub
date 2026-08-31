from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from app.core.caminhos import obter_raiz_projeto


CAMINHO_RELATIVO_DICIONARIO = (
    Path("assets")
    / "qualifica"
    / "dicionario_municipios.xlsx"
)


def obter_caminho_dicionario_municipios() -> Path:
    """Localiza o dicionário que acompanha a instalação do ArboHub."""

    return obter_raiz_projeto() / CAMINHO_RELATIVO_DICIONARIO


def obter_pasta_padrao_relatorios_72h() -> Path:
    """Retorna o destino padrão dos relatórios do Qualifica."""

    return (
        Path.home()
        / "Documents"
        / "Qualifica"
        / "Relatorios"
        / "72h"
    )


def formatar_data_digitada(valor: str) -> str:
    """Insere as barras de DD/MM/AAAA sem aceitar outros caracteres."""

    digitos = "".join(
        caractere
        for caractere in str(valor)
        if caractere.isdigit()
    )[:8]

    if len(digitos) <= 2:
        return digitos
    if len(digitos) <= 4:
        return f"{digitos[:2]}/{digitos[2:]}"
    return (
        f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
    )


def converter_data_interface(valor: str) -> date:
    """Converte uma data completa da interface ou informa o erro."""

    texto = str(valor).strip()
    try:
        return datetime.strptime(
            texto,
            "%d/%m/%Y",
        ).date()
    except ValueError as erro:
        raise ValueError(
            f"A data {texto!r} é inválida. Use o formato DD/MM/AAAA."
        ) from erro


def criar_nome_relatorio_72h(
    data_inicial: date,
    data_final: date,
) -> str:
    """Cria a sugestão de nome a partir do indicador e do período."""

    if not isinstance(data_inicial, date):
        raise TypeError("A data inicial precisa ser uma data válida.")
    if not isinstance(data_final, date):
        raise TypeError("A data final precisa ser uma data válida.")
    if data_inicial > data_final:
        raise ValueError(
            "A data inicial não pode ser posterior à data final."
        )

    inicio = data_inicial.strftime("%d-%m-%Y")
    fim = data_final.strftime("%d-%m-%Y")
    return f"Qualifica_72h_{inicio}_a_{fim}.xlsx"


def validar_nome_relatorio_72h(nome: str) -> str:
    """Valida um nome editável de Excel sem permitir outro caminho."""

    valor = str(nome).strip()
    if not valor:
        raise ValueError("Informe o nome do arquivo Excel.")

    if Path(valor).name != valor or any(
        caractere in '<>:"/\\|?*'
        for caractere in valor
    ):
        raise ValueError(
            "O nome do relatório contém caracteres não permitidos."
        )

    if valor.endswith((" ", ".")):
        raise ValueError(
            "O nome do relatório não pode terminar com espaço ou ponto."
        )

    if not valor.casefold().endswith(".xlsx"):
        valor += ".xlsx"

    if len(valor) > 140:
        raise ValueError(
            "O nome do relatório deve ter no máximo 140 caracteres."
        )

    if not Path(valor).stem.strip(". "):
        raise ValueError("Informe um nome válido antes de .xlsx.")

    nomes_reservados = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{numero}" for numero in range(1, 10)),
        *(f"LPT{numero}" for numero in range(1, 10)),
    }
    if Path(valor).stem.upper() in nomes_reservados:
        raise ValueError("Esse nome é reservado pelo Windows.")

    return valor
