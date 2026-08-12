from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.database import (
    conectar_sqlite,
    obter_caminho_banco_na_raiz,
    obter_caminho_banco_padrao,
    obter_raiz_projeto,
    resolver_caminho_banco,
)
from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)


@dataclass(frozen=True)
class PreviaResetBases:
    """
    Estado local da rotina de Bases para uma data específica.

    O objeto contém apenas metadados operacionais. Nenhum conteúdo
    de DBF ou dado de paciente é lido.
    """

    data_referencia: date
    lotes: tuple[dict[str, Any], ...]
    solicitacoes: tuple[dict[str, Any], ...]
    arquivos_historicos: tuple[Path, ...]
    pastas_temporarias: tuple[Path, ...]
    atualizacao_bases_concluida: bool
    alerta_enviado: bool

    @property
    def possui_estado_local(self) -> bool:
        return bool(
            self.lotes
            or self.solicitacoes
            or self.arquivos_historicos
            or self.pastas_temporarias
            or self.atualizacao_bases_concluida
            or self.alerta_enviado
        )

    def numeros_por_agravo(self) -> dict[str, str]:
        numeros: dict[str, str] = {}

        for solicitacao in self.solicitacoes:
            agravo = str(
                solicitacao.get(
                    "agravo",
                    ""
                )
            ).strip().casefold()
            numero = str(
                solicitacao.get(
                    "numero_solicitacao",
                    ""
                )
            ).strip()

            if agravo and numero:
                numeros[agravo] = numero

        return numeros


