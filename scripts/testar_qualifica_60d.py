from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from app.services.qualifica.relatorio_60d_service import (
    Relatorio60dService,
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
            "Valida manualmente o motor de 60 dias do Qualifica, sem "
            "abrir a interface do ArboHub."
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
        help="Um ou mais bancos DBF de Dengue do SINAN.",
    )
    parser.add_argument(
        "--notificacao-inicio",
        required=True,
        type=converter_data,
        help="Data inicial de notificação em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--notificacao-fim",
        required=True,
        type=converter_data,
        help="Data final de notificação em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--sintomas-inicio",
        required=True,
        type=converter_data,
        help="Data inicial de primeiros sintomas em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--sintomas-fim",
        required=True,
        type=converter_data,
        help="Data final de primeiros sintomas em DD/MM/AAAA.",
    )
    parser.add_argument(
        "--saida",
        required=True,
        type=Path,
        help="Destino XLSX do relatório.",
    )
    parser.add_argument(
        "--sentinela",
        action="store_true",
        help=(
            "Exclui notificações feitas em Porto Alegre para residentes "
            "de outros municípios."
        ),
    )
    return parser


def main() -> int:
    argumentos = criar_parser().parse_args()
    service = Relatorio60dService()

    try:
        resultado = service.gerar_relatorio(
            caminho_dicionario=argumentos.dicionario,
            caminhos_dbf=argumentos.dbf,
            notificacao_inicial=argumentos.notificacao_inicio,
            notificacao_final=argumentos.notificacao_fim,
            sintomas_inicial=argumentos.sintomas_inicio,
            sintomas_final=argumentos.sintomas_fim,
            caminho_saida=argumentos.saida,
            ignorar_poa=argumentos.sentinela,
            callback_status=lambda mensagem: print(
                f"[QUALIFICA 60D] {mensagem}"
            ),
        )
    except Exception as erro:
        print(f"[ERRO] {erro}")
        return 1

    print(
        "[OK] Relatório concluído: "
        f"{resultado.total_notificados} notificação(ões), "
        f"{resultado.total_no_prazo} dentro do prazo, "
        f"{resultado.percentual_estadual:.2f}% no estado."
    )
    for aviso in resultado.avisos:
        print(f"[AVISO] {aviso}")
    print(f"[OK] Arquivo salvo em: {argumentos.saida.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
