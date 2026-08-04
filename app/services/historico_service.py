from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EventoHistorico:
    """Evento operacional exibido na linha do tempo."""

    identificador: str
    data_referencia: date
    horario: datetime
    modulo: str
    titulo: str
    descricao: str
    status: str
    agravo: str | None = None


@dataclass(frozen=True)
class ResumoHistorico:
    """Indicadores consolidados para o período selecionado."""

    consulta_concluidas: int = 0
    consulta_em_andamento: int = 0
    consulta_erros: int = 0
    bases_concluidas: int = 0
    bases_em_andamento: int = 0
    bases_alertas: int = 0
    gal_concluidas: int = 0


@dataclass(frozen=True)
class ResultadoHistorico:
    """Resultado completo de uma consulta do histórico."""

    data_inicial: date
    data_final: date
    eventos: tuple[EventoHistorico, ...]
    resumo: ResumoHistorico


class HistoricoService:
    """
    Consulta o histórico operacional já existente no ArboHub.

    O serviço é somente leitura e usa apenas metadados operacionais:
    checkpoints, horários, agravos e números de solicitação. Nenhum
    conteúdo de DBF ou dado de paciente é lido.
    """

    MODULO_TODOS = "todos"
    MODULO_CONSULTA = "consulta"
    MODULO_BASES = "bases"
    MODULO_GAL = "gal"

    MODULOS_VALIDOS = {
        MODULO_TODOS,
        MODULO_CONSULTA,
        MODULO_BASES,
        MODULO_GAL,
    }

    STATUS_SUCESSO = "sucesso"
    STATUS_ATENCAO = "atencao"
    STATUS_ERRO = "erro"
    STATUS_INFO = "informacao"

    AGRAVOS = {
        "dengue": "Dengue",
        "chikungunya": "Chikungunya",
        "chiku": "Chikungunya",
    }

    def __init__(
        self,
        caminho_banco: str | Path | None = None,
    ):
        raiz_projeto = Path(__file__).resolve().parents[2]

        if caminho_banco is None:
            caminho_banco = raiz_projeto / "data" / "arbohub.db"

        self.caminho_banco = Path(caminho_banco).expanduser().resolve()

    def consultar(
        self,
        dias: int = 7,
        modulo: str = MODULO_TODOS,
        data_final: date | None = None,
    ) -> ResultadoHistorico:
        """Retorna resumo e eventos do período solicitado."""

        if dias not in {1, 7, 30}:
            raise ValueError("O período deve ser de 1, 7 ou 30 dias.")

        modulo = str(modulo).strip().casefold()
        if modulo not in self.MODULOS_VALIDOS:
            raise ValueError(f"Módulo inválido: {modulo}")

        data_final = data_final or date.today()
        data_inicial = data_final - timedelta(days=dias - 1)

        if not self.caminho_banco.exists():
            return ResultadoHistorico(
                data_inicial=data_inicial,
                data_final=data_final,
                eventos=(),
                resumo=ResumoHistorico(),
            )

        with self._conectar() as conexao:
            tabelas = self._listar_tabelas(conexao)
            rotinas = self._carregar_rotinas(
                conexao,
                tabelas,
                data_inicial,
                data_final,
            )
            obitos = self._carregar_obitos(
                conexao,
                tabelas,
                data_inicial,
                data_final,
            )
            lotes, solicitacoes = self._carregar_exportacoes(
                conexao,
                tabelas,
                data_inicial,
                data_final,
            )

        eventos = self._montar_eventos(
            rotinas=rotinas,
            obitos=obitos,
            lotes=lotes,
            solicitacoes=solicitacoes,
        )
        resumo = self._montar_resumo(
            rotinas=rotinas,
            obitos=obitos,
            lotes=lotes,
            solicitacoes=solicitacoes,
        )

        if modulo != self.MODULO_TODOS:
            eventos = [
                evento
                for evento in eventos
                if evento.modulo == modulo
            ]

        eventos.sort(
            key=lambda evento: (
                evento.horario,
                evento.identificador,
            ),
            reverse=True,
        )

        return ResultadoHistorico(
            data_inicial=data_inicial,
            data_final=data_final,
            eventos=tuple(eventos),
            resumo=resumo,
        )

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_banco,
            timeout=5,
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA query_only = ON")
        return conexao

    @staticmethod
    def _listar_tabelas(
        conexao: sqlite3.Connection,
    ) -> set[str]:
        linhas = conexao.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
        return {str(linha["name"]) for linha in linhas}

    @staticmethod
    def _colunas_tabela(
        conexao: sqlite3.Connection,
        tabela: str,
    ) -> set[str]:
        linhas = conexao.execute(
            f"PRAGMA table_info({tabela})"
        ).fetchall()
        return {str(linha["name"]) for linha in linhas}

    def _carregar_rotinas(
        self,
        conexao: sqlite3.Connection,
        tabelas: set[str],
        data_inicial: date,
        data_final: date,
    ) -> list[dict[str, Any]]:
        if "rotina_diaria" not in tabelas:
            return []

        colunas = self._colunas_tabela(conexao, "rotina_diaria")
        colunas_desejadas = (
            "data_referencia",
            "verificacao_obitos",
            "verificacao_obitos_em",
            "atualizacao_bases",
            "atualizacao_bases_em",
            "alerta_enviado",
            "alerta_enviado_em",
            "atualizacao_gal",
            "atualizacao_gal_em",
        )
        selecao = [
            coluna
            for coluna in colunas_desejadas
            if coluna in colunas
        ]

        if "data_referencia" not in selecao:
            return []

        linhas = conexao.execute(
            f"""
            SELECT {', '.join(selecao)}
            FROM rotina_diaria
            WHERE data_referencia BETWEEN ? AND ?
            ORDER BY data_referencia DESC
            """,
            (
                data_inicial.isoformat(),
                data_final.isoformat(),
            ),
        ).fetchall()

        return [dict(linha) for linha in linhas]

    def _carregar_obitos(
        self,
        conexao: sqlite3.Connection,
        tabelas: set[str],
        data_inicial: date,
        data_final: date,
    ) -> list[dict[str, Any]]:
        if "verificacao_obitos_diaria" not in tabelas:
            return []

        colunas = self._colunas_tabela(
            conexao,
            "verificacao_obitos_diaria",
        )
        colunas_desejadas = (
            "data_referencia",
            "agravo",
            "status",
            "iniciado_em",
            "consulta_concluida_em",
            "confirmado_em",
            "atualizado_em",
            "resultado_comparacao",
        )
        selecao = [
            coluna
            for coluna in colunas_desejadas
            if coluna in colunas
        ]

        if not {"data_referencia", "agravo", "status"}.issubset(
            selecao
        ):
            return []

        linhas = conexao.execute(
            f"""
            SELECT {', '.join(selecao)}
            FROM verificacao_obitos_diaria
            WHERE data_referencia BETWEEN ? AND ?
            ORDER BY data_referencia DESC, agravo ASC
            """,
            (
                data_inicial.isoformat(),
                data_final.isoformat(),
            ),
        ).fetchall()

        return [dict(linha) for linha in linhas]

    def _carregar_exportacoes(
        self,
        conexao: sqlite3.Connection,
        tabelas: set[str],
        data_inicial: date,
        data_final: date,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if "exportacao_dbf_lote" not in tabelas:
            return [], []

        lotes_linhas = conexao.execute(
            """
            SELECT
                lote_id,
                data_referencia,
                criado_em,
                atualizado_em
            FROM exportacao_dbf_lote
            WHERE data_referencia BETWEEN ? AND ?
            ORDER BY criado_em DESC
            """,
            (
                data_inicial.isoformat(),
                data_final.isoformat(),
            ),
        ).fetchall()
        lotes = [dict(linha) for linha in lotes_linhas]

        if (
            not lotes
            or "exportacao_dbf_solicitacao" not in tabelas
        ):
            return lotes, []

        ids = [str(lote["lote_id"]) for lote in lotes]
        placeholders = ",".join("?" for _ in ids)

        solicitacoes_linhas = conexao.execute(
            f"""
            SELECT
                lote_id,
                agravo,
                numero_solicitacao,
                solicitado_em,
                atualizado_em,
                status,
                quantidade_registros,
                processamento_concluido,
                link_disponivel,
                texto_link
            FROM exportacao_dbf_solicitacao
            WHERE lote_id IN ({placeholders})
            ORDER BY solicitado_em DESC
            """,
            ids,
        ).fetchall()

        return lotes, [dict(linha) for linha in solicitacoes_linhas]

    def _montar_eventos(
        self,
        rotinas: list[dict[str, Any]],
        obitos: list[dict[str, Any]],
        lotes: list[dict[str, Any]],
        solicitacoes: list[dict[str, Any]],
    ) -> list[EventoHistorico]:
        eventos: list[EventoHistorico] = []

        obitos_por_data: dict[str, list[dict[str, Any]]] = {}
        for registro in obitos:
            obitos_por_data.setdefault(
                str(registro["data_referencia"]),
                [],
            ).append(registro)
            eventos.extend(self._eventos_obito(registro))

        for rotina in rotinas:
            data_iso = str(rotina["data_referencia"])
            data_ref = self._converter_data(data_iso)
            if data_ref is None:
                continue

            if (
                rotina.get("verificacao_obitos_em")
                and not obitos_por_data.get(data_iso)
            ):
                evento = self._criar_evento(
                    identificador=f"consulta-geral-{data_iso}",
                    data_referencia=data_ref,
                    horario_iso=rotina.get("verificacao_obitos_em"),
                    modulo=self.MODULO_CONSULTA,
                    titulo="Consulta de óbitos concluída",
                    descricao=(
                        "Dengue e Chikungunya foram conferidas."
                    ),
                    status=self.STATUS_SUCESSO,
                )
                if evento:
                    eventos.append(evento)

            if rotina.get("atualizacao_bases_em"):
                evento = self._criar_evento(
                    identificador=f"bases-concluidas-{data_iso}",
                    data_referencia=data_ref,
                    horario_iso=rotina.get("atualizacao_bases_em"),
                    modulo=self.MODULO_BASES,
                    titulo="Bases do SINAN atualizadas",
                    descricao=(
                        "Os arquivos de Dengue e Chikungunya foram "
                        "validados e distribuídos aos destinos locais."
                    ),
                    status=self.STATUS_SUCESSO,
                )
                if evento:
                    eventos.append(evento)

            if rotina.get("alerta_enviado_em"):
                evento = self._criar_evento(
                    identificador=f"bases-alerta-{data_iso}",
                    data_referencia=data_ref,
                    horario_iso=rotina.get("alerta_enviado_em"),
                    modulo=self.MODULO_BASES,
                    titulo="Rotina de Bases exigiu atenção",
                    descricao=(
                        "O processamento ultrapassou o tempo previsto "
                        "e um alerta operacional foi registrado."
                    ),
                    status=self.STATUS_ATENCAO,
                )
                if evento:
                    eventos.append(evento)

            if rotina.get("atualizacao_gal_em"):
                evento = self._criar_evento(
                    identificador=f"gal-concluido-{data_iso}",
                    data_referencia=data_ref,
                    horario_iso=rotina.get("atualizacao_gal_em"),
                    modulo=self.MODULO_GAL,
                    titulo="Banco do GAL atualizado",
                    descricao=(
                        "A atualização programada do GAL foi marcada "
                        "como concluída."
                    ),
                    status=self.STATUS_SUCESSO,
                )
                if evento:
                    eventos.append(evento)

        for lote in lotes:
            data_ref = self._converter_data(lote.get("data_referencia"))
            if data_ref is None:
                continue

            possui_solicitacoes = any(
                solicitacao.get("lote_id") == lote.get("lote_id")
                for solicitacao in solicitacoes
            )
            if possui_solicitacoes:
                continue

            evento = self._criar_evento(
                identificador=f"lote-{lote.get('lote_id')}",
                data_referencia=data_ref,
                horario_iso=lote.get("criado_em"),
                modulo=self.MODULO_BASES,
                titulo="Lote de exportação criado",
                descricao=(
                    "O ArboHub iniciou um novo lote para as bases "
                    "de Dengue e Chikungunya."
                ),
                status=self.STATUS_INFO,
            )
            if evento:
                eventos.append(evento)

        for solicitacao in solicitacoes:
            eventos.extend(self._eventos_solicitacao(solicitacao, lotes))

        return eventos

    def _eventos_obito(
        self,
        registro: dict[str, Any],
    ) -> list[EventoHistorico]:
        data_ref = self._converter_data(registro.get("data_referencia"))
        if data_ref is None:
            return []

        agravo_chave = str(registro.get("agravo", "")).casefold()
        agravo = self.AGRAVOS.get(agravo_chave, agravo_chave.title())
        eventos: list[EventoHistorico] = []

        iniciado = self._criar_evento(
            identificador=f"obito-{agravo_chave}-inicio-{data_ref}",
            data_referencia=data_ref,
            horario_iso=registro.get("iniciado_em"),
            modulo=self.MODULO_CONSULTA,
            titulo=f"Consulta de {agravo} iniciada",
            descricao="O ArboHub iniciou a pesquisa no SINAN.",
            status=self.STATUS_INFO,
            agravo=agravo_chave,
        )
        if iniciado:
            eventos.append(iniciado)

        consulta_concluida = self._criar_evento(
            identificador=f"obito-{agravo_chave}-conferencia-{data_ref}",
            data_referencia=data_ref,
            horario_iso=registro.get("consulta_concluida_em"),
            modulo=self.MODULO_CONSULTA,
            titulo=f"{agravo} aguardando conferência",
            descricao=(
                "A pesquisa foi concluída e ficou disponível para "
                "a validação humana."
            ),
            status=self.STATUS_ATENCAO,
            agravo=agravo_chave,
        )
        if consulta_concluida:
            eventos.append(consulta_concluida)

        confirmado_em = registro.get("confirmado_em")
        if confirmado_em:
            resultado = str(
                registro.get("resultado_comparacao") or ""
            ).casefold()
            descricoes = {
                "manteve_igual": (
                    "A conferência foi confirmada sem alteração "
                    "no resultado comparado."
                ),
                "mudou": (
                    "A conferência foi concluída e registrou "
                    "alteração no resultado comparado."
                ),
            }
            descricao = descricoes.get(
                resultado,
                "A conferência humana foi concluída.",
            )
            confirmado = self._criar_evento(
                identificador=f"obito-{agravo_chave}-fim-{data_ref}",
                data_referencia=data_ref,
                horario_iso=confirmado_em,
                modulo=self.MODULO_CONSULTA,
                titulo=f"Conferência de {agravo} concluída",
                descricao=descricao,
                status=self.STATUS_SUCESSO,
                agravo=agravo_chave,
            )
            if confirmado:
                eventos.append(confirmado)

        if str(registro.get("status", "")).casefold() == "erro":
            erro = self._criar_evento(
                identificador=f"obito-{agravo_chave}-erro-{data_ref}",
                data_referencia=data_ref,
                horario_iso=(
                    registro.get("atualizado_em")
                    or registro.get("iniciado_em")
                ),
                modulo=self.MODULO_CONSULTA,
                titulo=f"Falha na consulta de {agravo}",
                descricao=(
                    "A rotina foi interrompida antes da conclusão."
                ),
                status=self.STATUS_ERRO,
                agravo=agravo_chave,
            )
            if erro:
                eventos.append(erro)

        return eventos

    def _eventos_solicitacao(
        self,
        solicitacao: dict[str, Any],
        lotes: list[dict[str, Any]],
    ) -> list[EventoHistorico]:
        lote = next(
            (
                item
                for item in lotes
                if item.get("lote_id") == solicitacao.get("lote_id")
            ),
            None,
        )
        if lote is None:
            return []

        data_ref = self._converter_data(lote.get("data_referencia"))
        if data_ref is None:
            return []

        agravo_chave = str(solicitacao.get("agravo", "")).casefold()
        agravo = self.AGRAVOS.get(agravo_chave, agravo_chave.title())
        numero = str(solicitacao.get("numero_solicitacao") or "").strip()
        complemento_numero = f" Solicitação {numero}." if numero else ""
        eventos: list[EventoHistorico] = []

        solicitado = self._criar_evento(
            identificador=(
                f"solicitacao-{solicitacao.get('lote_id')}-"
                f"{agravo_chave}"
            ),
            data_referencia=data_ref,
            horario_iso=solicitacao.get("solicitado_em"),
            modulo=self.MODULO_BASES,
            titulo=f"Exportação de {agravo} solicitada",
            descricao=(
                "A solicitação foi registrada no SINAN."
                + complemento_numero
            ),
            status=self.STATUS_INFO,
            agravo=agravo_chave,
        )
        if solicitado:
            eventos.append(solicitado)

        status = str(solicitacao.get("status") or "").casefold()
        concluido = bool(solicitacao.get("processamento_concluido"))
        link = bool(solicitacao.get("link_disponivel"))
        atualizado_em = solicitacao.get("atualizado_em")
        solicitado_em = solicitacao.get("solicitado_em")

        if (concluido or link or status == "concluido") and atualizado_em:
            quantidade = str(
                solicitacao.get("quantidade_registros") or ""
            ).strip()
            detalhe = (
                f" Quantidade informada pelo SINAN: {quantidade}."
                if quantidade
                else ""
            )
            disponivel = self._criar_evento(
                identificador=(
                    f"exportacao-pronta-{solicitacao.get('lote_id')}-"
                    f"{agravo_chave}"
                ),
                data_referencia=data_ref,
                horario_iso=atualizado_em,
                modulo=self.MODULO_BASES,
                titulo=f"Exportação de {agravo} disponível",
                descricao=(
                    "O processamento foi concluído e o arquivo ficou "
                    "disponível para download."
                    + detalhe
                ),
                status=self.STATUS_SUCESSO,
                agravo=agravo_chave,
            )
            if disponivel:
                eventos.append(disponivel)
        elif (
            status == "processando"
            and atualizado_em
            and atualizado_em != solicitado_em
        ):
            processando = self._criar_evento(
                identificador=(
                    f"exportacao-processando-{solicitacao.get('lote_id')}-"
                    f"{agravo_chave}"
                ),
                data_referencia=data_ref,
                horario_iso=atualizado_em,
                modulo=self.MODULO_BASES,
                titulo=f"Exportação de {agravo} em processamento",
                descricao=(
                    "O SINAN reconheceu a solicitação, mas o arquivo "
                    "ainda não estava disponível."
                ),
                status=self.STATUS_ATENCAO,
                agravo=agravo_chave,
            )
            if processando:
                eventos.append(processando)

        return eventos

    def _montar_resumo(
        self,
        rotinas: list[dict[str, Any]],
        obitos: list[dict[str, Any]],
        lotes: list[dict[str, Any]],
        solicitacoes: list[dict[str, Any]],
    ) -> ResumoHistorico:
        obitos_por_data: dict[str, list[dict[str, Any]]] = {}
        for registro in obitos:
            obitos_por_data.setdefault(
                str(registro.get("data_referencia")),
                [],
            ).append(registro)

        consulta_concluidas = 0
        consulta_em_andamento = 0
        consulta_erros = 0

        datas_rotinas = {
            str(rotina.get("data_referencia"))
            for rotina in rotinas
        }
        datas_consulta = datas_rotinas | set(obitos_por_data)

        rotinas_por_data = {
            str(rotina.get("data_referencia")): rotina
            for rotina in rotinas
        }

        for data_iso in datas_consulta:
            registros = obitos_por_data.get(data_iso, [])
            rotina = rotinas_por_data.get(data_iso, {})
            status = {
                str(item.get("status") or "").casefold()
                for item in registros
            }

            agravos_concluidos = {
                str(item.get("agravo") or "").casefold()
                for item in registros
                if str(item.get("status") or "").casefold()
                == "concluido"
            }
            concluido_detalhado = {
                "dengue",
                "chikungunya",
            }.issubset(agravos_concluidos)
            concluido = bool(
                rotina.get("verificacao_obitos")
            ) or concluido_detalhado

            houve_atividade = any(
                item.get("iniciado_em")
                or item.get("consulta_concluida_em")
                or item.get("confirmado_em")
                or str(item.get("status") or "").casefold()
                in {"executando", "aguardando_conferencia", "erro"}
                for item in registros
            )

            if concluido:
                consulta_concluidas += 1
            elif "erro" in status:
                consulta_erros += 1
            elif houve_atividade:
                consulta_em_andamento += 1

        bases_concluidas = sum(
            1
            for rotina in rotinas
            if bool(rotina.get("atualizacao_bases"))
        )
        bases_alertas = sum(
            1
            for rotina in rotinas
            if bool(rotina.get("alerta_enviado"))
        )

        lotes_por_data: dict[str, list[dict[str, Any]]] = {}
        for lote in lotes:
            lotes_por_data.setdefault(
                str(lote.get("data_referencia")),
                [],
            ).append(lote)

        bases_em_andamento = 0
        for data_iso, lotes_data in lotes_por_data.items():
            rotina = rotinas_por_data.get(data_iso, {})
            if bool(rotina.get("atualizacao_bases")):
                continue

            ids = {str(lote.get("lote_id")) for lote in lotes_data}
            solicitacoes_data = [
                item
                for item in solicitacoes
                if str(item.get("lote_id")) in ids
            ]

            if lotes_data or solicitacoes_data:
                bases_em_andamento += 1

        gal_concluidas = sum(
            1
            for rotina in rotinas
            if bool(rotina.get("atualizacao_gal"))
        )

        return ResumoHistorico(
            consulta_concluidas=consulta_concluidas,
            consulta_em_andamento=consulta_em_andamento,
            consulta_erros=consulta_erros,
            bases_concluidas=bases_concluidas,
            bases_em_andamento=bases_em_andamento,
            bases_alertas=bases_alertas,
            gal_concluidas=gal_concluidas,
        )

    def _criar_evento(
        self,
        identificador: str,
        data_referencia: date,
        horario_iso: Any,
        modulo: str,
        titulo: str,
        descricao: str,
        status: str,
        agravo: str | None = None,
    ) -> EventoHistorico | None:
        horario = self._converter_datetime(horario_iso)
        if horario is None:
            return None

        return EventoHistorico(
            identificador=identificador,
            data_referencia=data_referencia,
            horario=horario,
            modulo=modulo,
            titulo=titulo,
            descricao=descricao,
            status=status,
            agravo=agravo,
        )

    @staticmethod
    def _converter_data(valor: Any) -> date | None:
        if not valor:
            return None
        try:
            return date.fromisoformat(str(valor))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _converter_datetime(valor: Any) -> datetime | None:
        if not valor:
            return None
        try:
            return datetime.fromisoformat(str(valor))
        except (TypeError, ValueError):
            return None
