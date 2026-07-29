from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from app.gui.themes.colors import Colors
from app.services.checkpoint_service import CheckpointService


class SinanPage(ctk.CTkFrame):
    """
    Página SINAN com duas subabas:

    - Consulta: checkpoints de Dengue e Chikungunya.
    - Bases: download e atualização das bases.

    Nesta etapa, os botões de conferência validam a interface
    e a persistência local. A automação será conectada depois.
    """

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.pasta_destino = None
        self.progresso_atual = 0
        self.checkpoint_service = CheckpointService()

        self.layout_checkpoints_vertical = None
        self.layout_botoes_bases = None
        self._redimensionamento_agendado = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.criar_cabecalho()
        self.criar_subabas()
        self.criar_aba_consulta()
        self.criar_aba_bases()

        self.atualizar_painel_rotina()

        self.bind(
            "<Configure>",
            self.ao_redimensionar
        )

        self.after(
            100,
            self.ajustar_layout_responsivo
        )


    # ------------------------------------------------------------------
    # Estrutura geral
    # ------------------------------------------------------------------

    def criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.cabecalho = cabecalho
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(34, 18)
        )

        ctk.CTkLabel(
            cabecalho,
            text="SINAN",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Consultas de vigilância e gerenciamento "
                "das bases de dados do SINAN."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).pack(
            fill="x",
            pady=(5, 0)
        )

    def criar_subabas(self):
        self.abas_sinan = ctk.CTkTabview(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            segmented_button_fg_color=Colors.BORDER,
            segmented_button_selected_color=Colors.PRIMARY,
            segmented_button_selected_hover_color=(
                Colors.BUTTON_HOVER
            ),
            segmented_button_unselected_color=Colors.BUTTON,
            segmented_button_unselected_hover_color=(
                Colors.BUTTON_HOVER
            ),
            text_color=Colors.TEXT_PRIMARY
        )
        self.abas_sinan.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=34,
            pady=(0, 30)
        )

        self.abas_sinan.add("Consulta")
        self.abas_sinan.add("Bases")

        # O CTkTabview não expõe diretamente todas as opções
        # visuais da barra segmentada. A configuração abaixo deixa
        # as subabas maiores, com texto mais forte e melhor contraste.
        try:
            self.abas_sinan._segmented_button.configure(
                width=380,
                height=46,
                corner_radius=8,
                border_width=1,
                dynamic_resizing=False,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=14,
                    weight="bold"
                )
            )
        except (AttributeError, TypeError, ValueError):
            # Mantém compatibilidade com versões do CustomTkinter
            # que não aceitem alguma configuração interna.
            pass

        self.tab_consulta_base = self.abas_sinan.tab(
            "Consulta"
        )
        self.tab_bases_base = self.abas_sinan.tab(
            "Bases"
        )

        for aba_base in (
            self.tab_consulta_base,
            self.tab_bases_base
        ):
            aba_base.configure(
                fg_color=Colors.BACKGROUND
            )
            aba_base.grid_columnconfigure(
                0,
                weight=1
            )
            aba_base.grid_rowconfigure(
                0,
                weight=1
            )

        # Cada subaba recebe seu próprio CTkScrollableFrame.
        # Assim, a barra e a roda do mouse controlam diretamente
        # o conteúdo da subaba visível.
        self.tab_consulta = ctk.CTkScrollableFrame(
            self.tab_consulta_base,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            orientation="vertical",
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )
        self.tab_consulta.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.tab_consulta.grid_columnconfigure(
            0,
            weight=1
        )

        self.tab_bases = ctk.CTkScrollableFrame(
            self.tab_bases_base,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            orientation="vertical",
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )
        self.tab_bases.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.tab_bases.grid_columnconfigure(
            0,
            weight=1
        )

    # ------------------------------------------------------------------
    # Aba Consulta
    # ------------------------------------------------------------------

    def criar_aba_consulta(self):
        self.criar_resumo_consulta()
        self.criar_titulo_checkpoints_individuais()
        self.criar_checkpoints_consulta()
        self.criar_orientacao_consulta()

    def criar_resumo_consulta(self):
        """
        Cria o resumo consolidado da verificação.

        O bloco se diferencia dos cards individuais pela estrutura
        de painel-resumo: cabeçalho interno, progresso consolidado
        e indicadores gerais da rotina.
        """

        painel = self._criar_painel(
            self.tab_consulta,
            linha=0,
            pady=(30, 18)
        )
        painel.grid_columnconfigure(0, weight=1)

        cabecalho_resumo = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        cabecalho_resumo.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(12, 0)
        )
        cabecalho_resumo.grid_columnconfigure(
            1,
            weight=1
        )

        indicador = ctk.CTkFrame(
            cabecalho_resumo,
            width=38,
            height=38,
            fg_color=Colors.BUTTON,
            corner_radius=7
        )
        indicador.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(12, 12),
            pady=12
        )
        indicador.grid_propagate(False)

        ctk.CTkLabel(
            indicador,
            text="✓",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            cabecalho_resumo,
            text="RESUMO DA ROTINA",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 14),
            pady=(11, 1)
        )

        ctk.CTkLabel(
            cabecalho_resumo,
            text="Verificação de óbitos",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=1,
            sticky="nw",
            padx=(0, 14),
            pady=(0, 11)
        )

        self.label_descricao_resumo = ctk.CTkLabel(
            painel,
            text=(
                "A rotina somente será concluída após "
                "a conferência de Dengue e Chikungunya."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_descricao_resumo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(16, 12)
        )

        cabecalho_progresso = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        cabecalho_progresso.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22
        )
        cabecalho_progresso.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            cabecalho_progresso,
            text="Progresso da conferência",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.label_progresso_obitos = ctk.CTkLabel(
            cabecalho_progresso,
            text="0 de 2 conferências concluídas",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        )
        self.label_progresso_obitos.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.barra_resumo_obitos = ctk.CTkProgressBar(
            painel,
            height=8,
            corner_radius=4,
            fg_color=Colors.BACKGROUND,
            progress_color=Colors.PRIMARY
        )
        self.barra_resumo_obitos.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(8, 16)
        )
        self.barra_resumo_obitos.set(0)

        indicadores = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        indicadores.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22
        )
        indicadores.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="resumo_rotina"
        )

        bloco_obitos = ctk.CTkFrame(
            indicadores,
            fg_color=Colors.BACKGROUND,
            corner_radius=6
        )
        bloco_obitos.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6)
        )

        ctk.CTkLabel(
            bloco_obitos,
            text="VERIFICAÇÃO DE ÓBITOS",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).pack(
            fill="x",
            padx=12,
            pady=(10, 3)
        )

        self.label_rotina_obitos = ctk.CTkLabel(
            bloco_obitos,
            text="○ Verificação de óbitos pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_rotina_obitos.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        bloco_rotina = ctk.CTkFrame(
            indicadores,
            fg_color=Colors.BACKGROUND,
            corner_radius=6
        )
        bloco_rotina.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0)
        )

        ctk.CTkLabel(
            bloco_rotina,
            text="ROTINA DIÁRIA",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).pack(
            fill="x",
            padx=12,
            pady=(10, 3)
        )

        self.label_rotina_completa = ctk.CTkLabel(
            bloco_rotina,
            text="○ Rotina diária completa: pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_rotina_completa.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        self.botao_resetar_consulta = ctk.CTkButton(
            painel,
            text="↻ Resetar checkpoints da consulta",
            command=self.resetar_checkpoints_consulta,
            width=220,
            height=36,
            corner_radius=6,
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
        self.botao_resetar_consulta.grid(
            row=5,
            column=0,
            sticky="w",
            padx=22,
            pady=(16, 20)
        )

    def criar_titulo_checkpoints_individuais(self):
        """
        Apresenta os checkpoints específicos abaixo do resumo.
        """

        cabecalho = ctk.CTkFrame(
            self.tab_consulta,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=8,
            pady=(4, 10)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Conferências individuais",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew"
        )

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Confira separadamente cada agravo para "
                "completar a verificação de óbitos."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(3, 0)
        )

    def criar_checkpoints_consulta(self):
        container = ctk.CTkFrame(
            self.tab_consulta,
            fg_color="transparent"
        )
        self.container_checkpoints = container
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=6
        )
        container.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="checkpoint"
        )

        self.card_dengue = self.criar_card_checkpoint(
            master=container,
            coluna=0,
            titulo="Dengue",
            descricao=(
                "Consulta e conferência dos óbitos "
                "classificados como Dengue."
            ),
            comando=self.concluir_dengue
        )

        self.card_chikungunya = self.criar_card_checkpoint(
            master=container,
            coluna=1,
            titulo="Chikungunya",
            descricao=(
                "Consulta e conferência dos óbitos "
                "classificados como Chikungunya."
            ),
            comando=self.concluir_chikungunya
        )

        container.bind(
            "<Configure>",
            self.ajustar_layout_checkpoints
        )

    def criar_card_checkpoint(
        self,
        master,
        coluna: int,
        titulo: str,
        descricao: str,
        comando
    ) -> dict:
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=(
                (0, 8)
                if coluna == 0
                else (8, 0)
            )
        )
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=titulo,
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
            pady=(20, 5)
        )

        label_descricao = ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=300
        )
        label_descricao.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20
        )

        label_status = ctk.CTkLabel(
            card,
            text="○ Aguardando",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        label_status.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        label_horario = ctk.CTkLabel(
            card,
            text="Ainda não conferido",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        label_horario.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20
        )

        botao = ctk.CTkButton(
            card,
            text="✓ Marcar como conferido",
            command=comando,
            height=36,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        botao.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 20)
        )

        return {
            "frame": card,
            "descricao": label_descricao,
            "status": label_status,
            "horario": label_horario,
            "botao": botao
        }

    def criar_orientacao_consulta(self):
        painel = self._criar_painel(
            self.tab_consulta,
            linha=3,
            pady=(18, 0)
        )
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Fluxo planejado",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(16, 5)
        )

        self.label_fluxo_consulta = ctk.CTkLabel(
            painel,
            text=(
                "Dengue → conferência humana → pressione 0 "
                "ou confirme na tela → Chikungunya → "
                "conferência humana → rotina concluída."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=690
        )
        self.label_fluxo_consulta.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 8)
        )

        self.label_observacao_consulta = ctk.CTkLabel(
            painel,
            text=(
                "Nesta etapa, os botões validam os dois "
                "checkpoints e o banco local. A automação "
                "será conectada em seguida."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=690
        )
        self.label_observacao_consulta.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 16)
        )

    # ------------------------------------------------------------------
    # Aba Bases
    # ------------------------------------------------------------------

    def criar_aba_bases(self):
        self.criar_painel_status()
        self.criar_painel_progresso()
        self.criar_painel_operacoes()

    def criar_painel_status(self):
        painel = self._criar_painel(
            self.tab_bases,
            linha=0,
            pady=(30, 0)
        )
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Status da base",
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
            padx=22,
            pady=(20, 4)
        )

        self.label_status_base = ctk.CTkLabel(
            painel,
            text="Nenhuma base disponível",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_status_base.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22
        )

        self.label_checkpoint_bases = ctk.CTkLabel(
            painel,
            text="○ Atualização das bases pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_checkpoint_bases.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(5, 0)
        )

        ctk.CTkFrame(
            painel,
            height=1,
            fg_color=Colors.DIVIDER
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=18
        )

        ctk.CTkLabel(
            painel,
            text="Pasta de destino",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22
        )

        self.label_pasta = ctk.CTkLabel(
            painel,
            text="📁 Nenhuma pasta selecionada",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_pasta.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(5, 16)
        )

        botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_botoes_bases = botoes

        botoes.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 22)
        )

        self.botao_selecionar_pasta = self._criar_botao(
            botoes,
            "📁 Selecionar pasta",
            self.selecionar_pasta,
            160
        )

        self.botao_remover_pasta = self._criar_botao(
            botoes,
            "✕ Remover seleção",
            self.remover_pasta,
            160,
            transparente=True,
            estado="disabled"
        )

        self.botao_baixar = ctk.CTkButton(
            botoes,
            text="↓ Baixar bases",
            command=self.iniciar_download,
            width=145,
            height=38,
            corner_radius=6,
            state="disabled",
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )

        self.botao_concluir_bases = self._criar_botao(
            botoes,
            "✓ Concluir atualização",
            self.concluir_atualizacao_bases,
            165
        )
        self.botoes_bases = [
            self.botao_selecionar_pasta,
            self.botao_remover_pasta,
            self.botao_baixar,
            self.botao_concluir_bases
        ]

        botoes.bind(
            "<Configure>",
            self.ajustar_layout_botoes_bases
        )

    def criar_painel_progresso(self):
        painel = self._criar_painel(
            self.tab_bases,
            linha=1,
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
            padx=22,
            pady=(18, 10)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Progresso",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.label_porcentagem = ctk.CTkLabel(
            cabecalho,
            text="0%",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="e"
        )
        self.label_porcentagem.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.barra_progresso = ctk.CTkProgressBar(
            painel,
            height=10,
            corner_radius=5,
            fg_color=Colors.BACKGROUND,
            progress_color=Colors.PRIMARY
        )
        self.barra_progresso.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22
        )
        self.barra_progresso.set(0)

        self.label_progresso = ctk.CTkLabel(
            painel,
            text="Aguardando início do download.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_progresso.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(10, 18)
        )

    def criar_painel_operacoes(self):
        painel = self._criar_painel(
            self.tab_bases,
            linha=2,
            pady=(16, 20)
        )

        ctk.CTkLabel(
            painel,
            text="Últimas operações",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).pack(
            fill="x",
            padx=22,
            pady=(18, 6)
        )

        self.label_operacao = ctk.CTkLabel(
            painel,
            text="Nenhuma operação realizada.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_operacao.pack(
            fill="x",
            padx=22,
            pady=(0, 18)
        )

    # ------------------------------------------------------------------
    # Layout responsivo
    # ------------------------------------------------------------------

    def ao_redimensionar(self, event):
        """
        Agrupa várias notificações de redimensionamento para evitar
        reposicionamentos excessivos durante o movimento da janela.
        """

        if self._redimensionamento_agendado is not None:
            try:
                self.after_cancel(
                    self._redimensionamento_agendado
                )
            except Exception:
                pass

        self._redimensionamento_agendado = self.after(
            80,
            self.ajustar_layout_responsivo
        )

    def ajustar_layout_responsivo(self):
        self._redimensionamento_agendado = None

        largura_pagina = max(
            self.winfo_width(),
            1
        )

        if largura_pagina < 720:
            margem_cabecalho = 16
            margem_abas = 10
        elif largura_pagina < 980:
            margem_cabecalho = 26
            margem_abas = 20
        else:
            margem_cabecalho = 40
            margem_abas = 34

        self.cabecalho.grid_configure(
            padx=margem_cabecalho
        )
        self.abas_sinan.grid_configure(
            padx=margem_abas
        )

        self.ajustar_layout_checkpoints()
        self.ajustar_layout_botoes_bases()
        self.ajustar_quebra_textos()

    def ajustar_layout_checkpoints(self, event=None):
        if not hasattr(self, "container_checkpoints"):
            return

        largura = (
            event.width
            if event is not None
            else self.container_checkpoints.winfo_width()
        )

        if largura <= 1:
            return

        usar_vertical = largura < 720

        if usar_vertical:
            self.container_checkpoints.grid_columnconfigure(
                0,
                weight=1,
                uniform=""
            )
            self.container_checkpoints.grid_columnconfigure(
                1,
                weight=0,
                uniform=""
            )

            self.card_dengue["frame"].grid_configure(
                row=0,
                column=0,
                sticky="ew",
                padx=0,
                pady=(0, 10)
            )
            self.card_chikungunya["frame"].grid_configure(
                row=1,
                column=0,
                sticky="ew",
                padx=0,
                pady=0
            )

            wraplength = max(
                largura - 80,
                220
            )
        else:
            self.container_checkpoints.grid_columnconfigure(
                (0, 1),
                weight=1,
                uniform="checkpoint"
            )

            self.card_dengue["frame"].grid_configure(
                row=0,
                column=0,
                sticky="nsew",
                padx=(0, 8),
                pady=0
            )
            self.card_chikungunya["frame"].grid_configure(
                row=0,
                column=1,
                sticky="nsew",
                padx=(8, 0),
                pady=0
            )

            wraplength = max(
                int(largura / 2) - 70,
                220
            )

        self.card_dengue["descricao"].configure(
            wraplength=wraplength
        )
        self.card_chikungunya["descricao"].configure(
            wraplength=wraplength
        )

        self.layout_checkpoints_vertical = usar_vertical

    def ajustar_layout_botoes_bases(self, event=None):
        if not hasattr(self, "container_botoes_bases"):
            return

        largura = (
            event.width
            if event is not None
            else self.container_botoes_bases.winfo_width()
        )

        if largura <= 1:
            return

        if largura < 470:
            colunas = 1
        elif largura < 900:
            colunas = 2
        else:
            colunas = 4

        if (
            self.layout_botoes_bases == colunas
            and event is not None
        ):
            return

        for indice in range(4):
            self.container_botoes_bases.grid_columnconfigure(
                indice,
                weight=(
                    1
                    if indice < colunas
                    else 0
                ),
                uniform=(
                    "botoes_bases"
                    if indice < colunas
                    else ""
                )
            )

        for indice, botao in enumerate(
            self.botoes_bases
        ):
            botao.grid_forget()

            linha = indice // colunas
            coluna = indice % colunas

            botao.grid(
                row=linha,
                column=coluna,
                sticky="ew",
                padx=(
                    (0, 5)
                    if coluna == 0 and colunas > 1
                    else (
                        (5, 0)
                        if coluna == colunas - 1
                        else 5
                    )
                ),
                pady=(
                    (0, 5)
                    if linha == 0
                    else (5, 0)
                )
            )

        self.layout_botoes_bases = colunas

    def ajustar_quebra_textos(self):
        if hasattr(self, "tab_consulta"):
            largura_consulta = (
                self.tab_consulta.winfo_width()
            )

            if largura_consulta > 1:
                wrap_consulta = max(
                    largura_consulta - 80,
                    220
                )

                self.label_descricao_resumo.configure(
                    wraplength=wrap_consulta
                )
                self.label_fluxo_consulta.configure(
                    wraplength=wrap_consulta
                )
                self.label_observacao_consulta.configure(
                    wraplength=wrap_consulta
                )

        if hasattr(self, "tab_bases"):
            largura_bases = self.tab_bases.winfo_width()

            if largura_bases > 1:
                self.label_pasta.configure(
                    wraplength=max(
                        largura_bases - 90,
                        220
                    )
                )

    # ------------------------------------------------------------------
    # Ações dos checkpoints
    # ------------------------------------------------------------------

    def concluir_dengue(self):
        self.checkpoint_service.marcar_obito_concluido(
            CheckpointService.AGRAVO_DENGUE
        )
        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Checkpoint de Dengue marcado como conferido."
        )

    def concluir_chikungunya(self):
        self.checkpoint_service.marcar_obito_concluido(
            CheckpointService.AGRAVO_CHIKUNGUNYA
        )
        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Checkpoint de Chikungunya marcado como conferido."
        )

    def resetar_checkpoints_consulta(self):
        self.checkpoint_service.resetar_verificacao_obitos()
        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Checkpoints da consulta foram resetados."
        )

    # Compatibilidade com a versão antiga.
    def concluir_verificacao_obitos(self):
        self.checkpoint_service.marcar_verificacao_obitos()
        self.atualizar_painel_rotina()

    def concluir_atualizacao_bases(self):
        self.checkpoint_service.marcar_atualizacao_bases()
        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Atualização das bases marcada como concluída."
        )

    def resetar_checkpoints(self):
        self.checkpoint_service.resetar_rotina()
        self.atualizar_painel_rotina()

    # ------------------------------------------------------------------
    # Atualização visual
    # ------------------------------------------------------------------

    def atualizar_painel_rotina(self):
        rotina = self.checkpoint_service.obter_rotina()
        checkpoints = rotina["checkpoints_obitos"]

        quantidade_concluida = sum(
            1
            for checkpoint in checkpoints.values()
            if (
                checkpoint["status"]
                == CheckpointService.STATUS_CONCLUIDO
            )
        )

        self.barra_resumo_obitos.set(
            quantidade_concluida / 2
        )
        self.label_progresso_obitos.configure(
            text=(
                f"{quantidade_concluida} de 2 "
                "conferências concluídas"
            )
        )

        self.barra_resumo_obitos.configure(
            progress_color=(
                Colors.SUCCESS
                if quantidade_concluida == 2
                else Colors.PRIMARY
            )
        )

        self.atualizar_card_checkpoint(
            self.card_dengue,
            checkpoints[
                CheckpointService.AGRAVO_DENGUE
            ]
        )
        self.atualizar_card_checkpoint(
            self.card_chikungunya,
            checkpoints[
                CheckpointService.AGRAVO_CHIKUNGUNYA
            ]
        )

        if rotina["verificacao_obitos"]:
            self.label_rotina_obitos.configure(
                text=(
                    "✓ Verificação de óbitos concluída"
                    f"{self.formatar_horario(
                        rotina['verificacao_obitos_em']
                    )}"
                ),
                text_color=Colors.SUCCESS
            )
        else:
            self.label_rotina_obitos.configure(
                text="○ Verificação de óbitos pendente",
                text_color=Colors.TEXT_MUTED
            )

        if rotina["atualizacao_bases"]:
            self.label_checkpoint_bases.configure(
                text=(
                    "✓ Atualização das bases concluída"
                    f"{self.formatar_horario(
                        rotina['atualizacao_bases_em']
                    )}"
                ),
                text_color=Colors.SUCCESS
            )
            self.botao_concluir_bases.configure(
                text="✓ Atualização concluída",
                state="disabled"
            )
        else:
            self.label_checkpoint_bases.configure(
                text="○ Atualização das bases pendente",
                text_color=Colors.TEXT_MUTED
            )
            self.botao_concluir_bases.configure(
                text="✓ Concluir atualização",
                state="normal"
            )

        if rotina["rotina_concluida"]:
            self.label_rotina_completa.configure(
                text="✓ Rotina diária completa: concluída",
                text_color=Colors.SUCCESS
            )
        else:
            self.label_rotina_completa.configure(
                text="○ Rotina diária completa: pendente",
                text_color=Colors.TEXT_MUTED
            )

    def atualizar_card_checkpoint(
        self,
        componentes: dict,
        checkpoint: dict
    ):
        status = checkpoint["status"]

        apresentacao = {
            CheckpointService.STATUS_AGUARDANDO: (
                "○ Aguardando",
                Colors.TEXT_MUTED,
                "Ainda não conferido"
            ),
            CheckpointService.STATUS_EXECUTANDO: (
                "● Executando consulta",
                Colors.PRIMARY,
                "Automação em andamento"
            ),
            CheckpointService.STATUS_AGUARDANDO_CONFERENCIA: (
                "◉ Aguardando conferência",
                Colors.PRIMARY,
                "Revise os resultados no SINAN"
            ),
            CheckpointService.STATUS_CONCLUIDO: (
                "✓ Conferido",
                Colors.SUCCESS,
                self.texto_horario_checkpoint(
                    checkpoint
                )
            ),
            CheckpointService.STATUS_ERRO: (
                "✕ Erro na consulta",
                Colors.TEXT_SECONDARY,
                "Execute a consulta novamente"
            )
        }

        texto, cor, detalhe = apresentacao.get(
            status,
            apresentacao[
                CheckpointService.STATUS_AGUARDANDO
            ]
        )

        componentes["status"].configure(
            text=texto,
            text_color=cor
        )
        componentes["horario"].configure(
            text=detalhe
        )

        if status == CheckpointService.STATUS_CONCLUIDO:
            componentes["botao"].configure(
                text="✓ Conferido",
                state="disabled"
            )
        else:
            componentes["botao"].configure(
                text="✓ Marcar como conferido",
                state="normal"
            )

    def texto_horario_checkpoint(
        self,
        checkpoint: dict
    ) -> str:
        horario = checkpoint.get(
            "confirmado_em"
        )

        if not horario:
            return "Conferido"

        return (
            "Conferido às "
            + datetime.fromisoformat(
                horario
            ).strftime("%H:%M")
        )

    def formatar_horario(self, horario_iso):
        if not horario_iso:
            return ""

        return (
            " às "
            + datetime.fromisoformat(
                horario_iso
            ).strftime("%H:%M")
        )

    # ------------------------------------------------------------------
    # Download de bases
    # ------------------------------------------------------------------

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Selecione a pasta de destino"
        )

        if not pasta:
            return

        self.pasta_destino = pasta

        self.label_pasta.configure(
            text=f"📁 {pasta}",
            text_color=Colors.TEXT_SECONDARY
        )
        self.botao_remover_pasta.configure(
            state="normal"
        )
        self.botao_baixar.configure(
            state="normal",
            text="↓ Baixar bases"
        )
        self.label_progresso.configure(
            text=(
                "Pasta selecionada. "
                "A atualização pode ser iniciada."
            )
        )
        self.registrar_operacao(
            "Pasta de destino selecionada."
        )

    def remover_pasta(self):
        if self.pasta_destino is None:
            return

        self.pasta_destino = None
        self.progresso_atual = 0

        self.label_pasta.configure(
            text="📁 Nenhuma pasta selecionada",
            text_color=Colors.TEXT_MUTED
        )
        self.botao_remover_pasta.configure(
            state="disabled"
        )
        self.botao_baixar.configure(
            state="disabled",
            text="↓ Baixar bases"
        )
        self.barra_progresso.set(0)
        self.label_porcentagem.configure(
            text="0%"
        )
        self.label_progresso.configure(
            text=(
                "Seleção removida. "
                "Escolha uma pasta de destino."
            )
        )
        self.registrar_operacao(
            "Seleção da pasta de destino removida."
        )

    def iniciar_download(self):
        if self.pasta_destino is None:
            return

        self.progresso_atual = 0

        self.botao_selecionar_pasta.configure(
            state="disabled"
        )
        self.botao_remover_pasta.configure(
            state="disabled"
        )
        self.botao_baixar.configure(
            state="disabled",
            text="↓ Baixando..."
        )
        self.label_status_base.configure(
            text="Download em andamento",
            text_color=Colors.PRIMARY
        )
        self.label_progresso.configure(
            text=(
                "Preparando o download "
                "da base do SINAN..."
            )
        )
        self.registrar_operacao(
            "Download das bases iniciado."
        )
        self.barra_progresso.set(0)
        self.label_porcentagem.configure(
            text="0%"
        )

        self.simular_progresso()

    def simular_progresso(self):
        self.progresso_atual += 5

        self.barra_progresso.set(
            self.progresso_atual / 100
        )
        self.label_porcentagem.configure(
            text=f"{self.progresso_atual}%"
        )

        if self.progresso_atual < 100:
            self.after(
                100,
                self.simular_progresso
            )
            return

        self.finalizar_download()

    def finalizar_download(self):
        self.label_status_base.configure(
            text="Base disponível",
            text_color=Colors.SUCCESS
        )
        self.label_progresso.configure(
            text="Download concluído com sucesso."
        )
        self.botao_selecionar_pasta.configure(
            state="normal"
        )
        self.botao_remover_pasta.configure(
            state="normal"
        )
        self.botao_baixar.configure(
            state="normal",
            text="↻ Baixar novamente"
        )

        self.checkpoint_service.marcar_atualizacao_bases()
        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Bases do SINAN atualizadas com sucesso."
        )

    # ------------------------------------------------------------------
    # Helpers visuais
    # ------------------------------------------------------------------

    def _criar_painel(
        self,
        parent,
        linha: int,
        pady
    ):
        painel = ctk.CTkFrame(
            parent,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=6,
            pady=pady
        )
        return painel

    def _criar_botao(
        self,
        parent,
        texto: str,
        comando,
        largura: int,
        transparente: bool = False,
        estado: str = "normal"
    ):
        return ctk.CTkButton(
            parent,
            text=texto,
            command=comando,
            width=largura,
            height=38,
            corner_radius=6,
            state=estado,
            fg_color=(
                "transparent"
                if transparente
                else Colors.BUTTON
            ),
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )

    def registrar_operacao(self, mensagem):
        horario = datetime.now().strftime("%H:%M:%S")

        if hasattr(self, "label_operacao"):
            self.label_operacao.configure(
                text=f"{horario} — {mensagem}"
            )