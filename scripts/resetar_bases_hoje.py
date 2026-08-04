from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path


FRASE_CONFIRMACAO = "RESETAR BASES"


def obter_raiz_projeto() -> Path:
    return Path(__file__).resolve().parents[1]


def listar_tabelas(conexao: sqlite3.Connection) -> set[str]:
    linhas = conexao.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    ).fetchall()
    return {linha[0] for linha in linhas}


def colunas_tabela(
    conexao: sqlite3.Connection,
    tabela: str
) -> set[str]:
    linhas = conexao.execute(
        f"PRAGMA table_info({tabela})"
    ).fetchall()
    return {linha[1] for linha in linhas}


def localizar_arquivos_do_dia(
    data_referencia: date
) -> tuple[list[Path], list[Path]]:
    data_iso = data_referencia.isoformat()

    historicos: list[Path] = []
    raiz_historico = (
        Path.home()
        / "Documents"
        / "SINAN"
        / "Historico"
    )

    if raiz_historico.exists():
        nomes = {
            f"dengue_{data_iso}.zip",
            f"chiku_{data_iso}.zip",
            f"chikungunya_{data_iso}.zip"
        }

        for arquivo in raiz_historico.rglob("*.zip"):
            if arquivo.name.casefold() in {
                nome.casefold()
                for nome in nomes
            }:
                historicos.append(arquivo)

    stagings: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        raiz_staging = (
            Path(local_app_data)
            / "ArboHub"
            / "temp"
            / "exportacoes"
        )

        if raiz_staging.exists():
            padrao = f"exportacao_{data_iso}_*"
            stagings.extend(
                caminho
                for caminho in raiz_staging.glob(padrao)
                if caminho.exists()
            )

    return historicos, stagings


def obter_registros_do_dia(
    conexao: sqlite3.Connection,
    data_iso: str
) -> dict:
    tabelas = listar_tabelas(conexao)
    resultado = {
        "lotes": [],
        "solicitacoes": []
    }

    if "exportacao_dbf_lote" not in tabelas:
        return resultado

    lotes = conexao.execute(
        """
        SELECT *
        FROM exportacao_dbf_lote
        WHERE data_referencia = ?
        ORDER BY criado_em
        """,
        (data_iso,)
    ).fetchall()

    resultado["lotes"] = [
        dict(linha)
        for linha in lotes
    ]

    lote_ids = [
        linha["lote_id"]
        for linha in lotes
    ]

    if (
        lote_ids
        and "exportacao_dbf_solicitacao" in tabelas
    ):
        placeholders = ",".join(
            "?"
            for _ in lote_ids
        )

        solicitacoes = conexao.execute(
            f"""
            SELECT *
            FROM exportacao_dbf_solicitacao
            WHERE lote_id IN ({placeholders})
            ORDER BY solicitado_em
            """,
            lote_ids
        ).fetchall()

        resultado["solicitacoes"] = [
            dict(linha)
            for linha in solicitacoes
        ]

    return resultado


def mover_com_backup(
    origem: Path,
    destino: Path
) -> None:
    destino.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if destino.exists():
        sufixo = datetime.now().strftime(
            "%H%M%S%f"
        )
        destino = destino.with_name(
            f"{destino.stem}_{sufixo}"
            f"{destino.suffix}"
        )

    shutil.move(
        str(origem),
        str(destino)
    )


def restaurar_movimentos(
    movimentos: list[tuple[Path, Path]]
) -> None:
    for origem, destino in reversed(movimentos):
        if not destino.exists():
            continue

        origem.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        shutil.move(
            str(destino),
            str(origem)
        )


