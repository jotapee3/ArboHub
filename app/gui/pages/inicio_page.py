from __future__ import annotations

import tkinter as tk
from pathlib import Path
from datetime import date, datetime, timedelta

import customtkinter as ctk
from PIL import Image

from app.gui.themes.colors import Colors
from app.services.dashboard_service import DashboardService
from app.services.configuracoes_service import ConfiguracoesService


class InicioPage(ctk.CTkScrollableFrame):
    """
    Dashboard operacional do ArboHub.

    A tela resume a rotina do dia e apresenta a frequência anual
    em um calendário inspirado no painel de contribuições do GitHub.
    """

    COR_CALENDARIO_VAZIO = "#21262d"
    COR_CALENDARIO_BORDA = "#30363d"
    CORES_NIVEIS = {
        0: "#21262d",
        1: "#263a2d",
        2: "#2f6f44",
        3: "#3fb950",
        4: "#56d364"
    }

    COR_AVISO = "#D29922"
    COR_ERRO = "#F85149"

    def __init__(
        self,
        master,
        comando_sinan=None,
        comando_gal=None
    ):
        self.comando_sinan = comando_sinan
        self.comando_gal = comando_gal

        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.dashboard_service = DashboardService()
        self.configuracoes_service = ConfiguracoesService()
        self._icones_sistemas: dict[str, ctk.CTkImage] = {}
        self.resumo: dict[str, object] | None = None
        self._atualizacao_id = None
        self._pagina_destruida = False
        self._layout_vertical = None

        self.grid_columnconfigure(0, weight=1)

        self.criar_cabecalho()
        self.criar_painel_principal()
        self.criar_indicadores()
        self.criar_rotina_hoje()
        self.criar_calendario_frequencia()
        self.criar_atividade_recente()

        # CTkScrollableFrame já possui uma vinculação interna
        # em <Configure> para atualizar a região de rolagem.
        # O parâmetro add="+" preserva essa vinculação.
        self.bind(
            "<Configure>",
            self._ao_redimensionar,
            add="+"
        )
        self.bind(
            "<Destroy>",
            self._ao_destruir,
            add="+"
        )

        self.after(
            80,
            self.atualizar_dashboard
        )

    # ------------------------------------------------------------------
    # Construção da página
    # ------------------------------------------------------------------

    def criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(30, 18)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        self.label_titulo = ctk.CTkLabel(
            cabecalho,
            text="Início",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.label_titulo.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        ctk.CTkLabel(
            cabecalho,
            text="Visão geral da vigilância e da rotina operacional.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 0)
        )

        self.botao_atualizar = ctk.CTkButton(
            cabecalho,
            text="↻ Atualizar",
            command=self.atualizar_dashboard,
            width=118,
            height=36,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.botao_atualizar.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e"
        )

    def criar_painel_principal(self):
        self.painel_principal = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.painel_principal.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40
        )
        self.painel_principal.grid_columnconfigure(
            1,
            weight=1
        )

        self.bloco_icone_principal = ctk.CTkFrame(
            self.painel_principal,
            width=58,
            height=58,
            fg_color=Colors.BUTTON,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.bloco_icone_principal.grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(22, 17),
            pady=22
        )
        self.bloco_icone_principal.grid_propagate(
            False
        )

        self.label_icone_principal = ctk.CTkLabel(
            self.bloco_icone_principal,
            text="◉",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=25,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        )
        self.label_icone_principal.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        self.label_saudacao = ctk.CTkLabel(
            self.painel_principal,
            text="Carregando painel...",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.PRIMARY,
            anchor="w"
        )
        self.label_saudacao.grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 22),
            pady=(22, 2)
        )

        self.label_estado_dia = ctk.CTkLabel(
            self.painel_principal,
            text="Verificando a rotina de hoje",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=22,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.label_estado_dia.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 22)
        )

        self.label_descricao_dia = ctk.CTkLabel(
            self.painel_principal,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=700
        )
        self.label_descricao_dia.grid(
            row=2,
            column=1,
            sticky="new",
            padx=(0, 22),
            pady=(4, 22)
        )

    def criar_indicadores(self):
        self.container_indicadores = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.container_indicadores.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 0)
        )
        self.container_indicadores.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="indicadores"
        )

        self.card_frequencia = self._criar_card_indicador(
            master=self.container_indicadores,
            coluna=0,
            titulo="FREQUÊNCIA DO MÊS",
            valor="—",
            detalhe="Dias úteis concluídos"
        )
        self.card_sequencia = self._criar_card_indicador(
            master=self.container_indicadores,
            coluna=1,
            titulo="SEQUÊNCIA ATUAL",
            valor="—",
            detalhe="Dias programados consecutivos"
        )
        self.card_concluidas = self._criar_card_indicador(
            master=self.container_indicadores,
            coluna=2,
            titulo="ROTINAS CONCLUÍDAS",
            valor="—",
            detalhe="No mês atual"
        )

    def _criar_card_indicador(
        self,
        master,
        coluna: int,
        titulo: str,
        valor: str,
        detalhe: str
    ) -> dict[str, ctk.CTkBaseClass]:
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=(
                (0, 6)
                if coluna == 0
                else (
                    (6, 0)
                    if coluna == 2
                    else 6
                )
            )
        )

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).pack(
            fill="x",
            padx=18,
            pady=(16, 5)
        )

        label_valor = ctk.CTkLabel(
            card,
            text=valor,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=25,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        label_valor.pack(
            fill="x",
            padx=18
        )

        label_detalhe = ctk.CTkLabel(
            card,
            text=detalhe,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        label_detalhe.pack(
            fill="x",
            padx=18,
            pady=(3, 16)
        )

        return {
            "frame": card,
            "valor": label_valor,
            "detalhe": label_detalhe
        }

    def criar_rotina_hoje(self):
        self.painel_rotina = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.painel_rotina.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 0)
        )
        self.painel_rotina.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="rotina_hoje"
        )

        ctk.CTkLabel(
            self.painel_rotina,
            text="Rotina de hoje",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        self.label_programacao = ctk.CTkLabel(
            self.painel_rotina,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_programacao.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=20,
            pady=(0, 14)
        )

        self.card_sinan = self._criar_card_rotina(
            master=self.painel_rotina,
            coluna=0,
            icone="S",
            icone_arquivo="sinan_logo.png",
            titulo="SINAN",
            subtitulo=(
                "Consulta de óbitos e atualização das bases"
            )
        )

        self.card_gal = self._criar_card_rotina(
            master=self.painel_rotina,
            coluna=1,
            icone="G",
            icone_arquivo="gal_logo.png",
            titulo="GAL",
            subtitulo=(
                "Atualização semanal do banco laboratorial"
            )
        )

    def _criar_card_rotina(
        self,
        master,
        coluna: int,
        icone: str,
        icone_arquivo: str,
        titulo: str,
        subtitulo: str
    ) -> dict[str, ctk.CTkBaseClass]:
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=2,
            column=coluna,
            sticky="nsew",
            padx=(
                (20, 6)
                if coluna == 0
                else (6, 20)
            ),
            pady=(0, 20)
        )
        card.grid_columnconfigure(
            1,
            weight=1
        )

        icone_frame = ctk.CTkFrame(
            card,
            width=42,
            height=42,
            fg_color=Colors.BUTTON,
            corner_radius=9
        )
        icone_frame.grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(14, 12),
            pady=14
        )
        icone_frame.grid_propagate(False)

        imagem_icone = self._carregar_icone_sistema(
            icone_arquivo
        )

        label_icone = ctk.CTkLabel(
            icone_frame,
            text=(
                ""
                if imagem_icone is not None
                else icone
            ),
            image=imagem_icone,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        )
        label_icone.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 14),
            pady=(13, 1)
        )

        label_status = ctk.CTkLabel(
            card,
            text="○ Aguardando",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        label_status.grid(
            row=1,
            column=1,
            sticky="w",
            padx=(0, 14)
        )

        label_detalhe = ctk.CTkLabel(
            card,
            text=subtitulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=300
        )
        label_detalhe.grid(
            row=2,
            column=1,
            sticky="new",
            padx=(0, 14),
            pady=(3, 13)
        )

        return {
            "frame": card,
            "status": label_status,
            "detalhe": label_detalhe
        }

    def criar_calendario_frequencia(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 0)
        )
        painel.grid_columnconfigure(0, weight=1)

        cabecalho = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 8)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        self.label_titulo_calendario = ctk.CTkLabel(
            cabecalho,
            text="Frequência das rotinas",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.label_titulo_calendario.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.label_contribuicoes = ctk.CTkLabel(
            cabecalho,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="e"
        )
        self.label_contribuicoes.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.canvas_calendario = tk.Canvas(
            painel,
            height=165,
            bg=Colors.SURFACE,
            highlightthickness=0,
            bd=0
        )
        self.canvas_calendario.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=16
        )
        self.canvas_calendario.bind(
            "<Configure>",
            lambda _evento:
                self.desenhar_calendario()
        )

        legenda = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        legenda.grid(
            row=2,
            column=0,
            sticky="e",
            padx=20,
            pady=(2, 16)
        )

        ctk.CTkLabel(
            legenda,
            text="Menos",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED
        ).pack(
            side="left",
            padx=(0, 5)
        )

        for nivel in range(5):
            bloco = ctk.CTkFrame(
                legenda,
                width=11,
                height=11,
                corner_radius=2,
                fg_color=self.CORES_NIVEIS[nivel],
                border_width=1,
                border_color=self.COR_CALENDARIO_BORDA
            )
            bloco.pack(
                side="left",
                padx=2
            )
            bloco.pack_propagate(False)

        ctk.CTkLabel(
            legenda,
            text="Mais",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED
        ).pack(
            side="left",
            padx=(5, 0)
        )

    def criar_atividade_recente(self):
        self.painel_atividade = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.painel_atividade.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 30)
        )
        self.painel_atividade.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            self.painel_atividade,
            text="Atividade recente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        ctk.CTkLabel(
            self.painel_atividade,
            text=(
                "Somente eventos operacionais são exibidos. "
                "Nenhum dado de pacientes é armazenado neste painel."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )

        self.container_atividades = ctk.CTkFrame(
            self.painel_atividade,
            fg_color="transparent"
        )
        self.container_atividades.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 16)
        )
        self.container_atividades.grid_columnconfigure(
            0,
            weight=1
        )

    def _carregar_icone_sistema(
        self,
        nome_arquivo: str
    ) -> ctk.CTkImage | None:
        """
        Carrega as logos de SINAN e GAL sem alterar o layout dos cards.

        Se o arquivo não estiver disponível, o card usa automaticamente
        a letra original como fallback.
        """

        if nome_arquivo in self._icones_sistemas:
            return self._icones_sistemas[
                nome_arquivo
            ]

        raiz_projeto = Path(
            __file__
        ).resolve().parents[3]

        candidatos = (
            raiz_projeto
            / "assets"
            / "sistemas"
            / nome_arquivo,
            raiz_projeto
            / "app"
            / "assets"
            / "sistemas"
            / nome_arquivo
        )

        for caminho in candidatos:
            if not caminho.exists():
                continue

            try:
                with Image.open(caminho) as arquivo:
                    imagem_pil = arquivo.convert(
                        "RGBA"
                    )

                imagem = ctk.CTkImage(
                    light_image=imagem_pil,
                    dark_image=imagem_pil,
                    size=(30, 30)
                )

                self._icones_sistemas[
                    nome_arquivo
                ] = imagem

                return imagem
            except (
                OSError,
                ValueError
            ):
                continue

        return None

    # ------------------------------------------------------------------
    # Atualização
    # ------------------------------------------------------------------

    def atualizar_dashboard(self):
        if self._pagina_destruida:
            return

        try:
            self.resumo = (
                self.dashboard_service
                .obter_resumo_dashboard()
            )
        except Exception as erro:
            self.label_estado_dia.configure(
                text="Não foi possível carregar o painel",
                text_color=self.COR_ERRO
            )
            self.label_descricao_dia.configure(
                text=str(erro)
            )
            return

        self._atualizar_painel_principal()
        self._atualizar_indicadores()
        self._atualizar_rotina_hoje()
        self._atualizar_atividades()
        self.desenhar_calendario()

        if self._atualizacao_id is not None:
            try:
                self.after_cancel(
                    self._atualizacao_id
                )
            except Exception:
                pass

        configuracoes_dashboard = (
            self.configuracoes_service
            .carregar()["dashboard"]
        )

        if configuracoes_dashboard[
            "atualizacao_automatica"
        ]:
            intervalo_ms = (
                configuracoes_dashboard[
                    "intervalo_segundos"
                ]
                * 1000
            )

            self._atualizacao_id = self.after(
                intervalo_ms,
                self.atualizar_dashboard
            )
        else:
            self._atualizacao_id = None

    def _atualizar_painel_principal(self):
        hoje = self.resumo["hoje"]
        estado = hoje["estado"]

        apresentacao = {
            "concluido": (
                "✅",
                "Tudo concluído hoje",
                Colors.SUCCESS,
                "A rotina programada para hoje foi finalizada."
            ),
            "parcial": (
                "◐",
                "Rotina de hoje em andamento",
                self.COR_AVISO,
                (
                    f"{hoje['quantidade_concluida']} de "
                    f"{hoje['quantidade_programada']} "
                    "tarefas programadas foram concluídas."
                )
            ),
            "pendente": (
                "○",
                "A rotina de hoje está pendente",
                Colors.PRIMARY,
                "Há tarefas programadas aguardando execução."
            ),
            "atrasado": (
                "!",
                "Existem pendências na rotina",
                self.COR_ERRO,
                "A rotina programada ainda não foi concluída."
            ),
            "nao_programado": (
                "—",
                "Nenhuma rotina programada para hoje",
                Colors.TEXT_MUTED,
                (
                    "A próxima rotina será realizada no próximo "
                    "dia útil."
                )
            )
        }

        icone, titulo, cor, descricao = apresentacao[
            estado
        ]

        self.label_icone_principal.configure(
            text=icone,
            text_color=cor
        )
        self.label_saudacao.configure(
            text=(
                f"{self.resumo['saudacao']}  •  "
                f"{self.resumo['data_formatada']}"
            ),
            text_color=cor
        )
        self.label_estado_dia.configure(
            text=titulo,
            text_color=Colors.TEXT_PRIMARY
        )
        self.label_descricao_dia.configure(
            text=descricao
        )
        self.bloco_icone_principal.configure(
            border_color=cor
        )

    def _atualizar_indicadores(self):
        resumo_mes = self.resumo[
            "resumo_mes"
        ]

        self.card_frequencia["valor"].configure(
            text=f"{resumo_mes['frequencia']}%"
        )
        self.card_frequencia["detalhe"].configure(
            text=(
                f"{resumo_mes['concluidos']} de "
                f"{resumo_mes['programados']} dias programados"
            )
        )

        sequencia = int(
            self.resumo["sequencia_atual"]
        )
        self.card_sequencia["valor"].configure(
            text=str(sequencia)
        )
        self.card_sequencia["detalhe"].configure(
            text=(
                "dia consecutivo"
                if sequencia == 1
                else "dias programados consecutivos"
            )
        )

        self.card_concluidas["valor"].configure(
            text=(
                f"{resumo_mes['concluidos']} / "
                f"{resumo_mes['programados']}"
            )
        )
        self.card_concluidas["detalhe"].configure(
            text=(
                resumo_mes["nome_mes"].capitalize()
            )
        )

    def _atualizar_rotina_hoje(self):
        hoje = self.resumo["hoje"]
        tarefas = hoje["tarefas_programadas"]

        if tarefas == ("sinan", "gal"):
            texto_programacao = (
                "Segunda-feira: as rotinas do SINAN e do GAL "
                "devem ser concluídas."
            )
        elif tarefas == ("sinan",):
            texto_programacao = (
                "De terça a sexta-feira, apenas a rotina do "
                "SINAN deve ser concluída."
            )
        else:
            texto_programacao = (
                "Fim de semana: não há rotina obrigatória "
                "programada."
            )

        self.label_programacao.configure(
            text=texto_programacao
        )

        self._configurar_card_sinan(
            hoje["sinan"]
        )
        self._configurar_card_gal(
            hoje["gal"]
        )

    def _configurar_card_sinan(
        self,
        sinan: dict[str, object]
    ):
        if not sinan["programado"]:
            status = "— Não programado"
            cor = Colors.TEXT_MUTED
        elif sinan["concluido"]:
            status = "✔️ Rotina concluída"
            cor = Colors.SUCCESS
        elif (
            sinan["verificacao_obitos"]
            or sinan["atualizacao_bases"]
        ):
            status = "◐ Rotina parcialmente concluída"
            cor = self.COR_AVISO
        else:
            status = "○ Rotina pendente"
            cor = Colors.TEXT_MUTED

        detalhes = []

        detalhes.append(
            (
                "✔ Consulta de óbitos"
                if sinan["verificacao_obitos"]
                else "○ Consulta de óbitos"
            )
        )
        detalhes.append(
            (
                "✔ Bases atualizadas"
                if sinan["atualizacao_bases"]
                else "○ Atualização das bases"
            )
        )

        self.card_sinan["status"].configure(
            text=status,
            text_color=cor
        )
        self.card_sinan["detalhe"].configure(
            text="  •  ".join(detalhes)
        )

    def _configurar_card_gal(
        self,
        gal: dict[str, object]
    ):
        if not gal["programado"]:
            status = "— Não programado hoje"
            cor = Colors.TEXT_MUTED
            detalhe = (
                "O GAL é obrigatório somente às segundas-feiras."
            )
        elif gal["concluido"]:
            status = "✔️ Atualização concluída"
            cor = Colors.SUCCESS
            detalhe = self._formatar_horario(
                gal["atualizacao_em"],
                prefixo="Concluído às "
            )
        else:
            status = "○ Atualização pendente"
            cor = self.COR_AVISO
            detalhe = (
                "Aguardando a rotina semanal do GAL."
            )

        self.card_gal["status"].configure(
            text=status,
            text_color=cor
        )
        self.card_gal["detalhe"].configure(
            text=detalhe
        )

    def _atualizar_atividades(self):
        for widget in (
            self.container_atividades.winfo_children()
        ):
            widget.destroy()

        atividades = self.resumo[
            "atividades_recentes"
        ]

        if not atividades:
            ctk.CTkLabel(
                self.container_atividades,
                text="Nenhuma atividade operacional registrada.",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).grid(
                row=0,
                column=0,
                sticky="ew",
                pady=10
            )
            return

        hoje = date.today()

        for indice, atividade in enumerate(
            atividades
        ):
            linha = ctk.CTkFrame(
                self.container_atividades,
                fg_color=(
                    Colors.BACKGROUND
                    if indice % 2 == 0
                    else Colors.SURFACE_HOVER
                ),
                corner_radius=7
            )
            linha.grid(
                row=indice,
                column=0,
                sticky="ew",
                pady=(
                    (0, 6)
                    if indice < len(atividades) - 1
                    else 0
                )
            )
            linha.grid_columnconfigure(
                1,
                weight=1
            )

            ctk.CTkLabel(
                linha,
                text="✔",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=13,
                    weight="bold"
                ),
                text_color=Colors.SUCCESS
            ).grid(
                row=0,
                column=0,
                padx=(13, 10),
                pady=11
            )

            ctk.CTkLabel(
                linha,
                text=atividade["titulo"],
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12,
                    weight="bold"
                ),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w"
            ).grid(
                row=0,
                column=1,
                sticky="w",
                pady=11
            )

            horario = atividade["horario"]
            diferenca = (
                hoje
                - atividade["data_referencia"]
            ).days

            if diferenca == 0:
                texto_data = (
                    f"Hoje, {horario.strftime('%H:%M')}"
                )
            elif diferenca == 1:
                texto_data = (
                    f"Ontem, {horario.strftime('%H:%M')}"
                )
            else:
                texto_data = horario.strftime(
                    "%d/%m/%Y, %H:%M"
                )

            ctk.CTkLabel(
                linha,
                text=texto_data,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="e"
            ).grid(
                row=0,
                column=2,
                sticky="e",
                padx=(12, 13),
                pady=11
            )

    # ------------------------------------------------------------------
    # Calendário estilo GitHub
    # ------------------------------------------------------------------

    def desenhar_calendario(self):
        if (
            self.resumo is None
            or not hasattr(
                self,
                "canvas_calendario"
            )
        ):
            return

        canvas = self.canvas_calendario
        canvas.delete("all")

        largura = max(
            canvas.winfo_width(),
            520
        )

        margem_esquerda = 48
        margem_direita = 18
        topo = 31
        gap = 3 if largura >= 760 else 2

        largura_disponivel = (
            largura
            - margem_esquerda
            - margem_direita
        )

        celula = max(
            6,
            min(
                11,
                int(
                    (
                        largura_disponivel
                        - 52 * gap
                    )
                    / 53
                )
            )
        )

        passo = celula + gap
        primeira_data = date(
            self.resumo["calendario"]["ano"],
            1,
            1
        )
        primeira_segunda = (
            primeira_data
            - timedelta(
                days=primeira_data.weekday()
            )
        )

        dias_por_data = {
            item["data"]: item
            for item in self.resumo[
                "calendario"
            ]["dias"]
        }

        fonte_pequena = (
            "Segoe UI",
            8
        )

        for texto, linha in (
            ("Seg", 0),
            ("Qua", 2),
            ("Sex", 4)
        ):
            y = (
                topo
                + linha * passo
                + celula / 2
            )
            canvas.create_text(
                margem_esquerda - 8,
                y,
                text=texto,
                fill=Colors.TEXT_MUTED,
                font=fonte_pequena,
                anchor="e"
            )

        meses_desenhados = set()

        for coluna in range(53):
            inicio_semana = (
                primeira_segunda
                + timedelta(
                    days=coluna * 7
                )
            )

            for linha in range(7):
                dia = (
                    inicio_semana
                    + timedelta(days=linha)
                )

                if dia.year != primeira_data.year:
                    continue

                item = dias_por_data.get(dia)

                if item is None:
                    continue

                x1 = (
                    margem_esquerda
                    + coluna * passo
                )
                y1 = topo + linha * passo
                x2 = x1 + celula
                y2 = y1 + celula

                cor = self.CORES_NIVEIS.get(
                    item["nivel"],
                    self.COR_CALENDARIO_VAZIO
                )

                if item["estado"] == "futuro":
                    cor = self.COR_CALENDARIO_VAZIO

                canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=cor,
                    outline=self.COR_CALENDARIO_BORDA,
                    width=1
                )

                if (
                    dia.day <= 7
                    and dia.month not in meses_desenhados
                ):
                    meses_desenhados.add(
                        dia.month
                    )
                    canvas.create_text(
                        x1,
                        13,
                        text=(
                            self.dashboard_service
                            .MESES_CURTOS[
                                dia.month - 1
                            ]
                        ),
                        fill=Colors.TEXT_SECONDARY,
                        font=(
                            "Segoe UI",
                            8
                        ),
                        anchor="w"
                    )

        self.label_contribuicoes.configure(
            text=(
                f"{self.resumo['calendario']['contribuicoes']} "
                f"rotinas concluídas em "
                f"{self.resumo['calendario']['ano']}"
            )
        )

    # ------------------------------------------------------------------
    # Responsividade e utilitários
    # ------------------------------------------------------------------

    def _ao_redimensionar(self, event=None):
        largura = (
            event.width
            if event is not None
            else self.winfo_width()
        )

        if largura <= 1:
            return

        vertical = largura < 760

        if self._layout_vertical == vertical:
            return

        if vertical:
            for indice, card in enumerate(
                (
                    self.card_frequencia,
                    self.card_sequencia,
                    self.card_concluidas
                )
            ):
                card["frame"].grid_configure(
                    row=indice,
                    column=0,
                    sticky="ew",
                    padx=0,
                    pady=(
                        (0, 8)
                        if indice < 2
                        else 0
                    )
                )

            self.container_indicadores.grid_columnconfigure(
                0,
                weight=1
            )
            self.container_indicadores.grid_columnconfigure(
                (1, 2),
                weight=0
            )

            self.card_sinan["frame"].grid_configure(
                row=2,
                column=0,
                columnspan=2,
                padx=20,
                pady=(0, 8)
            )
            self.card_gal["frame"].grid_configure(
                row=3,
                column=0,
                columnspan=2,
                padx=20,
                pady=(0, 20)
            )

        else:
            self.container_indicadores.grid_columnconfigure(
                (0, 1, 2),
                weight=1,
                uniform="indicadores"
            )

            for indice, card in enumerate(
                (
                    self.card_frequencia,
                    self.card_sequencia,
                    self.card_concluidas
                )
            ):
                card["frame"].grid_configure(
                    row=0,
                    column=indice,
                    sticky="nsew",
                    padx=(
                        (0, 6)
                        if indice == 0
                        else (
                            (6, 0)
                            if indice == 2
                            else 6
                        )
                    ),
                    pady=0
                )

            self.card_sinan["frame"].grid_configure(
                row=2,
                column=0,
                columnspan=1,
                padx=(20, 6),
                pady=(0, 20)
            )
            self.card_gal["frame"].grid_configure(
                row=2,
                column=1,
                columnspan=1,
                padx=(6, 20),
                pady=(0, 20)
            )

        self._layout_vertical = vertical

    def _formatar_horario(
        self,
        horario_iso,
        prefixo: str = ""
    ) -> str:
        if not horario_iso:
            return "Sem horário registrado"

        try:
            horario = datetime.fromisoformat(
                horario_iso
            )
        except ValueError:
            return "Horário registrado"

        return (
            prefixo
            + horario.strftime("%H:%M")
        )

    def _ao_destruir(self, event):
        if event.widget is not self:
            return

        self._pagina_destruida = True

        if self._atualizacao_id is not None:
            try:
                self.after_cancel(
                    self._atualizacao_id
                )
            except Exception:
                pass

            self._atualizacao_id = None
