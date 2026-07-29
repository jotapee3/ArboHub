from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path


class CheckpointService:
    """
    Gerencia a rotina diária e os checkpoints de óbitos.

    A verificação geral de óbitos somente é concluída quando
    Dengue e Chikungunya estiverem concluídas.
    """

    ETAPA_OBITOS = "verificacao_obitos"
    ETAPA_BASES = "atualizacao_bases"

    AGRAVO_DENGUE = "dengue"
    AGRAVO_CHIKUNGUNYA = "chikungunya"

    STATUS_AGUARDANDO = "aguardando"
    STATUS_EXECUTANDO = "executando"
    STATUS_AGUARDANDO_CONFERENCIA = "aguardando_conferencia"
    STATUS_CONCLUIDO = "concluido"
    STATUS_ERRO = "erro"

    AGRAVOS_VALIDOS = {
        AGRAVO_DENGUE,
        AGRAVO_CHIKUNGUNYA
    }

    STATUS_VALIDOS = {
        STATUS_AGUARDANDO,
        STATUS_EXECUTANDO,
        STATUS_AGUARDANDO_CONFERENCIA,
        STATUS_CONCLUIDO,
        STATUS_ERRO
    }

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
        return conexao

    def criar_tabelas(self):
        comando_rotina = """
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

        comando_obitos = """
            CREATE TABLE IF NOT EXISTS verificacao_obitos_diaria (
                data_referencia TEXT NOT NULL,
                agravo TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'aguardando',

                iniciado_em TEXT,
                consulta_concluida_em TEXT,
                confirmado_em TEXT,
                atualizado_em TEXT,

                resultado_comparacao TEXT,
                observacao TEXT,
                responsavel TEXT,

                PRIMARY KEY (
                    data_referencia,
                    agravo
                )
            )
        """

        with self.conectar() as conexao:
            conexao.execute(comando_rotina)
            conexao.execute(comando_obitos)
            conexao.commit()

    # Compatibilidade com a versão anterior.
    def criar_tabela(self):
        self.criar_tabelas()

    def garantir_rotina_do_dia(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = data_referencia or date.today()

        with self.conectar() as conexao:
            conexao.execute(
                """
                    INSERT OR IGNORE INTO rotina_diaria (
                        data_referencia
                    )
                    VALUES (?)
                """,
                (data_referencia.isoformat(),)
            )
            conexao.commit()

        self.garantir_checkpoints_obitos_do_dia(
            data_referencia
        )

    def garantir_checkpoints_obitos_do_dia(
        self,
        data_referencia: date | None = None
    ):
        """
        Cria os registros de Dengue e Chikungunya.

        Se o checkpoint geral antigo já estava concluído, os
        dois registros novos também são marcados como concluídos.
        """

        data_referencia = data_referencia or date.today()
        data_iso = data_referencia.isoformat()
        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            for agravo in sorted(self.AGRAVOS_VALIDOS):
                conexao.execute(
                    """
                        INSERT OR IGNORE INTO
                            verificacao_obitos_diaria (
                                data_referencia,
                                agravo,
                                status,
                                atualizado_em
                            )
                        VALUES (?, ?, ?, ?)
                    """,
                    (
                        data_iso,
                        agravo,
                        self.STATUS_AGUARDANDO,
                        agora
                    )
                )

            legado = conexao.execute(
                """
                    SELECT
                        verificacao_obitos,
                        verificacao_obitos_em
                    FROM rotina_diaria
                    WHERE data_referencia = ?
                """,
                (data_iso,)
            ).fetchone()

            if (
                legado is not None
                and bool(legado["verificacao_obitos"])
            ):
                horario = (
                    legado["verificacao_obitos_em"]
                    or agora
                )

                conexao.execute(
                    """
                        UPDATE verificacao_obitos_diaria
                        SET
                            status = ?,
                            confirmado_em = COALESCE(
                                confirmado_em,
                                ?
                            ),
                            atualizado_em = ?
                        WHERE
                            data_referencia = ?
                            AND status != ?
                    """,
                    (
                        self.STATUS_CONCLUIDO,
                        horario,
                        agora,
                        data_iso,
                        self.STATUS_CONCLUIDO
                    )
                )

            conexao.commit()

    def obter_rotina(
        self,
        data_referencia: date | None = None
    ) -> dict:
        data_referencia = data_referencia or date.today()
        self.garantir_rotina_do_dia(
            data_referencia
        )

        with self.conectar() as conexao:
            resultado = conexao.execute(
                """
                    SELECT *
                    FROM rotina_diaria
                    WHERE data_referencia = ?
                """,
                (data_referencia.isoformat(),)
            ).fetchone()

        checkpoints = self.obter_checkpoints_obitos(
            data_referencia
        )

        verificacao_obitos = all(
            item["status"] == self.STATUS_CONCLUIDO
            for item in checkpoints.values()
        )

        horarios = [
            item["confirmado_em"]
            for item in checkpoints.values()
            if item["confirmado_em"]
        ]

        horario_obitos = (
            max(horarios)
            if verificacao_obitos and horarios
            else resultado["verificacao_obitos_em"]
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
                horario_obitos,

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
                resultado["alerta_enviado_em"],

            "checkpoints_obitos":
                checkpoints
        }

    def obter_checkpoints_obitos(
        self,
        data_referencia: date | None = None
    ) -> dict[str, dict]:
        data_referencia = data_referencia or date.today()
        data_iso = data_referencia.isoformat()

        # Garante a linha principal sem criar recursão.
        with self.conectar() as conexao:
            conexao.execute(
                """
                    INSERT OR IGNORE INTO rotina_diaria (
                        data_referencia
                    )
                    VALUES (?)
                """,
                (data_iso,)
            )
            conexao.commit()

        self.garantir_checkpoints_obitos_do_dia(
            data_referencia
        )

        with self.conectar() as conexao:
            resultados = conexao.execute(
                """
                    SELECT *
                    FROM verificacao_obitos_diaria
                    WHERE data_referencia = ?
                    ORDER BY agravo
                """,
                (data_iso,)
            ).fetchall()

        return {
            resultado["agravo"]: dict(resultado)
            for resultado in resultados
        }

    def obter_checkpoint_obito(
        self,
        agravo: str,
        data_referencia: date | None = None
    ) -> dict:
        agravo = self._validar_agravo(agravo)

        return self.obter_checkpoints_obitos(
            data_referencia
        )[agravo]

    def atualizar_status_obito(
        self,
        agravo: str,
        status: str,
        data_referencia: date | None = None
    ):
        agravo = self._validar_agravo(agravo)
        status = self._validar_status(status)
        data_referencia = data_referencia or date.today()

        self.garantir_rotina_do_dia(
            data_referencia
        )

        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        colunas_horario = {
            self.STATUS_EXECUTANDO: "iniciado_em",
            self.STATUS_AGUARDANDO_CONFERENCIA:
                "consulta_concluida_em",
            self.STATUS_CONCLUIDO: "confirmado_em"
        }

        coluna_horario = colunas_horario.get(status)

        if coluna_horario:
            comando = f"""
                UPDATE verificacao_obitos_diaria
                SET
                    status = ?,
                    {coluna_horario} = ?,
                    atualizado_em = ?
                WHERE
                    data_referencia = ?
                    AND agravo = ?
            """
            parametros = (
                status,
                agora,
                agora,
                data_referencia.isoformat(),
                agravo
            )
        else:
            comando = """
                UPDATE verificacao_obitos_diaria
                SET
                    status = ?,
                    atualizado_em = ?
                WHERE
                    data_referencia = ?
                    AND agravo = ?
            """
            parametros = (
                status,
                agora,
                data_referencia.isoformat(),
                agravo
            )

        with self.conectar() as conexao:
            conexao.execute(
                comando,
                parametros
            )
            conexao.commit()

        self._sincronizar_verificacao_obitos_geral(
            data_referencia
        )

    def marcar_obito_iniciado(
        self,
        agravo: str,
        data_referencia: date | None = None
    ):
        self.atualizar_status_obito(
            agravo,
            self.STATUS_EXECUTANDO,
            data_referencia
        )

    def marcar_obito_aguardando_conferencia(
        self,
        agravo: str,
        data_referencia: date | None = None
    ):
        self.atualizar_status_obito(
            agravo,
            self.STATUS_AGUARDANDO_CONFERENCIA,
            data_referencia
        )

    def marcar_obito_concluido(
        self,
        agravo: str,
        resultado_comparacao: str | None = None,
        observacao: str | None = None,
        responsavel: str | None = None,
        data_referencia: date | None = None
    ):
        agravo = self._validar_agravo(agravo)
        data_referencia = data_referencia or date.today()

        self.atualizar_status_obito(
            agravo,
            self.STATUS_CONCLUIDO,
            data_referencia
        )

        if any(
            valor is not None
            for valor in (
                resultado_comparacao,
                observacao,
                responsavel
            )
        ):
            self.salvar_relatorio_obito(
                agravo=agravo,
                resultado_comparacao=resultado_comparacao,
                observacao=observacao,
                responsavel=responsavel,
                data_referencia=data_referencia
            )

    def marcar_obito_erro(
        self,
        agravo: str,
        data_referencia: date | None = None
    ):
        self.atualizar_status_obito(
            agravo,
            self.STATUS_ERRO,
            data_referencia
        )

    def salvar_relatorio_obito(
        self,
        agravo: str,
        resultado_comparacao: str | None,
        observacao: str | None,
        responsavel: str | None = None,
        data_referencia: date | None = None
    ):
        """
        Guarda a base para o relatório futuro.

        Não deve receber nomes de pacientes ou outros dados
        identificáveis.
        """

        agravo = self._validar_agravo(agravo)
        data_referencia = data_referencia or date.today()
        self.garantir_rotina_do_dia(
            data_referencia
        )

        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE verificacao_obitos_diaria
                    SET
                        resultado_comparacao = ?,
                        observacao = ?,
                        responsavel = ?,
                        atualizado_em = ?
                    WHERE
                        data_referencia = ?
                        AND agravo = ?
                """,
                (
                    resultado_comparacao,
                    observacao,
                    responsavel,
                    agora,
                    data_referencia.isoformat(),
                    agravo
                )
            )
            conexao.commit()

    def marcar_verificacao_obitos(
        self,
        data_referencia: date | None = None
    ):
        """
        Compatibilidade com a API antiga.
        """

        data_referencia = data_referencia or date.today()

        for agravo in (
            self.AGRAVO_DENGUE,
            self.AGRAVO_CHIKUNGUNYA
        ):
            self.marcar_obito_concluido(
                agravo,
                data_referencia=data_referencia
            )

    def marcar_atualizacao_bases(
        self,
        data_referencia: date | None = None
    ):
        self.marcar_etapa(
            self.ETAPA_BASES,
            data_referencia
        )

    def marcar_etapa(
        self,
        etapa: str,
        data_referencia: date | None = None
    ):
        data_referencia = data_referencia or date.today()

        if etapa == self.ETAPA_OBITOS:
            self.marcar_verificacao_obitos(
                data_referencia
            )
            return

        if etapa != self.ETAPA_BASES:
            raise ValueError(
                f"Etapa inválida: {etapa}"
            )

        self.garantir_rotina_do_dia(
            data_referencia
        )

        horario = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        atualizacao_bases = 1,
                        atualizacao_bases_em = ?
                    WHERE data_referencia = ?
                """,
                (
                    horario,
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def _sincronizar_verificacao_obitos_geral(
        self,
        data_referencia: date
    ):
        checkpoints = self.obter_checkpoints_obitos(
            data_referencia
        )

        concluido = all(
            item["status"] == self.STATUS_CONCLUIDO
            for item in checkpoints.values()
        )

        horarios = [
            item["confirmado_em"]
            for item in checkpoints.values()
            if item["confirmado_em"]
        ]

        horario = (
            max(horarios)
            if concluido and horarios
            else None
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        verificacao_obitos = ?,
                        verificacao_obitos_em = ?
                    WHERE data_referencia = ?
                """,
                (
                    int(concluido),
                    horario,
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def marcar_alerta_enviado(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = data_referencia or date.today()
        self.garantir_rotina_do_dia(
            data_referencia
        )

        horario = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        alerta_enviado = 1,
                        alerta_enviado_em = ?
                    WHERE data_referencia = ?
                """,
                (
                    horario,
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def resetar_verificacao_obitos(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = data_referencia or date.today()
        self.garantir_rotina_do_dia(
            data_referencia
        )

        agora = datetime.now().isoformat(
            timespec="seconds"
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE verificacao_obitos_diaria
                    SET
                        status = ?,
                        iniciado_em = NULL,
                        consulta_concluida_em = NULL,
                        confirmado_em = NULL,
                        atualizado_em = ?,
                        resultado_comparacao = NULL,
                        observacao = NULL,
                        responsavel = NULL
                    WHERE data_referencia = ?
                """,
                (
                    self.STATUS_AGUARDANDO,
                    agora,
                    data_referencia.isoformat()
                )
            )

            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        verificacao_obitos = 0,
                        verificacao_obitos_em = NULL
                    WHERE data_referencia = ?
                """,
                (data_referencia.isoformat(),)
            )
            conexao.commit()

    def resetar_rotina(
        self,
        data_referencia: date | None = None
    ):
        data_referencia = data_referencia or date.today()
        self.garantir_rotina_do_dia(
            data_referencia
        )

        self.resetar_verificacao_obitos(
            data_referencia
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        atualizacao_bases = 0,
                        atualizacao_bases_em = NULL,
                        alerta_enviado = 0,
                        alerta_enviado_em = NULL
                    WHERE data_referencia = ?
                """,
                (data_referencia.isoformat(),)
            )
            conexao.commit()

    def listar_relatorios_obitos(
        self,
        agravo: str | None = None,
        resultado_comparacao: str | None = None,
        limite: int = 100
    ) -> list[dict]:
        """
        Retorna o histórico de conferências de óbitos.

        A consulta utiliza somente os dados registrados pelo
        ArboHub durante a conferência humana. Ela não acessa
        nem retorna linhas de pacientes do SINAN.
        """

        if limite < 1:
            raise ValueError(
                "O limite precisa ser maior que zero."
            )

        limite = min(limite, 500)

        filtros = [
            "status = ?"
        ]
        parametros: list[str | int] = [
            self.STATUS_CONCLUIDO
        ]

        if agravo is not None:
            agravo = self._validar_agravo(agravo)
            filtros.append("agravo = ?")
            parametros.append(agravo)

        resultados_validos = {
            "manteve_igual",
            "mudou"
        }

        if resultado_comparacao is not None:
            resultado_normalizado = (
                resultado_comparacao.strip().casefold()
            )

            if resultado_normalizado not in resultados_validos:
                raise ValueError(
                    "Resultado inválido. Use 'manteve_igual' "
                    "ou 'mudou'."
                )

            filtros.append(
                "resultado_comparacao = ?"
            )
            parametros.append(
                resultado_normalizado
            )

        parametros.append(limite)

        comando = f"""
            SELECT
                data_referencia,
                agravo,
                status,
                iniciado_em,
                consulta_concluida_em,
                confirmado_em,
                resultado_comparacao,
                observacao,
                responsavel
            FROM verificacao_obitos_diaria
            WHERE {' AND '.join(filtros)}
            ORDER BY
                data_referencia DESC,
                confirmado_em DESC,
                agravo ASC
            LIMIT ?
        """

        with self.conectar() as conexao:
            resultados = conexao.execute(
                comando,
                parametros
            ).fetchall()

        return [
            dict(resultado)
            for resultado in resultados
        ]

    def _validar_agravo(
        self,
        agravo: str
    ) -> str:
        normalizado = agravo.strip().casefold()

        aliases = {
            "dengue": self.AGRAVO_DENGUE,
            "chikungunya": self.AGRAVO_CHIKUNGUNYA,
            "chiku": self.AGRAVO_CHIKUNGUNYA
        }

        if normalizado not in aliases:
            raise ValueError(
                "Agravo inválido. Use Dengue ou Chikungunya."
            )

        return aliases[normalizado]

    def _validar_status(
        self,
        status: str
    ) -> str:
        if status not in self.STATUS_VALIDOS:
            raise ValueError(
                f"Status inválido: {status}"
            )

        return status