class ManutencaoService:
    """
    Ferramentas locais de teste e manutenção do ArboHub.

    O reset completo de Bases:
    - cria um backup consistente do banco SQLite;
    - preserva Consulta e Relatórios;
    - remove apenas lotes e solicitações locais da data;
    - reseta somente o checkpoint visual de Bases;
    - move ZIPs históricos e staging da data para o backup;
    - restaura o estado anterior automaticamente em caso de falha.

    As solicitações já enviadas ao site do SINAN não podem ser
    apagadas por este serviço e continuarão visíveis no sistema.
    """

    FRASE_CONFIRMACAO = "RESETAR BASES"

    def __init__(
        self,
        raiz_projeto: str | Path | None = None,
        caminho_banco: str | Path | None = None,
        arquivos_service:
            ArquivosExportacaoDbfService | None = None
    ):
        raiz_personalizada = raiz_projeto is not None

        if raiz_projeto is None:
            raiz_projeto = obter_raiz_projeto()

        self.raiz_projeto = Path(
            raiz_projeto
        ).expanduser().resolve()

        if caminho_banco is None:
            caminho_banco = (
                obter_caminho_banco_na_raiz(
                    self.raiz_projeto
                )
                if raiz_personalizada
                else obter_caminho_banco_padrao()
            )

        self.caminho_banco = resolver_caminho_banco(
            caminho_banco
        )

        self.arquivos_service = (
            arquivos_service
            or ArquivosExportacaoDbfService()
        )

        self.pasta_dados = (
            self.raiz_projeto
            / "data"
        )
        self.pasta_backups = (
            self.pasta_dados
            / "backups"
            / "reset_bases"
        )
        self.pasta_temporaria = (
            self.arquivos_service
            .raiz_staging
        )

    # ------------------------------------------------------------------
    # Prévia
    # ------------------------------------------------------------------

    def gerar_previa_reset_bases(
        self,
        data_referencia: date | None = None
    ) -> PreviaResetBases:
        data_referencia = (
            data_referencia
            or date.today()
        )

        if not self.caminho_banco.exists():
            raise FileNotFoundError(
                "O banco operacional do ArboHub não foi encontrado:\n"
                f"{self.caminho_banco}"
            )

        data_iso = data_referencia.isoformat()

        with self._conectar() as conexao:
            tabelas = self._listar_tabelas(
                conexao
            )
            registros = self._obter_registros_exportacao(
                conexao=conexao,
                data_iso=data_iso,
                tabelas=tabelas
            )
            rotina = self._obter_estado_rotina(
                conexao=conexao,
                data_iso=data_iso,
                tabelas=tabelas
            )

        historicos = self._localizar_historicos(
            data_referencia
        )
        temporarios = self._localizar_temporarios(
            data_referencia
        )

        return PreviaResetBases(
            data_referencia=data_referencia,
            lotes=tuple(
                registros["lotes"]
            ),
            solicitacoes=tuple(
                registros["solicitacoes"]
            ),
            arquivos_historicos=tuple(
                historicos
            ),
            pastas_temporarias=tuple(
                temporarios
            ),
            atualizacao_bases_concluida=bool(
                rotina.get(
                    "atualizacao_bases",
                    False
                )
            ),
            alerta_enviado=bool(
                rotina.get(
                    "alerta_enviado",
                    False
                )
            )
        )

    def formatar_previa(
        self,
        previa: PreviaResetBases
    ) -> str:
        numeros = previa.numeros_por_agravo()

        linhas = [
            (
                "Data que será resetada: "
                f"{previa.data_referencia.strftime('%d/%m/%Y')}"
            ),
            "",
            (
                "Lotes locais encontrados: "
                f"{len(previa.lotes)}"
            ),
            (
                "Solicitações locais encontradas: "
                f"{len(previa.solicitacoes)}"
            )
        ]

        for agravo, rotulo in (
            ("dengue", "Dengue"),
            ("chikungunya", "Chikungunya")
        ):
            numero = numeros.get(agravo)

            if numero:
                linhas.append(
                    f"• {rotulo}: solicitação {numero}"
                )

        linhas.extend(
            [
                (
                    "ZIPs históricos encontrados: "
                    f"{len(previa.arquivos_historicos)}"
                ),
                (
                    "Pastas temporárias encontradas: "
                    f"{len(previa.pastas_temporarias)}"
                ),
                "",
                "SERÁ RESETADO",
                "• solicitações locais de Bases desta data;",
                "• progresso e alerta da rotina de Bases;",
                "• ZIPs históricos da data, movidos para backup;",
                "• staging da data, movido para backup.",
                "",
                "SERÁ PRESERVADO",
                "• Consulta e relatórios de óbitos;",
                (
                    "• DBFs dos destinos configurados para Dengue "
                    "e Chikungunya;"
                ),
                "• DBFs de Bancos_Atuais;",
                "• arquivos e registros de outras datas.",
                "",
                (
                    "As solicitações antigas continuarão visíveis "
                    "no site do SINAN."
                )
            ]
        )

        return "\n".join(
            linhas
        )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def executar_reset_bases(
        self,
        frase_confirmacao: str,
        data_referencia: date | None = None
    ) -> dict[str, Any]:
        if (
            str(frase_confirmacao).strip()
            != self.FRASE_CONFIRMACAO
        ):
            raise PermissionError(
                "A frase de confirmação está incorreta."
            )

        data_referencia = (
            data_referencia
            or date.today()
        )
        previa = self.gerar_previa_reset_bases(
            data_referencia
        )

        carimbo = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )
        pasta_backup = (
            self.pasta_backups
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

        self._criar_backup_sqlite(
            backup_banco
        )

        movimentos: list[tuple[Path, Path]] = []
        registros_removidos = {
            "lotes": list(
                previa.lotes
            ),
            "solicitacoes": list(
                previa.solicitacoes
            )
        }

        try:
            for arquivo in previa.arquivos_historicos:
                relativo = self._caminho_relativo_seguro(
                    arquivo,
                    self.arquivos_service.raiz_historico
                )
                destino = (
                    pasta_backup
                    / "historico"
                    / relativo
                )
                destino_real = self._mover_para_backup(
                    arquivo,
                    destino
                )
                movimentos.append(
                    (
                        arquivo,
                        destino_real
                    )
                )

            for pasta in previa.pastas_temporarias:
                destino = (
                    pasta_backup
                    / "staging"
                    / pasta.name
                )
                destino_real = self._mover_para_backup(
                    pasta,
                    destino
                )
                movimentos.append(
                    (
                        pasta,
                        destino_real
                    )
                )

            self._resetar_banco(
                data_referencia
            )

            resultado = {
                "executado_em": (
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                ),
                "data_resetada": (
                    data_referencia.isoformat()
                ),
                "pasta_backup": str(
                    pasta_backup
                ),
                "backup_banco": str(
                    backup_banco
                ),
                "lotes_removidos": (
                    registros_removidos["lotes"]
                ),
                "solicitacoes_removidas": (
                    registros_removidos[
                        "solicitacoes"
                    ]
                ),
                "arquivos_movidos": [
                    {
                        "origem": str(origem),
                        "backup": str(destino)
                    }
                    for origem, destino in movimentos
                ]
            }

            (
                pasta_backup
                / "manifesto_reset.json"
            ).write_text(
                json.dumps(
                    resultado,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

            return resultado

        except Exception:
            self._restaurar_movimentos(
                movimentos
            )
            self._restaurar_banco(
                backup_banco
            )
            raise

    # ------------------------------------------------------------------
    # Pastas
    # ------------------------------------------------------------------

    def abrir_pasta_backups(self):
        self.pasta_backups.mkdir(
            parents=True,
            exist_ok=True
        )
        self._abrir_pasta(
            self.pasta_backups
        )

    def abrir_pasta_temporaria(self):
        self.pasta_temporaria.mkdir(
            parents=True,
            exist_ok=True
        )
        self._abrir_pasta(
            self.pasta_temporaria
        )

    def abrir_pasta_dados(self):
        self.pasta_dados.mkdir(
            parents=True,
            exist_ok=True
        )
        self._abrir_pasta(
            self.pasta_dados
        )

    # ------------------------------------------------------------------
    # Banco de dados
    # ------------------------------------------------------------------

    def _conectar(self):
        return conectar_sqlite(
            self.caminho_banco,
            timeout=10,
            chaves_estrangeiras=True,
        )

    def _criar_backup_sqlite(
        self,
        destino: Path
    ):
        destino.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with self._conectar() as origem:
            with conectar_sqlite(
                destino,
                timeout=10,
            ) as backup:
                origem.backup(
                    backup
                )
                backup.commit()

    def _restaurar_banco(
        self,
        backup_banco: Path
    ):
        if not backup_banco.exists():
            return

        temporario = self.caminho_banco.with_suffix(
            ".db.restaurando"
        )

        if temporario.exists():
            temporario.unlink()

        shutil.copy2(
            backup_banco,
            temporario
        )
        os.replace(
            temporario,
            self.caminho_banco
        )

    def _resetar_banco(
        self,
        data_referencia: date
    ):
        data_iso = data_referencia.isoformat()

        with self._conectar() as conexao:
            tabelas = self._listar_tabelas(
                conexao
            )
            conexao.execute("BEGIN IMMEDIATE")

            if "exportacao_dbf_lote" in tabelas:
                lote_ids = [
                    linha["lote_id"]
                    for linha in conexao.execute(
                        """
                        SELECT lote_id
                        FROM exportacao_dbf_lote
                        WHERE data_referencia = ?
                        """,
                        (data_iso,)
                    ).fetchall()
                ]

                if (
                    lote_ids
                    and "exportacao_dbf_solicitacao"
                    in tabelas
                ):
                    marcadores = ",".join(
                        "?"
                        for _ in lote_ids
                    )
                    conexao.execute(
                        f"""
                        DELETE FROM exportacao_dbf_solicitacao
                        WHERE lote_id IN ({marcadores})
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
                colunas = self._colunas_tabela(
                    conexao,
                    "rotina_diaria"
                )
                atualizacoes: list[str] = []
                valores: list[Any] = []

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
                        valores.append(
                            valor
                        )

                if atualizacoes:
                    valores.append(
                        data_iso
                    )
                    conexao.execute(
                        f"""
                        UPDATE rotina_diaria
                        SET {", ".join(atualizacoes)}
                        WHERE data_referencia = ?
                        """,
                        valores
                    )

            conexao.commit()

    def _obter_registros_exportacao(
        self,
        conexao: sqlite3.Connection,
        data_iso: str,
        tabelas: set[str]
    ) -> dict[str, list[dict[str, Any]]]:
        resultado: dict[str, list[dict[str, Any]]] = {
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
            not lote_ids
            or "exportacao_dbf_solicitacao"
            not in tabelas
        ):
            return resultado

        marcadores = ",".join(
            "?"
            for _ in lote_ids
        )
        solicitacoes = conexao.execute(
            f"""
            SELECT *
            FROM exportacao_dbf_solicitacao
            WHERE lote_id IN ({marcadores})
            ORDER BY solicitado_em
            """,
            lote_ids
        ).fetchall()

        resultado["solicitacoes"] = [
            dict(linha)
            for linha in solicitacoes
        ]

        return resultado

    def _obter_estado_rotina(
        self,
        conexao: sqlite3.Connection,
        data_iso: str,
        tabelas: set[str]
    ) -> dict[str, Any]:
        if "rotina_diaria" not in tabelas:
            return {}

        linha = conexao.execute(
            """
            SELECT
                atualizacao_bases,
                alerta_enviado
            FROM rotina_diaria
            WHERE data_referencia = ?
            """,
            (data_iso,)
        ).fetchone()

        return (
            dict(linha)
            if linha is not None
            else {}
        )

    @staticmethod
    def _listar_tabelas(
        conexao: sqlite3.Connection
    ) -> set[str]:
        linhas = conexao.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

        return {
            str(linha[0])
            for linha in linhas
        }

    @staticmethod
    def _colunas_tabela(
        conexao: sqlite3.Connection,
        tabela: str
    ) -> set[str]:
        linhas = conexao.execute(
            f"PRAGMA table_info({tabela})"
        ).fetchall()

        return {
            str(linha[1])
            for linha in linhas
        }

    # ------------------------------------------------------------------
    # Arquivos
    # ------------------------------------------------------------------

    def _localizar_historicos(
        self,
        data_referencia: date
    ) -> list[Path]:
        candidatos = [
            self.arquivos_service.caminho_historico(
                agravo=agravo,
                data_referencia=data_referencia
            )
            for agravo in (
                ArquivosExportacaoDbfService
                .AGRAVO_DENGUE,
                ArquivosExportacaoDbfService
                .AGRAVO_CHIKUNGUNYA
            )
        ]

        nomes_legados = {
            (
                f"chikungunya_"
                f"{data_referencia.isoformat()}.zip"
            ).casefold()
        }

        raiz_historico = (
            self.arquivos_service
            .raiz_historico
        )

        if raiz_historico.exists():
            for arquivo in raiz_historico.rglob(
                "*.zip"
            ):
                if (
                    arquivo.name.casefold()
                    in nomes_legados
                ):
                    candidatos.append(
                        arquivo
                    )

        unicos: dict[str, Path] = {}

        for caminho in candidatos:
            if caminho.exists() and caminho.is_file():
                unicos[str(caminho.resolve())] = caminho

        return sorted(
            unicos.values(),
            key=lambda caminho: str(caminho).casefold()
        )

    def _localizar_temporarios(
        self,
        data_referencia: date
    ) -> list[Path]:
        raiz = (
            self.arquivos_service
            .raiz_staging
        )

        if not raiz.exists():
            return []

        padrao = (
            f"exportacao_"
            f"{data_referencia.isoformat()}_*"
        )

        return sorted(
            (
                caminho
                for caminho in raiz.glob(padrao)
                if caminho.exists()
            ),
            key=lambda caminho: caminho.name.casefold()
        )

    @staticmethod
    def _caminho_relativo_seguro(
        caminho: Path,
        raiz: Path
    ) -> Path:
        try:
            return caminho.resolve().relative_to(
                raiz.resolve()
            )
        except ValueError:
            return Path(
                caminho.name
            )

    @staticmethod
    def _mover_para_backup(
        origem: Path,
        destino: Path
    ) -> Path:
        destino.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        destino_real = destino

        if destino_real.exists():
            sufixo = datetime.now().strftime(
                "%H%M%S%f"
            )
            destino_real = destino_real.with_name(
                f"{destino_real.stem}_{sufixo}"
                f"{destino_real.suffix}"
            )

        shutil.move(
            str(origem),
            str(destino_real)
        )
        return destino_real

    @staticmethod
    def _restaurar_movimentos(
        movimentos: list[tuple[Path, Path]]
    ):
        for origem, destino in reversed(
            movimentos
        ):
            if not destino.exists():
                continue

            origem.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            if origem.exists():
                conflito = origem.with_name(
                    (
                        f"{origem.stem}_conflito_"
                        f"{datetime.now().strftime('%H%M%S%f')}"
                        f"{origem.suffix}"
                    )
                )
                shutil.move(
                    str(origem),
                    str(conflito)
                )

            shutil.move(
                str(destino),
                str(origem)
            )

    @staticmethod
    def _abrir_pasta(
        caminho: Path
    ):
        caminho = caminho.resolve()

        if sys.platform == "win32":
            os.startfile(
                str(caminho)
            )
            return

        comando = (
            ["open", str(caminho)]
            if sys.platform == "darwin"
            else ["xdg-open", str(caminho)]
        )
        subprocess.Popen(
            comando
        )
