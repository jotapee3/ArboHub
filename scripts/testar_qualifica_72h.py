from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from app.services.qualifica.relatorio_72h_service import (
    Relatorio72hService,
)


def converter_data(valor: str):
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError as erro:
        raise argparse.ArgumentTypeError(
            "Use datas no formato DD/MM/AAAA."
        ) from erro


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida manualmente o motor de 72h do Qualifica, sem abrir "
            "a interface do ArboHub."
        )
    )
    parser.add_argument(
        "--dicionario",
        required=True,
        type=Path,
        help="Dicionário de municípios em XLSX.",
    )
    parser.add_argument(
        "--dbf",
        required=True,
        type=Path,
        nargs="+",
        help="Um ou mais bancos DBF do SINAN.",
    )
    parser.add_argument(
        "--inicio",
        required=True,
        type=converter_data,
        help="Data inicial de sintomas em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--fim",
        required=True,
        type=converter_data,
        help="Data final de sintomas em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--saida",
        required=True,
        type=Path,
        help="Destino XLSX do relatório.",
    )
    return parser


def main() -> int:
    argumentos = criar_parser().parse_args()
    service = Relatorio72hService()

    try:
        resultado = service.gerar_relatorio(
            caminho_dicionario=argumentos.dicionario,
            caminhos_dbf=argumentos.dbf,
            data_inicial=argumentos.inicio,
            data_final=argumentos.fim,
            caminho_saida=argumentos.saida,
            callback_status=lambda mensagem: print(
                f"[QUALIFICA 72H] {mensagem}"
            ),
        )
    except Exception as erro:
        print(f"[ERRO] {erro}")
        return 1

    print(
        "[OK] Relatório concluído: "
        f"{resultado.total_notificacoes} notificação(ões), "
        f"{resultado.total_dentro_do_prazo} dentro do prazo, "
        f"{resultado.percentual_estadual:.2f}% no estado."
    )
    for aviso in resultado.avisos:
        print(f"[AVISO] {aviso}")
    print(f"[OK] Arquivo salvo em: {argumentos.saida.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
