from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


class CheckpointService:

    ETAPA_OBITOS = "verificacao_obitos"
    ETAPA_BASES = "atualizacao_bases"

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

        self.criar_tabela()

    def conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_banco
        )

        conexao.row_factory = sqlite3.Row

        return conexao

    def criar_tabela(self):
        comando = """
            CREATE TABLE IF NOT EXISTS rotina_diaria (
                data_referencia TEXT PRIMARY KEY,

                verificacao_obitos INTEGER
                    NOT NULL DEFAULT 0,

                verificacao_obitos_em TEXT,

                atualizacao_bases INTEGER
                    NOT NULL DEFAULT 0,

                atualizacao_bases_em TEXT,

                alerta_enviado INTEGER
                    NOT NULL DEFAULT 0,

                alerta_enviado_em TEXT
            )
        """

        with self.conectar() as conexao:
            conexao.execute(comando)
            conexao.commit()

    def garantir_rotina_do_dia(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = (
            data_referencia or date.today()
        )

        comando = """
            INSERT OR IGNORE INTO rotina_diaria (
                data_referencia
            )
            VALUES (?)
        """

        with self.conectar() as conexao:
            conexao.execute(
                comando,
                (data_referencia.isoformat(),)
            )
            conexao.commit()

    def obter_rotina(
        self,
        data_referencia: date | None = None
    ) -> dict:
        data_referencia = (
            data_referencia or date.today()
        )

        self.garantir_rotina_do_dia(
            data_referencia
        )

        comando = """
            SELECT *
            FROM rotina_diaria
            WHERE data_referencia = ?
        """

        with self.conectar() as conexao:
            resultado = conexao.execute(
                comando,
                (data_referencia.isoformat(),)
            ).fetchone()

        verificacao_obitos = bool(
            resultado["verificacao_obitos"]
        )

        atualizacao_bases = bool(
            resultado["atualizacao_bases"]
        )

        return {
            "data_referencia":
                resultado["data_referencia"],

            "verificacao_obitos":
                verificacao_obitos,

            "verificacao_obitos_em":
                resultado["verificacao_obitos_em"],

            "atualizacao_bases":
                atualizacao_bases,

            "atualizacao_bases_em":
                resultado["atualizacao_bases_em"],

            "rotina_concluida":
                verificacao_obitos
                and atualizacao_bases,

            "alerta_enviado":
                bool(resultado["alerta_enviado"]),

            "alerta_enviado_em":
                resultado["alerta_enviado_em"]
        }

    def marcar_verificacao_obitos(
        self,
        data_referencia: date | None = None
    ):
        self.marcar_etapa(
            etapa=self.ETAPA_OBITOS,
            data_referencia=data_referencia
        )

    def marcar_atualizacao_bases(
        self,
        data_referencia: date | None = None
    ):
        self.marcar_etapa(
            etapa=self.ETAPA_BASES,
            data_referencia=data_referencia
        )

    def marcar_etapa(
        self,
        etapa: str,
        data_referencia: date | None = None
    ):
        data_referencia = (
            data_referencia or date.today()
        )

        self.garantir_rotina_do_dia(
            data_referencia
        )

        colunas = {
            self.ETAPA_OBITOS: (
                "verificacao_obitos",
                "verificacao_obitos_em"
            ),
            self.ETAPA_BASES: (
                "atualizacao_bases",
                "atualizacao_bases_em"
            )
        }

        if etapa not in colunas:
            raise ValueError(
                f"Etapa inválida: {etapa}"
            )

        coluna_estado, coluna_horario = (
            colunas[etapa]
        )

        horario_atual = datetime.now().isoformat(
            timespec="seconds"
        )

        comando = f"""
            UPDATE rotina_diaria
            SET
                {coluna_estado} = 1,
                {coluna_horario} = ?
            WHERE data_referencia = ?
        """

        with self.conectar() as conexao:
            conexao.execute(
                comando,
                (
                    horario_atual,
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def marcar_alerta_enviado(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = (
            data_referencia or date.today()
        )

        self.garantir_rotina_do_dia(
            data_referencia
        )

        horario_atual = datetime.now().isoformat(
            timespec="seconds"
        )

        comando = """
            UPDATE rotina_diaria
            SET
                alerta_enviado = 1,
                alerta_enviado_em = ?
            WHERE data_referencia = ?
        """

        with self.conectar() as conexao:
            conexao.execute(
                comando,
                (
                    horario_atual,
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def resetar_rotina(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = (
            data_referencia or date.today()
        )

        self.garantir_rotina_do_dia(
            data_referencia
        )

        comando = """
            UPDATE rotina_diaria
            SET
                verificacao_obitos = 0,
                verificacao_obitos_em = NULL,
                atualizacao_bases = 0,
                atualizacao_bases_em = NULL,
                alerta_enviado = 0,
                alerta_enviado_em = NULL
            WHERE data_referencia = ?
        """

        with self.conectar() as conexao:
            conexao.execute(
                comando,
                (data_referencia.isoformat(),)
            )
            conexao.commit()