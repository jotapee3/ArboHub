from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

from app.core.database import (
    conectar_sqlite,
    resolver_caminho_banco,
)


class DashboardService:
    """
    Consolida os dados operacionais exibidos na aba Início.

    Regras da rotina:
    - segunda-feira: SINAN + GAL;
    - terça a sexta-feira: somente SINAN;
    - sábado e domingo: nenhuma rotina obrigatória.

    SINAN é considerado concluído somente quando:
    - a verificação de óbitos foi concluída; e
    - a atualização das bases foi concluída.

    O serviço lê apenas metadados operacionais do SQLite. Nenhum
    registro de pacientes ou conteúdo dos DBFs é acessado.
    """

    ETAPA_GAL = "atualizacao_gal"

    DIAS_SEMANA = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo"
    )

    MESES = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro"
    )

    MESES_CURTOS = (
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
        "Set",
        "Out",
        "Nov",
        "Dez"
    )

    def __init__(
        self,
        caminho_banco: str | Path | None = None
    ):
        self.caminho_banco = resolver_caminho_banco(
            caminho_banco
        )

        self._garantir_estrutura()

    def conectar(self):
        return conectar_sqlite(
            self.caminho_banco
        )

    # ------------------------------------------------------------------
    # Estrutura e compatibilidade
    # ------------------------------------------------------------------

    def _garantir_estrutura(self):
        """
        Mantém compatibilidade com o banco já utilizado pelo SINAN.

        A coluna de GAL é adicionada por migração segura, sem apagar
        ou recriar a tabela existente.
        """

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

            colunas = {
                linha["name"]
                for linha in conexao.execute(
                    "PRAGMA table_info(rotina_diaria)"
                ).fetchall()
            }

            if "atualizacao_gal" not in colunas:
                conexao.execute(
                    """
                        ALTER TABLE rotina_diaria
                        ADD COLUMN atualizacao_gal INTEGER
                        NOT NULL DEFAULT 0
                    """
                )

            if "atualizacao_gal_em" not in colunas:
                conexao.execute(
                    """
                        ALTER TABLE rotina_diaria
                        ADD COLUMN atualizacao_gal_em TEXT
                    """
                )

            if "atualizacao_gal_data_inicio" not in colunas:
                conexao.execute(
                    """
                        ALTER TABLE rotina_diaria
                        ADD COLUMN atualizacao_gal_data_inicio TEXT
                    """
                )

            if "atualizacao_gal_data_fim" not in colunas:
                conexao.execute(
                    """
                        ALTER TABLE rotina_diaria
                        ADD COLUMN atualizacao_gal_data_fim TEXT
                    """
                )

            conexao.commit()

    def marcar_gal_concluido(
        self,
        data_referencia: date | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None
    ):
        """
        Registra a conclusão e o período efetivamente usado no GAL.

        As datas são opcionais para manter compatibilidade com
        registros e integrações anteriores.
        """

        if (data_inicio is None) != (data_fim is None):
            raise ValueError(
                "Informe juntas as datas inicial e final do GAL."
            )

        if (
            data_inicio is not None
            and data_fim is not None
            and data_inicio > data_fim
        ):
            raise ValueError(
                "A data inicial do GAL não pode superar a final."
            )

        data_referencia = (
            data_referencia
            or date.today()
        )

        self._garantir_linha(
            data_referencia
        )

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        atualizacao_gal = 1,
                        atualizacao_gal_em = ?,
                        atualizacao_gal_data_inicio = ?,
                        atualizacao_gal_data_fim = ?
                    WHERE data_referencia = ?
                """,
                (
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    (
                        data_inicio.isoformat()
                        if data_inicio is not None
                        else None
                    ),
                    (
                        data_fim.isoformat()
                        if data_fim is not None
                        else None
                    ),
                    data_referencia.isoformat()
                )
            )
            conexao.commit()

    def resetar_gal(
        self,
        data_referencia: date | None = None
    ):
        """
        Reseta somente o checkpoint visual do GAL no dia informado.

        Arquivos do histórico, Banco_Atual, TesteSORO e checkpoints
        do SINAN permanecem intactos.
        """

        data_referencia = data_referencia or date.today()
        self._garantir_linha(data_referencia)

        with self.conectar() as conexao:
            conexao.execute(
                """
                    UPDATE rotina_diaria
                    SET
                        atualizacao_gal = 0,
                        atualizacao_gal_em = NULL,
                        atualizacao_gal_data_inicio = NULL,
                        atualizacao_gal_data_fim = NULL
                    WHERE data_referencia = ?
                """,
                (data_referencia.isoformat(),)
            )
            conexao.commit()

    def _garantir_linha(
        self,
        data_referencia: date
    ):
        with self.conectar() as conexao:
            conexao.execute(
                """
                    INSERT OR IGNORE INTO rotina_diaria (
                        data_referencia
                    )
                    VALUES (?)
                """,
                (
                    data_referencia.isoformat(),
                )
            )
            conexao.commit()

    # ------------------------------------------------------------------
    # Regras da rotina
    # ------------------------------------------------------------------

    def tarefas_programadas(
        self,
        data_referencia: date
    ) -> tuple[str, ...]:
        dia_semana = data_referencia.weekday()

        if dia_semana == 0:
            return (
                "sinan",
                "gal"
            )

        if 1 <= dia_semana <= 4:
            return (
                "sinan",
            )

        return ()

    def obter_resumo_dashboard(
        self,
        data_referencia: date | None = None
    ) -> dict[str, object]:
        hoje = (
            data_referencia
            or date.today()
        )

        rotina_hoje = self.obter_estado_dia(
            hoje
        )
        calendario = self.obter_calendario_ano(
            hoje.year,
            hoje=hoje
        )
        resumo_mes = self.obter_resumo_mes(
            ano=hoje.year,
            mes=hoje.month,
            hoje=hoje
        )
        sequencia = self.obter_sequencia_atual(
            hoje
        )
        atividades = self.obter_atividades_recentes(
            limite=6,
            limite_dias=3
        )
        grupos_atividades = self.agrupar_atividades_por_dia(
            atividades,
            hoje=hoje
        )

        return {
            "hoje": rotina_hoje,
            "calendario": calendario,
            "resumo_mes": resumo_mes,
            "sequencia_atual": sequencia,
            "atividades_recentes": atividades,
            "grupos_atividades_recentes": grupos_atividades,
            "saudacao": self._saudacao(),
            "data_formatada": self.formatar_data_extenso(
                hoje
            )
        }

    def obter_estado_dia(
        self,
        data_referencia: date
    ) -> dict[str, object]:
        tarefas = self.tarefas_programadas(
            data_referencia
        )
        registro = self._obter_registro(
            data_referencia
        )

        verificacao_obitos = bool(
            registro.get(
                "verificacao_obitos",
                0
            )
        )
        atualizacao_bases = bool(
            registro.get(
                "atualizacao_bases",
                0
            )
        )
        atualizacao_gal = bool(
            registro.get(
                "atualizacao_gal",
                0
            )
        )

        sinan_concluido = (
            verificacao_obitos
            and atualizacao_bases
        )

        concluidas = {
            "sinan": sinan_concluido,
            "gal": atualizacao_gal
        }

        quantidade_programada = len(
            tarefas
        )
        quantidade_concluida = sum(
            1
            for tarefa in tarefas
            if concluidas[tarefa]
        )

        houve_atividade = (
            verificacao_obitos
            or atualizacao_bases
            or atualizacao_gal
        )

        if not tarefas:
            estado = "nao_programado"

        elif quantidade_concluida == quantidade_programada:
            estado = "concluido"

        elif houve_atividade:
            estado = "parcial"

        elif data_referencia < date.today():
            estado = "atrasado"

        else:
            estado = "pendente"

        return {
            "data": data_referencia,
            "tarefas_programadas": tarefas,
            "estado": estado,
            "quantidade_programada":
                quantidade_programada,
            "quantidade_concluida":
                quantidade_concluida,
            "sinan": {
                "programado": "sinan" in tarefas,
                "concluido": sinan_concluido,
                "verificacao_obitos":
                    verificacao_obitos,
                "verificacao_obitos_em":
                    registro.get(
                        "verificacao_obitos_em"
                    ),
                "atualizacao_bases":
                    atualizacao_bases,
                "atualizacao_bases_em":
                    registro.get(
                        "atualizacao_bases_em"
                    )
            },
            "gal": {
                "programado": "gal" in tarefas,
                "concluido": atualizacao_gal,
                "atualizacao_em":
                    registro.get(
                        "atualizacao_gal_em"
                    ),
                "data_inicio": self._converter_data_iso(
                    registro.get(
                        "atualizacao_gal_data_inicio"
                    )
                ),
                "data_fim": self._converter_data_iso(
                    registro.get(
                        "atualizacao_gal_data_fim"
                    )
                )
            }
        }

    # ------------------------------------------------------------------
    # Frequência e calendário
    # ------------------------------------------------------------------

    def obter_calendario_ano(
        self,
        ano: int,
        hoje: date | None = None
    ) -> dict[str, object]:
        hoje = hoje or date.today()

        inicio = date(
            ano,
            1,
            1
        )
        fim = date(
            ano,
            12,
            31
        )
        primeira_data_monitorada = (
            self._primeira_data_monitorada()
        )

        registros = self._obter_registros_periodo(
            inicio,
            fim
        )

        dias = []
        cursor = inicio

        while cursor <= fim:
            if (
                primeira_data_monitorada is None
                or cursor < primeira_data_monitorada
            ):
                estado = "nao_monitorado"
                nivel = 0
            elif cursor > hoje:
                estado = "futuro"
                nivel = 0
            else:
                estado_dia = self._montar_estado_com_registro(
                    cursor,
                    registros.get(
                        cursor.isoformat(),
                        {}
                    ),
                    hoje=hoje
                )
                estado = estado_dia["estado"]
                nivel = self._nivel_calendario(
                    estado_dia
                )

            dias.append(
                {
                    "data": cursor,
                    "estado": estado,
                    "nivel": nivel,
                    "programado": bool(
                        self.tarefas_programadas(
                            cursor
                        )
                    )
                }
            )
            cursor += timedelta(days=1)

        programados_passados = [
            item
            for item in dias
            if (
                item["programado"]
                and item["data"] <= hoje
            )
        ]
        concluidos = sum(
            1
            for item in programados_passados
            if item["estado"] == "concluido"
        )

        return {
            "ano": ano,
            "dias": dias,
            "contribuicoes": concluidos,
            "programados":
                len(programados_passados)
        }

    def obter_resumo_mes(
        self,
        ano: int,
        mes: int,
        hoje: date | None = None
    ) -> dict[str, object]:
        hoje = hoje or date.today()

        ultimo_dia = monthrange(
            ano,
            mes
        )[1]

        inicio = date(
            ano,
            mes,
            1
        )
        fim = date(
            ano,
            mes,
            ultimo_dia
        )
        primeira_data_monitorada = (
            self._primeira_data_monitorada()
        )

        registros = self._obter_registros_periodo(
            inicio,
            fim
        )

        programados = 0
        concluidos = 0
        parciais = 0
        pendentes = 0

        cursor = inicio

        while cursor <= fim:
            if (
                primeira_data_monitorada is None
                or cursor < primeira_data_monitorada
                or cursor > hoje
            ):
                cursor += timedelta(days=1)
                continue

            tarefas = self.tarefas_programadas(
                cursor
            )

            if not tarefas:
                cursor += timedelta(days=1)
                continue

            programados += 1

            estado = self._montar_estado_com_registro(
                cursor,
                registros.get(
                    cursor.isoformat(),
                    {}
                ),
                hoje=hoje
            )["estado"]

            if estado == "concluido":
                concluidos += 1
            elif estado == "parcial":
                parciais += 1
            else:
                pendentes += 1

            cursor += timedelta(days=1)

        frequencia = (
            int(
                round(
                    concluidos
                    / programados
                    * 100
                )
            )
            if programados
            else 100
        )

        return {
            "ano": ano,
            "mes": mes,
            "nome_mes": self.MESES[
                mes - 1
            ],
            "programados": programados,
            "concluidos": concluidos,
            "parciais": parciais,
            "pendentes": pendentes,
            "frequencia": frequencia
        }

    def obter_sequencia_atual(
        self,
        hoje: date | None = None
    ) -> int:
        hoje = hoje or date.today()
        cursor = hoje

        estado_hoje = self.obter_estado_dia(
            hoje
        )

        if (
            estado_hoje["tarefas_programadas"]
            and estado_hoje["estado"] != "concluido"
        ):
            cursor -= timedelta(days=1)

        sequencia = 0

        while True:
            tarefas = self.tarefas_programadas(
                cursor
            )

            if not tarefas:
                cursor -= timedelta(days=1)
                continue

            estado = self.obter_estado_dia(
                cursor
            )

            if estado["estado"] != "concluido":
                break

            sequencia += 1
            cursor -= timedelta(days=1)

        return sequencia

    def _nivel_calendario(
        self,
        estado_dia: dict[str, object]
    ) -> int:
        if not estado_dia[
            "tarefas_programadas"
        ]:
            return 0

        if estado_dia["estado"] == "concluido":
            return 4

        if estado_dia["estado"] == "parcial":
            return 2

        return 1

    # ------------------------------------------------------------------
    # Atividade recente
    # ------------------------------------------------------------------

    def obter_atividades_recentes(
        self,
        limite: int = 6,
        limite_dias: int = 3
    ) -> list[dict[str, object]]:
        if limite <= 0 or limite_dias <= 0:
            return []

        with self.conectar() as conexao:
            linhas = conexao.execute(
                """
                    SELECT *
                    FROM rotina_diaria
                    ORDER BY data_referencia DESC
                    LIMIT 45
                """
            ).fetchall()

        atividades = []

        for linha in linhas:
            registro = dict(linha)
            data_referencia = date.fromisoformat(
                registro["data_referencia"]
            )

            candidatos = (
                (
                    registro.get(
                        "verificacao_obitos_em"
                    ),
                    "Consulta de óbitos concluída",
                    "sinan"
                ),
                (
                    registro.get(
                        "atualizacao_bases_em"
                    ),
                    "Bases do SINAN atualizadas",
                    "sinan"
                ),
                (
                    registro.get(
                        "atualizacao_gal_em"
                    ),
                    "Banco do GAL atualizado",
                    "gal"
                )
            )

            for horario_iso, titulo, modulo in candidatos:
                if not horario_iso:
                    continue

                try:
                    horario = datetime.fromisoformat(
                        horario_iso
                    )
                except ValueError:
                    continue

                atividades.append(
                    {
                        "titulo": titulo,
                        "modulo": modulo,
                        "horario": horario,
                        "data_referencia":
                            data_referencia
                    }
                )

        atividades.sort(
            key=lambda item: item["horario"],
            reverse=True
        )

        selecionadas = []
        datas_incluidas: set[date] = set()

        for atividade in atividades:
            data_referencia = atividade["data_referencia"]

            if data_referencia not in datas_incluidas:
                if len(datas_incluidas) >= limite_dias:
                    break
                datas_incluidas.add(data_referencia)

            selecionadas.append(atividade)
            if len(selecionadas) >= limite:
                break

        return selecionadas

    @classmethod
    def agrupar_atividades_por_dia(
        cls,
        atividades: list[dict[str, object]],
        hoje: date | None = None
    ) -> list[dict[str, object]]:
        """Agrupa eventos operacionais já ordenados por horário."""

        hoje = hoje or date.today()
        grupos: list[dict[str, object]] = []
        grupos_por_data: dict[date, dict[str, object]] = {}

        for atividade in atividades:
            data_referencia = atividade.get("data_referencia")
            if not isinstance(data_referencia, date):
                continue

            grupo = grupos_por_data.get(data_referencia)
            if grupo is None:
                grupo = {
                    "data": data_referencia,
                    "rotulo": cls._rotulo_data_atividade(
                        data_referencia,
                        hoje
                    ),
                    "atividades": []
                }
                grupos_por_data[data_referencia] = grupo
                grupos.append(grupo)

            grupo["atividades"].append(atividade)

        for grupo in grupos:
            grupo["quantidade"] = len(grupo["atividades"])

        return grupos

    @classmethod
    def _rotulo_data_atividade(
        cls,
        data_referencia: date,
        hoje: date
    ) -> str:
        diferenca = (hoje - data_referencia).days
        if diferenca == 0:
            return "Hoje"
        if diferenca == 1:
            return "Ontem"

        return (
            f"{data_referencia.day} de "
            f"{cls.MESES[data_referencia.month - 1]}"
        )

    @staticmethod
    def _converter_data_iso(valor: object) -> date | None:
        if not isinstance(valor, str) or not valor:
            return None

        try:
            return date.fromisoformat(valor)
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Consultas internas
    # ------------------------------------------------------------------

    def _primeira_data_monitorada(
        self
    ) -> date | None:
        """
        Evita considerar como falha os dias anteriores ao início
        efetivo do uso do ArboHub.
        """

        with self.conectar() as conexao:
            linha = conexao.execute(
                """
                    SELECT MIN(data_referencia) AS primeira_data
                    FROM rotina_diaria
                    WHERE
                        verificacao_obitos = 1
                        OR atualizacao_bases = 1
                        OR atualizacao_gal = 1
                        OR verificacao_obitos_em IS NOT NULL
                        OR atualizacao_bases_em IS NOT NULL
                        OR atualizacao_gal_em IS NOT NULL
                """
            ).fetchone()

        valor = (
            linha["primeira_data"]
            if linha is not None
            else None
        )

        return (
            date.fromisoformat(valor)
            if valor
            else None
        )

    def _obter_registro(
        self,
        data_referencia: date
    ) -> dict[str, object]:
        with self.conectar() as conexao:
            linha = conexao.execute(
                """
                    SELECT *
                    FROM rotina_diaria
                    WHERE data_referencia = ?
                """,
                (
                    data_referencia.isoformat(),
                )
            ).fetchone()

        return (
            dict(linha)
            if linha is not None
            else {}
        )

    def _obter_registros_periodo(
        self,
        inicio: date,
        fim: date
    ) -> dict[str, dict[str, object]]:
        with self.conectar() as conexao:
            linhas = conexao.execute(
                """
                    SELECT *
                    FROM rotina_diaria
                    WHERE data_referencia
                        BETWEEN ? AND ?
                """,
                (
                    inicio.isoformat(),
                    fim.isoformat()
                )
            ).fetchall()

        return {
            linha["data_referencia"]:
                dict(linha)
            for linha in linhas
        }

    def _montar_estado_com_registro(
        self,
        data_referencia: date,
        registro: dict[str, object],
        hoje: date
    ) -> dict[str, object]:
        tarefas = self.tarefas_programadas(
            data_referencia
        )

        verificacao = bool(
            registro.get(
                "verificacao_obitos",
                0
            )
        )
        bases = bool(
            registro.get(
                "atualizacao_bases",
                0
            )
        )
        gal = bool(
            registro.get(
                "atualizacao_gal",
                0
            )
        )

        sinan = verificacao and bases
        concluidas = {
            "sinan": sinan,
            "gal": gal
        }

        quantidade = sum(
            1
            for tarefa in tarefas
            if concluidas[tarefa]
        )

        houve_atividade = (
            verificacao
            or bases
            or gal
        )

        if not tarefas:
            estado = "nao_programado"
        elif quantidade == len(tarefas):
            estado = "concluido"
        elif houve_atividade:
            estado = "parcial"
        elif data_referencia < hoje:
            estado = "atrasado"
        else:
            estado = "pendente"

        return {
            "estado": estado,
            "tarefas_programadas": tarefas
        }

    # ------------------------------------------------------------------
    # Formatação
    # ------------------------------------------------------------------

    def formatar_data_extenso(
        self,
        data_referencia: date
    ) -> str:
        return (
            f"{self.DIAS_SEMANA[data_referencia.weekday()]}, "
            f"{data_referencia.day} de "
            f"{self.MESES[data_referencia.month - 1]} de "
            f"{data_referencia.year}"
        )

    def _saudacao(self) -> str:
        hora = datetime.now().hour

        if hora < 12:
            return "Bom dia"

        if hora < 18:
            return "Boa tarde"

        return "Boa noite"
