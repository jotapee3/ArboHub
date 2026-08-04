from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

import customtkinter as ctk

from app.gui.components.arbohub_dialog import mostrar_dialogo_arbohub
from app.gui.themes.colors import Colors
from app.services.historico_service import (
    EventoHistorico,
    HistoricoService,
    ResultadoHistorico,
)


class HistoricoPage(ctk.CTkScrollableFrame):
    """Linha do tempo operacional do ArboHub."""

    PERIODOS = {
        "Hoje": 1,
        "7 dias": 7,
        "30 dias": 30,
    }

    MODULOS = {
        "Todos os módulos": HistoricoService.MODULO_TODOS,
        "Consulta": HistoricoService.MODULO_CONSULTA,
        "Bases": HistoricoService.MODULO_BASES,
        "GAL": HistoricoService.MODULO_GAL,
    }

    ROTULOS_MODULOS = {
        HistoricoService.MODULO_CONSULTA: "CONSULTA",
        HistoricoService.MODULO_BASES: "BASES",
        HistoricoService.MODULO_GAL: "GAL",
    }

    CORES_STATUS = {
        HistoricoService.STATUS_SUCESSO: Colors.SUCCESS,
        HistoricoService.STATUS_ATENCAO: Colors.WARNING,
        HistoricoService.STATUS_ERRO: Colors.ERROR,
        HistoricoService.STATUS_INFO: Colors.INFO,
    }

    ROTULOS_STATUS = {
        HistoricoService.STATUS_SUCESSO: "Concluído",
        HistoricoService.STATUS_ATENCAO: "Atenção",
        HistoricoService.STATUS_ERRO: "Erro",
        HistoricoService.STATUS_INFO: "Informação",
    }

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
        "dezembro",
    )

    DIAS_SEMANA = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED,
        )

        self.historico_service = HistoricoService()
        self.periodo_var = ctk.StringVar(value="7 dias")
        self.modulo_var = ctk.StringVar(value="Todos os módulos")

        self.grid_columnconfigure(0, weight=1)

        self._criar_cabecalho()
        self._criar_filtros()
        self._criar_area_resumo()
        self._criar_area_timeline()
        self.atualizar_historico()

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(30, 18),
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Histórico",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Acompanhe as operações registradas pelo ArboHub "
                "sem acessar dados de pacientes."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))

        self.label_atualizacao = ctk.CTkLabel(
            cabecalho,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
            anchor="e",
        )
        self.label_atualizacao.grid(
            row=1,
            column=1,
            sticky="e",
            padx=(20, 0),
            pady=(5, 0),
        )

        ctk.CTkButton(
            cabecalho,
            text="↻  Atualizar",
            command=self.atualizar_historico,
            width=125,
            height=38,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=1,
            sticky="e",
            padx=(20, 0),
        )

    def _criar_filtros(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        painel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 18),
        )
        painel.grid_columnconfigure(0, weight=1)

        esquerda = ctk.CTkFrame(painel, fg_color="transparent")
        esquerda.grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=18,
        )

        ctk.CTkLabel(
            esquerda,
            text="Período",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        self.controle_periodo = ctk.CTkSegmentedButton(
            esquerda,
            values=list(self.PERIODOS.keys()),
            variable=self.periodo_var,
            command=lambda _valor: self.atualizar_historico(),
            height=34,
            corner_radius=7,
            fg_color=Colors.INPUT,
            selected_color=Colors.PRIMARY_PRESSED,
            selected_hover_color=Colors.PRIMARY_HOVER,
            unselected_color=Colors.BUTTON,
            unselected_hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.controle_periodo.pack(anchor="w")

        direita = ctk.CTkFrame(painel, fg_color="transparent")
        direita.grid(
            row=0,
            column=1,
            sticky="e",
            padx=20,
            pady=18,
        )

        ctk.CTkLabel(
            direita,
            text="Módulo",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkOptionMenu(
            direita,
            variable=self.modulo_var,
            values=list(self.MODULOS.keys()),
            command=lambda _valor: self.atualizar_historico(),
            width=190,
            height=34,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE_SECONDARY,
            dropdown_hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
        ).pack(anchor="w")

    def _criar_area_resumo(self):
        self.container_resumo = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.container_resumo.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 18),
        )
        self.container_resumo.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="resumo_historico",
        )

    def _criar_area_timeline(self):
        self.painel_timeline = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.painel_timeline.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 38),
        )
        self.painel_timeline.grid_columnconfigure(0, weight=1)

        cabecalho = ctk.CTkFrame(
            self.painel_timeline,
            fg_color="transparent",
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(20, 14),
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Linha do tempo",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        self.label_quantidade = ctk.CTkLabel(
            cabecalho,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
            anchor="e",
        )
        self.label_quantidade.grid(row=0, column=1, sticky="e")

        divisor = ctk.CTkFrame(
            self.painel_timeline,
            height=1,
            fg_color=Colors.DIVIDER,
        )
        divisor.grid(row=1, column=0, sticky="ew")

        self.container_eventos = ctk.CTkFrame(
            self.painel_timeline,
            fg_color="transparent",
        )
        self.container_eventos.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(6, 22),
        )
        self.container_eventos.grid_columnconfigure(0, weight=1)

    def atualizar_historico(self):
        try:
            dias = self.PERIODOS.get(self.periodo_var.get(), 7)
            modulo = self.MODULOS.get(
                self.modulo_var.get(),
                HistoricoService.MODULO_TODOS,
            )
            resultado = self.historico_service.consultar(
                dias=dias,
                modulo=modulo,
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                self,
                titulo="Histórico indisponível",
                mensagem=(
                    "Não foi possível carregar o histórico "
                    f"operacional.\n\nDetalhe: {erro}"
                ),
                tipo="erro",
            )
            return

        self._preencher_resumo(resultado)
        self._preencher_timeline(resultado)
        self.label_atualizacao.configure(
            text=(
                "Atualizado às "
                f"{datetime.now().strftime('%H:%M')}"
            )
        )

    def _preencher_resumo(self, resultado: ResultadoHistorico):
        for filho in self.container_resumo.winfo_children():
            filho.destroy()

        resumo = resultado.resumo

        consulta_detalhes = []
        if resumo.consulta_em_andamento:
            consulta_detalhes.append(
                f"{resumo.consulta_em_andamento} em andamento"
            )
        if resumo.consulta_erros:
            consulta_detalhes.append(
                f"{resumo.consulta_erros} com erro"
            )

        bases_detalhes = []
        if resumo.bases_em_andamento:
            bases_detalhes.append(
                f"{resumo.bases_em_andamento} em andamento"
            )
        if resumo.bases_alertas:
            bases_detalhes.append(
                f"{resumo.bases_alertas} com alerta"
            )

        cards = (
            (
                "Consulta",
                resumo.consulta_concluidas,
                self._pluralizar(
                    resumo.consulta_concluidas,
                    "concluída",
                    "concluídas",
                ),
                " · ".join(consulta_detalhes) or "Sem pendências registradas",
                Colors.INFO,
            ),
            (
                "Bases",
                resumo.bases_concluidas,
                self._pluralizar(
                    resumo.bases_concluidas,
                    "completa",
                    "completas",
                ),
                " · ".join(bases_detalhes) or "Sem pendências registradas",
                Colors.SUCCESS,
            ),
            (
                "GAL",
                resumo.gal_concluidas,
                self._pluralizar(
                    resumo.gal_concluidas,
                    "atualização",
                    "atualizações",
                ),
                "Conclusões registradas no período",
                Colors.WARNING,
            ),
        )

        for coluna, card in enumerate(cards):
            self._criar_card_resumo(
                coluna=coluna,
                titulo=card[0],
                valor=card[1],
                unidade=card[2],
                detalhe=card[3],
                cor=card[4],
            )

    def _criar_card_resumo(
        self,
        coluna: int,
        titulo: str,
        valor: int,
        unidade: str,
        detalhe: str,
        cor: str,
    ):
        margem = (
            (0, 6)
            if coluna == 0
            else (6, 6)
            if coluna == 1
            else (6, 0)
        )

        card = ctk.CTkFrame(
            self.container_resumo,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        card.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=margem,
        )
        card.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(16, 8),
        )
        topo.grid_columnconfigure(1, weight=1)

        ctk.CTkFrame(
            topo,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=cor,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            topo,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            card,
            text=str(valor),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=28,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
        )

        ctk.CTkLabel(
            card,
            text=unidade,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 7),
        )

        ctk.CTkLabel(
            card,
            text=detalhe,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=260,
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )

    def _preencher_timeline(self, resultado: ResultadoHistorico):
        for filho in self.container_eventos.winfo_children():
            filho.destroy()

        quantidade = len(resultado.eventos)
        self.label_quantidade.configure(
            text=(
                f"{quantidade} "
                + self._pluralizar(
                    quantidade,
                    "evento",
                    "eventos",
                )
            )
        )

        if not resultado.eventos:
            self._criar_estado_vazio(resultado)
            return

        por_data: dict[date, list[EventoHistorico]] = defaultdict(list)
        for evento in resultado.eventos:
            por_data[evento.data_referencia].append(evento)

        linha = 0
        for data_referencia in sorted(por_data, reverse=True):
            self._criar_cabecalho_data(
                linha=linha,
                data_referencia=data_referencia,
            )
            linha += 1

            for evento in por_data[data_referencia]:
                self._criar_card_evento(
                    linha=linha,
                    evento=evento,
                )
                linha += 1

    def _criar_estado_vazio(self, resultado: ResultadoHistorico):
        estado = ctk.CTkFrame(
            self.container_eventos,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_MUTED,
        )
        estado.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        ctk.CTkLabel(
            estado,
            text="Nenhuma atividade encontrada",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(pady=(28, 7))

        ctk.CTkLabel(
            estado,
            text=(
                "Não existem registros para o período e o módulo "
                "selecionados."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(pady=(0, 28))

    def _criar_cabecalho_data(
        self,
        linha: int,
        data_referencia: date,
    ):
        container = ctk.CTkFrame(
            self.container_eventos,
            fg_color="transparent",
        )
        container.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(16 if linha else 10, 8),
        )
        container.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            container,
            text=self._formatar_data_grupo(data_referencia),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkFrame(
            container,
            height=1,
            fg_color=Colors.DIVIDER,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 0),
        )

    def _criar_card_evento(
        self,
        linha: int,
        evento: EventoHistorico,
    ):
        cor = self.CORES_STATUS.get(evento.status, Colors.TEXT_MUTED)

        card = ctk.CTkFrame(
            self.container_eventos,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_MUTED,
        )
        card.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=4,
        )
        card.grid_columnconfigure(2, weight=1)

        ctk.CTkFrame(
            card,
            width=4,
            corner_radius=2,
            fg_color=cor,
        ).grid(
            row=0,
            column=0,
            rowspan=3,
            sticky="ns",
            padx=(0, 0),
        )

        ctk.CTkLabel(
            card,
            text=evento.horario.strftime("%H:%M"),
            width=58,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="center",
        ).grid(
            row=0,
            column=1,
            rowspan=3,
            sticky="ns",
            padx=(10, 8),
            pady=14,
        )

        cabecalho = ctk.CTkFrame(card, fg_color="transparent")
        cabecalho.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(0, 14),
            pady=(12, 3),
        )
        cabecalho.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text=self.ROTULOS_MODULOS.get(
                evento.modulo,
                evento.modulo.upper(),
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold",
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            cabecalho,
            text=self.ROTULOS_STATUS.get(
                evento.status,
                "Registro",
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold",
            ),
            text_color=cor,
            anchor="e",
        ).grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(
            card,
            text=evento.titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(0, 14),
        )

        ctk.CTkLabel(
            card,
            text=evento.descricao,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=760,
        ).grid(
            row=2,
            column=2,
            sticky="ew",
            padx=(0, 14),
            pady=(3, 13),
        )

    def _formatar_data_grupo(self, data_referencia: date) -> str:
        hoje = date.today()
        prefixo = ""

        if data_referencia == hoje:
            prefixo = "Hoje — "
        elif data_referencia == hoje - timedelta(days=1):
            prefixo = "Ontem — "
        else:
            prefixo = (
                self.DIAS_SEMANA[data_referencia.weekday()].capitalize()
                + " — "
            )

        return (
            f"{prefixo}{data_referencia.day:02d} de "
            f"{self.MESES[data_referencia.month - 1]} de "
            f"{data_referencia.year}"
        )

    @staticmethod
    def _pluralizar(
        quantidade: int,
        singular: str,
        plural: str,
    ) -> str:
        return singular if quantidade == 1 else plural