def executar_reset(
    raiz_projeto: Path,
    data_referencia: date
) -> Path:
    data_iso = data_referencia.isoformat()
    banco = (
        raiz_projeto
        / "data"
        / "arbohub.db"
    )

    if not banco.exists():
        raise FileNotFoundError(
            f"Banco local não encontrado: {banco}"
        )

    carimbo = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )
    pasta_backup = (
        raiz_projeto
        / "data"
        / "backups"
        / "reset_bases"
        / carimbo
    )
    pasta_backup.mkdir(
        parents=True,
        exist_ok=False
    )

    backup_banco = (
        pasta_backup
        / "arbohub_antes_reset.db"
    )
    shutil.copy2(
        banco,
        backup_banco
    )

    historicos, stagings = localizar_arquivos_do_dia(
        data_referencia
    )

    movimentos: list[tuple[Path, Path]] = []

    try:
        raiz_historico = (
            Path.home()
            / "Documents"
            / "SINAN"
            / "Historico"
        )

        for arquivo in historicos:
            try:
                relativo = arquivo.relative_to(
                    raiz_historico
                )
            except ValueError:
                relativo = Path(
                    arquivo.name
                )

            destino = (
                pasta_backup
                / "historico"
                / relativo
            )
            mover_com_backup(
                arquivo,
                destino
            )
            movimentos.append(
                (arquivo, destino)
            )

        for caminho in stagings:
            destino = (
                pasta_backup
                / "staging"
                / caminho.name
            )
            mover_com_backup(
                caminho,
                destino
            )
            movimentos.append(
                (caminho, destino)
            )

        with sqlite3.connect(banco) as conexao:
            conexao.row_factory = sqlite3.Row
            conexao.execute(
                "PRAGMA foreign_keys = ON"
            )

            registros = obter_registros_do_dia(
                conexao,
                data_iso
            )
            tabelas = listar_tabelas(
                conexao
            )

            conexao.execute("BEGIN")

            if "exportacao_dbf_lote" in tabelas:
                lote_ids = [
                    item["lote_id"]
                    for item in registros["lotes"]
                ]

                if (
                    lote_ids
                    and "exportacao_dbf_solicitacao"
                    in tabelas
                ):
                    placeholders = ",".join(
                        "?"
                        for _ in lote_ids
                    )
                    conexao.execute(
                        f"""
                        DELETE FROM exportacao_dbf_solicitacao
                        WHERE lote_id IN ({placeholders})
                        """,
                        lote_ids
                    )

                conexao.execute(
                    """
                    DELETE FROM exportacao_dbf_lote
                    WHERE data_referencia = ?
                    """,
                    (data_iso,)
                )

            if "rotina_diaria" in tabelas:
                colunas = colunas_tabela(
                    conexao,
                    "rotina_diaria"
                )

                atualizacoes = []
                valores = []

                for coluna, valor in (
                    ("atualizacao_bases", 0),
                    ("atualizacao_bases_em", None),
                    ("alerta_enviado", 0),
                    ("alerta_enviado_em", None)
                ):
                    if coluna in colunas:
                        atualizacoes.append(
                            f"{coluna} = ?"
                        )
                        valores.append(valor)

                if atualizacoes:
                    valores.append(data_iso)
                    conexao.execute(
                        f"""
                        UPDATE rotina_diaria
                        SET {", ".join(atualizacoes)}
                        WHERE data_referencia = ?
                        """,
                        valores
                    )

            conexao.commit()

        manifesto = {
            "executado_em": datetime.now().isoformat(
                timespec="seconds"
            ),
            "data_resetada": data_iso,
            "banco_original": str(banco),
            "backup_banco": str(backup_banco),
            "lotes_removidos": registros["lotes"],
            "solicitacoes_removidas":
                registros["solicitacoes"],
            "arquivos_historicos_movidos": [
                {
                    "origem": str(origem),
                    "backup": str(destino)
                }
                for origem, destino in movimentos
                if "historico" in destino.parts
            ],
            "stagings_movidos": [
                {
                    "origem": str(origem),
                    "backup": str(destino)
                }
                for origem, destino in movimentos
                if "staging" in destino.parts
            ]
        }

        (
            pasta_backup
            / "manifesto_reset.json"
        ).write_text(
            json.dumps(
                manifesto,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        return pasta_backup

    except Exception:
        restaurar_movimentos(
            movimentos
        )

        shutil.copy2(
            backup_banco,
            banco
        )
        raise


def mostrar_previa(
    raiz_projeto: Path,
    data_referencia: date
) -> None:
    banco = (
        raiz_projeto
        / "data"
        / "arbohub.db"
    )
    data_iso = data_referencia.isoformat()

    if not banco.exists():
        raise FileNotFoundError(
            f"Banco local não encontrado: {banco}"
        )

    with sqlite3.connect(banco) as conexao:
        conexao.row_factory = sqlite3.Row
        registros = obter_registros_do_dia(
            conexao,
            data_iso
        )

    historicos, stagings = localizar_arquivos_do_dia(
        data_referencia
    )

    print()
    print("=" * 64)
    print("PRÉVIA DO RESET COMPLETO DE BASES")
    print("=" * 64)
    print(f"Data: {data_iso}")
    print(
        f"Lotes locais encontrados: "
        f"{len(registros['lotes'])}"
    )
    print(
        f"Solicitações locais encontradas: "
        f"{len(registros['solicitacoes'])}"
    )

    for solicitacao in registros[
        "solicitacoes"
    ]:
        print(
            "  - "
            f"{solicitacao.get('agravo', '?')}: "
            f"{solicitacao.get('numero_solicitacao', '?')}"
        )

    print(
        f"ZIPs históricos de hoje: "
        f"{len(historicos)}"
    )
    for arquivo in historicos:
        print(f"  - {arquivo}")

    print(
        f"Pastas temporárias de hoje: "
        f"{len(stagings)}"
    )
    for caminho in stagings:
        print(f"  - {caminho}")

    print()
    print("Será resetado:")
    print(
        "  - solicitações locais de Dengue e "
        "Chikungunya do dia;"
    )
    print(
        "  - status visual de atualização de Bases;"
    )
    print(
        "  - ZIPs históricos do dia, movidos para backup;"
    )
    print(
        "  - pastas temporárias do dia, movidas para backup."
    )

    print()
    print("NÃO será alterado:")
    print("  - Consulta de óbitos;")
    print("  - Relatórios;")
    print("  - DBFs antigos de Teste AB1/AB2;")
    print("  - DBFs de Bancos_Atuais;")
    print("  - solicitações que já existem no site do SINAN.")
    print("=" * 64)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reseta com backup a rotina de Bases do dia atual "
            "para permitir um teste completo desde a solicitação."
        )
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help=(
            "Executa o reset. Sem esta opção, apenas mostra "
            "uma prévia."
        )
    )
    parser.add_argument(
        "--data",
        type=str,
        default=date.today().isoformat(),
        help="Data no formato AAAA-MM-DD."
    )

    argumentos = parser.parse_args()

    try:
        data_referencia = date.fromisoformat(
            argumentos.data
        )
    except ValueError:
        print(
            "Data inválida. Use AAAA-MM-DD.",
            file=sys.stderr
        )
        return 2

    raiz_projeto = obter_raiz_projeto()

    try:
        mostrar_previa(
            raiz_projeto,
            data_referencia
        )

        if not argumentos.executar:
            print(
                "Prévia concluída. Nada foi alterado."
            )
            print(
                "Para executar, use:"
            )
            print(
                "python scripts/resetar_bases_hoje.py --executar"
            )
            return 0

        print(
            "Feche o ArboHub antes de continuar."
        )
        resposta = input(
            f'Digite exatamente "{FRASE_CONFIRMACAO}" '
            "para confirmar: "
        ).strip()

        if resposta != FRASE_CONFIRMACAO:
            print(
                "Confirmação incorreta. Nenhuma alteração feita."
            )
            return 1

        pasta_backup = executar_reset(
            raiz_projeto,
            data_referencia
        )

        print()
        print("Reset concluído com segurança.")
        print(
            "A aba Bases deverá abrir como uma rotina nova."
        )
        print(
            f"Backup criado em: {pasta_backup}"
        )
        print()
        print("Agora execute:")
        print("python main.py")
        return 0

    except Exception as erro:
        print(
            f"Falha ao resetar Bases: {erro}",
            file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())