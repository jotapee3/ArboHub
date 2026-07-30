from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


class ExportacaoDbfService:
    """
    Persiste os números e metadados operacionais das exportações DBF.

    O serviço usa o mesmo banco local do ArboHub, mas não armazena:
    - credenciais;
    - conteúdo dos arquivos DBF;
    - linhas de pacientes;
    - nomes ou outros identificadores pessoais.

    Cada execução de Dengue + Chikungunya recebe um ``lote_id``.
    Isso impede que números de execuções diferentes sejam misturados.
    """

    AGRAVO_DENGUE = "dengue"
    AGRAVO_CHIKUNGUNYA = "chikungunya"

    AGRAVOS_VALIDOS = {
        AGRAVO_DENGUE,
        AGRAVO_CHIKUNGUNYA
    }

    STATUS_SOLICITADO = "solicitado"
    STATUS_PROCESSANDO = "processando"
    STATUS_CONCLUIDO = "concluido"

    def __init__(
        self,
        caminho_banco: str | Path | None = None
    ):
        raiz_projeto = Path(__file__).resolve().parents[2]

        if caminho_banco is None:
            caminho_banco = (
                raiz_projeto
                / "data"
                / "arbohub.db"
            )

        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.criar_tabelas()

    def conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_banco
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute(
            "PRAGMA foreign_keys = ON"
        )
        return conexao

    def criar_tabelas(self):
        comando_lotes = """
            CREATE TABLE IF NOT EXISTS exportacao_dbf_lote (
                lote_id TEXT PRIMARY KEY,
                data_referencia TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
        """

        comando_solicitacoes = """
            CREATE TABLE IF NOT EXISTS exportacao_dbf_solicitacao (
                lote_id TEXT NOT NULL,
                agravo TEXT NOT NULL,
                numero_solicitacao TEXT NOT NULL,

                solicitado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'solicitado',
                quantidade_registros TEXT,
                processamento_concluido INTEGER
                    NOT NULL DEFAULT 0,
                link_disponivel INTEGER
                    NOT NULL DEFAULT 0,
                texto_link TEXT,

                PRIMARY KEY (
                    lote_id,
                    agravo
                ),

                UNIQUE (
                    numero_solicitacao
                ),

                FOREIGN KEY (
                    lote_id
                )
                REFERENCES exportacao_dbf_lote (
                    lote_id
                )
                ON DELETE CASCADE
            )
        """

        comando_indice = """
            CREATE INDEX IF NOT EXISTS
                idx_exportacao_dbf_lote_data
            ON exportacao_dbf_lote (
                data_referencia,
                criado_em
            )
        """

        with self.conectar() as conexao:
            conexao.execute(comando_lotes)
            conexao.execute(comando_solicitacoes)
            conexao.execute(comando_indice)
            conexao.commit()

    def criar_lote(
        self,
        data_referencia: date | None = None
    ) -> str:
        data_referencia = data_referencia or date.today()
        agora = datetime.now().isoformat(
            timespec="seconds"
        )
        lote_id = uuid4().hex

        with self.conectar() as conexao:
            conexao.execute(
                """
                    INSERT INTO exportacao_dbf_lote (
                        lote_id,
                        data_referencia,
                        criado_em,
                        atualizado_em
                    )
                    VALUES (?, ?, ?, ?)
                """,
                (
                    lote_id,
                    data_referencia.isoformat(),
                    agora,
                    agora
                )
            )
            conexao.commit()

        return lote_id

    def salvar_solicitacao(
        self,
        lote_id: str,
        agravo: str,
        numero_solicitacao: str
    ):
        agravo = self._validar_agravo(
            agravo
        )
        numero_solicitacao = (
            self._validar_numero_solicitacao(
                numero_solicitacao
            )
        )
        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            lote = conexao.execute(
                """
                    SELECT lote_id
                    FROM exportacao_dbf_lote
                    WHERE lote_id = ?
                """,
                (lote_id,)
            ).fetchone()

            if lote is None:
                raise ValueError(
                    "O lote informado não existe."
                )

            conexao.execute(
                """
                    INSERT INTO exportacao_dbf_solicitacao (
                        lote_id,
                        agravo,
                        numero_solicitacao,
                        solicitado_em,
                        atualizado_em,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)

                    ON CONFLICT (
                        lote_id,
                        agravo
                    )
                    DO UPDATE SET
                        numero_solicitacao =
                            excluded.numero_solicitacao,
                        solicitado_em =
                            excluded.solicitado_em,
                        atualizado_em =
                            excluded.atualizado_em,
                        status =
                            excluded.status,
                        quantidade_registros = NULL,
                        processamento_concluido = 0,
                        link_disponivel = 0,
                        texto_link = NULL
                """,
                (
                    lote_id,
                    agravo,
                    numero_solicitacao,
                    agora,
                    agora,
                    self.STATUS_SOLICITADO
                )
            )

            conexao.execute(
                """
                    UPDATE exportacao_dbf_lote
                    SET atualizado_em = ?
                    WHERE lote_id = ?
                """,
                (
                    agora,
                    lote_id
                )
            )
            conexao.commit()

    def obter_lote_parcial_do_dia(
        self,
        data_referencia: date | None = None
    ) -> dict | None:
        """
        Retorna o lote parcial mais recente do dia.

        Um lote parcial possui exatamente uma das solicitações:
        Dengue ou Chikungunya. Isso permite retomar uma execução
        interrompida sem criar novamente a solicitação que já foi
        capturada e salva.

        Lotes completos não são retornados por este método.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        with self.conectar() as conexao:
            lote = conexao.execute(
                """
                    SELECT
                        lote.lote_id,
                        lote.data_referencia,
                        lote.criado_em,
                        lote.atualizado_em
                    FROM exportacao_dbf_lote AS lote
                    WHERE
                        lote.data_referencia = ?
                        AND (
                            SELECT COUNT(
                                DISTINCT solicitacao.agravo
                            )
                            FROM exportacao_dbf_solicitacao
                                AS solicitacao
                            WHERE
                                solicitacao.lote_id =
                                    lote.lote_id
                                AND solicitacao.agravo IN (?, ?)
                        ) = 1
                    ORDER BY
                        lote.criado_em DESC,
                        lote.rowid DESC
                    LIMIT 1
                """,
                (
                    data_referencia.isoformat(),
                    self.AGRAVO_DENGUE,
                    self.AGRAVO_CHIKUNGUNYA
                )
            ).fetchone()

            if lote is None:
                return None

            solicitacoes = conexao.execute(
                """
                    SELECT *
                    FROM exportacao_dbf_solicitacao
                    WHERE lote_id = ?
                """,
                (lote["lote_id"],)
            ).fetchall()

        por_agravo = {
            linha["agravo"]: dict(linha)
            for linha in solicitacoes
        }

        return {
            "lote_id": lote["lote_id"],
            "data_referencia": lote["data_referencia"],
            "criado_em": lote["criado_em"],
            "atualizado_em": lote["atualizado_em"],
            "dengue": por_agravo.get(
                self.AGRAVO_DENGUE
            ),
            "chikungunya": por_agravo.get(
                self.AGRAVO_CHIKUNGUNYA
            )
        }

    def obter_lote_completo_do_dia(
        self,
        data_referencia: date | None = None
    ) -> dict | None:
        """
        Retorna o lote completo mais recente do dia informado.

        Isso impede que a consulta de hoje reutilize, por engano,
        os números da execução de ontem quando ainda não existe
        um par completo de Dengue e Chikungunya para hoje.
        """

        data_referencia = data_referencia or date.today()

        with self.conectar() as conexao:
            lote = conexao.execute(
                """
                    SELECT
                        lote.lote_id,
                        lote.data_referencia,
                        lote.criado_em,
                        lote.atualizado_em
                    FROM exportacao_dbf_lote AS lote
                    WHERE
                        lote.data_referencia = ?
                        AND (
                            SELECT COUNT(
                                DISTINCT solicitacao.agravo
                            )
                            FROM exportacao_dbf_solicitacao
                                AS solicitacao
                            WHERE
                                solicitacao.lote_id =
                                    lote.lote_id
                                AND solicitacao.agravo IN (?, ?)
                        ) = 2
                    ORDER BY
                        lote.criado_em DESC,
                        lote.rowid DESC
                    LIMIT 1
                """,
                (
                    data_referencia.isoformat(),
                    self.AGRAVO_DENGUE,
                    self.AGRAVO_CHIKUNGUNYA
                )
            ).fetchone()

            if lote is None:
                return None

            solicitacoes = conexao.execute(
                """
                    SELECT *
                    FROM exportacao_dbf_solicitacao
                    WHERE lote_id = ?
                """,
                (lote["lote_id"],)
            ).fetchall()

        por_agravo = {
            linha["agravo"]: dict(linha)
            for linha in solicitacoes
        }

        return {
            "lote_id": lote["lote_id"],
            "data_referencia": lote["data_referencia"],
            "criado_em": lote["criado_em"],
            "atualizado_em": lote["atualizado_em"],
            "dengue": por_agravo[
                self.AGRAVO_DENGUE
            ],
            "chikungunya": por_agravo[
                self.AGRAVO_CHIKUNGUNYA
            ]
        }

    def obter_ultimo_lote_completo(
        self
    ) -> dict | None:
        """
        Retorna o lote mais recente que possui números distintos
        para Dengue e Chikungunya.
        """

        with self.conectar() as conexao:
            lote = conexao.execute(
                """
                    SELECT
                        lote.lote_id,
                        lote.data_referencia,
                        lote.criado_em,
                        lote.atualizado_em
                    FROM exportacao_dbf_lote AS lote
                    WHERE (
                        SELECT COUNT(DISTINCT solicitacao.agravo)
                        FROM exportacao_dbf_solicitacao
                            AS solicitacao
                        WHERE
                            solicitacao.lote_id =
                                lote.lote_id
                            AND solicitacao.agravo IN (?, ?)
                    ) = 2
                    ORDER BY
                        lote.criado_em DESC,
                        lote.rowid DESC
                    LIMIT 1
                """,
                (
                    self.AGRAVO_DENGUE,
                    self.AGRAVO_CHIKUNGUNYA
                )
            ).fetchone()

            if lote is None:
                return None

            solicitacoes = conexao.execute(
                """
                    SELECT *
                    FROM exportacao_dbf_solicitacao
                    WHERE lote_id = ?
                """,
                (lote["lote_id"],)
            ).fetchall()

        por_agravo = {
            linha["agravo"]: dict(linha)
            for linha in solicitacoes
        }

        return {
            "lote_id": lote["lote_id"],
            "data_referencia": lote["data_referencia"],
            "criado_em": lote["criado_em"],
            "atualizado_em": lote["atualizado_em"],
            "dengue": por_agravo[
                self.AGRAVO_DENGUE
            ],
            "chikungunya": por_agravo[
                self.AGRAVO_CHIKUNGUNYA
            ]
        }

    def atualizar_resultado_consulta(
        self,
        lote_id: str,
        agravo: str,
        resultado: dict
    ):
        agravo = self._validar_agravo(
            agravo
        )
        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        processamento_concluido = bool(
            resultado.get(
                "processamento_concluido",
                False
            )
        )
        link_disponivel = bool(
            resultado.get(
                "link_disponivel",
                False
            )
        )

        if processamento_concluido:
            status = self.STATUS_CONCLUIDO
        elif resultado.get("encontrada", False):
            status = self.STATUS_PROCESSANDO
        else:
            status = self.STATUS_SOLICITADO

        with self.conectar() as conexao:
            resultado_update = conexao.execute(
                """
                    UPDATE exportacao_dbf_solicitacao
                    SET
                        atualizado_em = ?,
                        status = ?,
                        quantidade_registros = ?,
                        processamento_concluido = ?,
                        link_disponivel = ?,
                        texto_link = ?
                    WHERE
                        lote_id = ?
                        AND agravo = ?
                """,
                (
                    agora,
                    status,
                    str(
                        resultado.get(
                            "quantidade_registros",
                            ""
                        )
                    ),
                    int(processamento_concluido),
                    int(link_disponivel),
                    str(
                        resultado.get(
                            "texto_link",
                            ""
                        )
                    ),
                    lote_id,
                    agravo
                )
            )

            if resultado_update.rowcount == 0:
                raise ValueError(
                    "Não existe solicitação salva para "
                    f"o agravo {agravo!r} nesse lote."
                )

            conexao.execute(
                """
                    UPDATE exportacao_dbf_lote
                    SET atualizado_em = ?
                    WHERE lote_id = ?
                """,
                (
                    agora,
                    lote_id
                )
            )
            conexao.commit()

    def _validar_agravo(
        self,
        agravo: str
    ) -> str:
        agravo = str(agravo).strip().casefold()

        if agravo not in self.AGRAVOS_VALIDOS:
            raise ValueError(
                "Agravo inválido. Use dengue ou chikungunya."
            )

        return agravo

    def _validar_numero_solicitacao(
        self,
        numero_solicitacao: str
    ) -> str:
        numero_solicitacao = str(
            numero_solicitacao
        ).strip()

        if not numero_solicitacao.isdigit():
            raise ValueError(
                "O número da solicitação deve conter "
                "somente dígitos."
            )

        return numero_solicitacao