from datetime import date, datetime
import os
from pathlib import Path
import subprocess
import sys
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.gui.components.arbohub_dialog import (
    mostrar_dialogo_arbohub,
    solicitar_confirmacao_arbohub
)
from app.gui.components.confirmacao_conferencia_dialog import (
    solicitar_confirmacao_conferencia_nativa
)
from app.gui.themes.colors import Colors
from app.services.atualizacao_bases_service import (
    AtualizacaoBasesService
)
from app.services.checkpoint_service import CheckpointService
from app.services.consulta_obitos_service import (
    ConsultaObitosService
)


class SinanPage(ctk.CTkFrame):
    """
    Página SINAN com três subabas:

    - Consulta: checkpoints de Dengue e Chikungunya.
    - Bases: download e atualização das bases.
    - Relatórios: histórico das conferências realizadas.

    A subaba Consulta inicia a automação em segundo plano,
    acompanha os checkpoints e abre a confirmação humana nativa.
    """

    ETAPAS_FLUXO_CONSULTA = (
        (
            ConsultaObitosService.ETAPA_ABRIR_SINAN,
            "Abrir o SINAN",
            "Inicialização do navegador seguro."
        ),
        (
            ConsultaObitosService.ETAPA_LOGIN,
            "Login manual",
            "As credenciais são digitadas diretamente no SINAN."
        ),
        (
            ConsultaObitosService.ETAPA_DENGUE_CONSULTA,
            "Consulta de Dengue",
            "Preenchimento dos filtros e execução da pesquisa."
        ),
        (
            ConsultaObitosService.ETAPA_DENGUE_CONFERENCIA,
            "Conferência de Dengue",
            "Revisão humana e registro do resultado."
        ),
        (
            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONSULTA,
            "Consulta de Chikungunya",
            "Troca do agravo e reutilização do critério."
        ),
        (
            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONFERENCIA,
            "Conferência de Chikungunya",
            "Revisão humana e registro do resultado."
        ),
        (
            ConsultaObitosService.ETAPA_FINALIZACAO,
            "Finalização",
            "Conclusão dos checkpoints e encerramento seguro."
        )
    )

    ETAPAS_FLUXO_BASES = (
        (
            AtualizacaoBasesService.ETAPA_ACESSO,
            "Acesso ao SINAN",
            "Login manual quando solicitações ou downloads forem necessários."
        ),
        (
            AtualizacaoBasesService.ETAPA_SOLICITACOES,
            "Solicitações DBF",
            "Criar ou reutilizar as solicitações de Dengue e Chikungunya."
        ),
        (
            AtualizacaoBasesService.ETAPA_PROCESSAMENTO,
            "Processamento",
            "Acompanhar os dois números até os links ficarem disponíveis."
        ),
        (
            AtualizacaoBasesService.ETAPA_DOWNLOAD,
            "Download",
            "Baixar e validar os ZIPs pelas solicitações exatas."
        ),
        (
            AtualizacaoBasesService.ETAPA_HISTORICO,
            "Histórico",
            "Arquivar os ZIPs nas pastas anuais e mensais."
        ),
        (
            AtualizacaoBasesService.ETAPA_EXTRACAO,
            "Extração segura",
            "Confirmar DENGON e CHIKON sem interpretar registros."
        ),
        (
            AtualizacaoBasesService.ETAPA_PASTAS_TESTE,
            "Pastas de teste",
            "Atualizar Teste AB1 e Teste AB2 com backup e SHA-256."
        ),
        (
            AtualizacaoBasesService.ETAPA_BANCOS_ATUAIS,
            "Bancos atuais",
            "Atualizar dengue_AAAA.dbf e chiku_AAAA.dbf com restauração."
        ),
        (
            AtualizacaoBasesService.ETAPA_FINALIZACAO,
            "Finalização",
            "Registrar a rotina diária somente após sucesso completo."
        )
    )

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.pasta_destino = None
        self.progresso_atual = 0
        self.checkpoint_service = CheckpointService()
        self.consulta_obitos_service = ConsultaObitosService(
            checkpoint_service=self.checkpoint_service
        )
        self.atualizacao_bases_service = (
            AtualizacaoBasesService(
                checkpoint_service=self.checkpoint_service
            )
        )

        self.layout_checkpoints_vertical = None
        self.layout_botoes_bases = None
        self.layout_destinos_bases_vertical = None
        self.layout_acoes_consulta_vertical = None
        self.labels_relatorios_wrap = []
        self._redimensionamento_agendado = None
        self._polling_automacao_id = None
        self._pagina_destruida = False

        self.etapa_fluxo_atual = None
        self.estado_fluxo_atual = "aguardando"
        self.mensagem_etapa_fluxo = None

        self.etapa_bases_atual = None
        self.estado_bases_atual = "aguardando"
        self.mensagem_bases_atual = None
        self.estados_etapas_bases = {
            etapa[0]: "aguardando"
            for etapa in self.ETAPAS_FLUXO_BASES
        }
        self.mensagens_etapas_bases = {}
        self.estado_arquivos_bases = {
            "dengue": False,
            "chikungunya": False
        }
        self._correcao_manual_bases_habilitada = False
        self._agravos_pendentes_bases: list[str] = []

        self.componentes_linha_tempo = {}
        self.componentes_linha_tempo_bases = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.criar_cabecalho()
        self.criar_subabas()
        self.criar_aba_consulta()
        self.criar_aba_bases()
        self.criar_aba_relatorios()

        self.atualizar_painel_rotina()

        self.bind(
            "<Configure>",
            self.ao_redimensionar
        )

        self.after(
            100,
            self.ajustar_layout_responsivo
        )

        self.bind(
            "<Destroy>",
            self._ao_destruir_pagina,
            add="+"
        )

        self._agendar_processamento_eventos()

        self.after(
            250,
            self.atualizar_estado_bases
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
            corner_radius=0,
            border_width=0,
            border_color=Colors.BACKGROUND,
            segmented_button_fg_color=Colors.BACKGROUND,
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
        self.abas_sinan.add("Relatórios")

        # O CTkTabview não expõe diretamente todas as opções
        # visuais da barra segmentada. A configuração abaixo deixa
        # as subabas maiores, com texto mais forte e melhor contraste.
        try:
            self.abas_sinan._segmented_button.configure(
                width=510,
                height=46,
                corner_radius=8,
                border_width=0,
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
        self.tab_relatorios_base = self.abas_sinan.tab(
            "Relatórios"
        )

        for aba_base in (
            self.tab_consulta_base,
            self.tab_bases_base,
            self.tab_relatorios_base
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

        self.tab_relatorios = ctk.CTkScrollableFrame(
            self.tab_relatorios_base,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            orientation="vertical",
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )
        self.tab_relatorios.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.tab_relatorios.grid_columnconfigure(
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
            text="✅",
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=18
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

        acoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_acoes_consulta = acoes

        acoes.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(16, 8)
        )
        acoes.grid_columnconfigure(
            0,
            weight=1
        )

        self.botao_iniciar_verificacao = ctk.CTkButton(
            acoes,
            text="▶ Iniciar verificação",
            command=self.iniciar_verificacao_obitos,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_iniciar_verificacao.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6)
        )

        self.botao_resetar_consulta = ctk.CTkButton(
            acoes,
            text="↻ Resetar",
            command=self.resetar_checkpoints_consulta,
            width=130,
            height=38,
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
        self.botao_resetar_consulta.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(6, 0)
        )

        self.label_estado_automacao = ctk.CTkLabel(
            painel,
            text=(
                "Aguardando o início da verificação."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_estado_automacao.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 18)
        )

        acoes.bind(
            "<Configure>",
            self.ajustar_layout_acoes_consulta
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
            text="Aguardando automação",
            command=comando,
            height=36,
            corner_radius=6,
            state="disabled",
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
        self.painel_fluxo_consulta = painel
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Andamento da verificação",
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
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        self.label_descricao_linha_tempo = ctk.CTkLabel(
            painel,
            text=(
                "A linha do tempo acompanha, em tempo real, "
                "a etapa executada pela automação."
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
        self.label_descricao_linha_tempo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 16)
        )

        container = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_linha_tempo = container
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 8)
        )
        container.grid_columnconfigure(
            1,
            weight=1
        )

        for indice, (
            identificador,
            titulo,
            detalhe
        ) in enumerate(self.ETAPAS_FLUXO_CONSULTA):
            componentes = self._criar_item_linha_tempo(
                master=container,
                indice=indice,
                quantidade=len(
                    self.ETAPAS_FLUXO_CONSULTA
                ),
                titulo=titulo,
                detalhe=detalhe
            )

            self.componentes_linha_tempo[
                identificador
            ] = componentes

        ctk.CTkLabel(
            painel,
            text=(
                "O login permanece manual e nenhum conteúdo "
                "das linhas de resultado é lido pelo ArboHub."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=690
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 18)
        )

        self.atualizar_linha_tempo_consulta()

    def _criar_item_linha_tempo(
        self,
        master,
        indice: int,
        quantidade: int,
        titulo: str,
        detalhe: str
    ) -> dict:
        linha_item = indice * 2

        indicador = ctk.CTkFrame(
            master,
            width=30,
            height=30,
            fg_color=Colors.BUTTON,
            corner_radius=15,
            border_width=1,
            border_color=Colors.BORDER
        )
        indicador.grid(
            row=linha_item,
            column=0,
            sticky="n",
            padx=(0, 12)
        )
        indicador.grid_propagate(False)

        label_indicador = ctk.CTkLabel(
            indicador,
            text=str(indice + 1),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED
        )
        label_indicador.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        textos = ctk.CTkFrame(
            master,
            fg_color="transparent"
        )
        textos.grid(
            row=linha_item,
            column=1,
            sticky="ew",
            pady=(0, 4)
        )
        textos.grid_columnconfigure(
            0,
            weight=1
        )

        label_titulo = ctk.CTkLabel(
            textos,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        label_titulo.grid(
            row=0,
            column=0,
            sticky="ew"
        )

        label_detalhe = ctk.CTkLabel(
            textos,
            text=detalhe,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        label_detalhe.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(2, 0)
        )

        conector = None

        if indice < quantidade - 1:
            conector = ctk.CTkFrame(
                master,
                width=2,
                height=22,
                fg_color=Colors.BORDER,
                corner_radius=0
            )
            conector.grid(
                row=linha_item + 1,
                column=0,
                sticky="ns",
                pady=3
            )
            conector.grid_propagate(False)

        return {
            "indicador": indicador,
            "label_indicador": label_indicador,
            "titulo": label_titulo,
            "detalhe": label_detalhe,
            "detalhe_padrao": detalhe,
            "conector": conector
        }

    def atualizar_linha_tempo_consulta(
        self,
        rotina: dict | None = None
    ):
        if not self.componentes_linha_tempo:
            return

        rotina = (
            rotina
            or self.checkpoint_service.obter_rotina()
        )

        etapas = [
            item[0]
            for item in self.ETAPAS_FLUXO_CONSULTA
        ]

        estados = {
            etapa: "aguardando"
            for etapa in etapas
        }

        executando = (
            self.consulta_obitos_service.esta_em_execucao()
        )

        if (
            executando
            and self.etapa_fluxo_atual in estados
        ):
            indice_atual = etapas.index(
                self.etapa_fluxo_atual
            )

            for etapa in etapas[:indice_atual]:
                estados[etapa] = "concluido"

            estados[
                self.etapa_fluxo_atual
            ] = "executando"

        elif (
            self.estado_fluxo_atual
            in {"erro", "cancelado"}
            and self.etapa_fluxo_atual in estados
        ):
            indice_atual = etapas.index(
                self.etapa_fluxo_atual
            )

            for etapa in etapas[:indice_atual]:
                estados[etapa] = "concluido"

            estados[
                self.etapa_fluxo_atual
            ] = self.estado_fluxo_atual

        else:
            checkpoints = rotina[
                "checkpoints_obitos"
            ]

            dengue = checkpoints[
                CheckpointService.AGRAVO_DENGUE
            ]["status"]

            chikungunya = checkpoints[
                CheckpointService.AGRAVO_CHIKUNGUNYA
            ]["status"]

            if rotina["verificacao_obitos"]:
                for etapa in etapas:
                    estados[etapa] = "concluido"

            elif dengue != CheckpointService.STATUS_AGUARDANDO:
                estados[
                    ConsultaObitosService.ETAPA_ABRIR_SINAN
                ] = "concluido"
                estados[
                    ConsultaObitosService.ETAPA_LOGIN
                ] = "concluido"

                if (
                    dengue
                    == CheckpointService.STATUS_EXECUTANDO
                ):
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONSULTA
                    ] = "executando"

                elif (
                    dengue
                    == CheckpointService.STATUS_AGUARDANDO_CONFERENCIA
                ):
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONSULTA
                    ] = "concluido"
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONFERENCIA
                    ] = "executando"

                elif dengue == CheckpointService.STATUS_ERRO:
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONSULTA
                    ] = "erro"

                elif dengue == CheckpointService.STATUS_CONCLUIDO:
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONSULTA
                    ] = "concluido"
                    estados[
                        ConsultaObitosService.ETAPA_DENGUE_CONFERENCIA
                    ] = "concluido"

                    if (
                        chikungunya
                        == CheckpointService.STATUS_EXECUTANDO
                    ):
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONSULTA
                        ] = "executando"

                    elif (
                        chikungunya
                        == CheckpointService.STATUS_AGUARDANDO_CONFERENCIA
                    ):
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONSULTA
                        ] = "concluido"
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONFERENCIA
                        ] = "executando"

                    elif (
                        chikungunya
                        == CheckpointService.STATUS_ERRO
                    ):
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONSULTA
                        ] = "erro"

                    elif (
                        chikungunya
                        == CheckpointService.STATUS_CONCLUIDO
                    ):
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONSULTA
                        ] = "concluido"
                        estados[
                            ConsultaObitosService.ETAPA_CHIKUNGUNYA_CONFERENCIA
                        ] = "concluido"
                        estados[
                            ConsultaObitosService.ETAPA_FINALIZACAO
                        ] = "executando"

        for indice, etapa in enumerate(etapas):
            mensagem = None

            if (
                etapa == self.etapa_fluxo_atual
                and self.mensagem_etapa_fluxo
            ):
                mensagem = self.mensagem_etapa_fluxo

            self._aplicar_estado_item_linha_tempo(
                componentes=(
                    self.componentes_linha_tempo[
                        etapa
                    ]
                ),
                estado=estados[etapa],
                indice=indice,
                mensagem=mensagem
            )

        for indice, etapa in enumerate(
            etapas[:-1]
        ):
            conector = (
                self.componentes_linha_tempo[
                    etapa
                ]["conector"]
            )

            if conector is None:
                continue

            concluido = (
                estados[etapa] == "concluido"
            )

            conector.configure(
                fg_color=(
                    Colors.SUCCESS
                    if concluido
                    else Colors.BORDER
                )
            )

    def _aplicar_estado_item_linha_tempo(
        self,
        componentes: dict,
        estado: str,
        indice: int,
        mensagem: str | None = None
    ):
        configuracoes = {
            "aguardando": {
                "simbolo": str(indice + 1),
                "fundo": Colors.BUTTON,
                "borda": Colors.BORDER,
                "cor_simbolo": Colors.TEXT_MUTED,
                "cor_titulo": Colors.TEXT_SECONDARY,
                "cor_detalhe": Colors.TEXT_MUTED
            },
            "executando": {
                "simbolo": "●",
                "fundo": Colors.PRIMARY,
                "borda": Colors.PRIMARY,
                "cor_simbolo": Colors.TEXT_PRIMARY,
                "cor_titulo": Colors.TEXT_PRIMARY,
                "cor_detalhe": Colors.PRIMARY
            },
            "concluido": {
                "simbolo": "✔",
                "fundo": Colors.SUCCESS,
                "borda": Colors.SUCCESS,
                "cor_simbolo": Colors.TEXT_PRIMARY,
                "cor_titulo": Colors.TEXT_PRIMARY,
                "cor_detalhe": Colors.TEXT_SECONDARY
            },
            "erro": {
                "simbolo": "✕",
                "fundo": Colors.BUTTON,
                "borda": Colors.TEXT_SECONDARY,
                "cor_simbolo": Colors.TEXT_SECONDARY,
                "cor_titulo": Colors.TEXT_PRIMARY,
                "cor_detalhe": Colors.TEXT_SECONDARY
            },
            "cancelado": {
                "simbolo": "–",
                "fundo": Colors.BUTTON,
                "borda": Colors.TEXT_MUTED,
                "cor_simbolo": Colors.TEXT_MUTED,
                "cor_titulo": Colors.TEXT_SECONDARY,
                "cor_detalhe": Colors.TEXT_MUTED
            }
        }

        visual = configuracoes.get(
            estado,
            configuracoes["aguardando"]
        )

        componentes["indicador"].configure(
            fg_color=visual["fundo"],
            border_color=visual["borda"]
        )
        componentes["label_indicador"].configure(
            text=visual["simbolo"],
            text_color=visual["cor_simbolo"]
        )
        componentes["titulo"].configure(
            text_color=visual["cor_titulo"]
        )

        detalhe = (
            mensagem
            or (
                "Etapa concluída."
                if estado == "concluido"
                else componentes["detalhe_padrao"]
            )
        )

        componentes["detalhe"].configure(
            text=detalhe,
            text_color=visual["cor_detalhe"]
        )

    # ------------------------------------------------------------------
    # Aba Relatórios
    # ------------------------------------------------------------------

    def criar_aba_relatorios(self):
        self.filtro_agravo_relatorio = ctk.StringVar(
            value="Todos os agravos"
        )
        self.filtro_resultado_relatorio = ctk.StringVar(
            value="Todos os resultados"
        )

        self.criar_cabecalho_relatorios()
        self.criar_filtros_relatorios()
        self.criar_lista_relatorios()
        self.atualizar_relatorios()

    def criar_cabecalho_relatorios(self):
        painel = self._criar_painel(
            self.tab_relatorios,
            linha=0,
            pady=(30, 16)
        )
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Histórico de conferências",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(20, 5)
        )

        self.label_descricao_relatorios = ctk.CTkLabel(
            painel,
            text=(
                "Consulte as conferências registradas pelo "
                "ArboHub. O histórico contém somente o resultado "
                "da conferência e a observação informada pelo "
                "usuário; nenhuma linha de paciente é armazenada."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=680
        )
        self.label_descricao_relatorios.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 20)
        )

    def criar_filtros_relatorios(self):
        painel = self._criar_painel(
            self.tab_relatorios,
            linha=1,
            pady=(0, 16)
        )
        self.painel_filtros_relatorios = painel
        painel.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            painel,
            text="Filtros",
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
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(16, 10)
        )

        self.menu_agravo_relatorio = ctk.CTkOptionMenu(
            painel,
            variable=self.filtro_agravo_relatorio,
            values=[
                "Todos os agravos",
                "Dengue",
                "Chikungunya"
            ],
            command=lambda _valor: self.atualizar_relatorios(),
            height=36,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.menu_agravo_relatorio.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(20, 6),
            pady=(0, 18)
        )

        self.menu_resultado_relatorio = ctk.CTkOptionMenu(
            painel,
            variable=self.filtro_resultado_relatorio,
            values=[
                "Todos os resultados",
                "Manteve igual",
                "Mudou"
            ],
            command=lambda _valor: self.atualizar_relatorios(),
            height=36,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.menu_resultado_relatorio.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
            pady=(0, 18)
        )

        self.botao_atualizar_relatorios = ctk.CTkButton(
            painel,
            text="↻ Atualizar",
            command=self.atualizar_relatorios,
            width=120,
            height=36,
            corner_radius=6,
            fg_color="transparent",
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
        self.botao_atualizar_relatorios.grid(
            row=1,
            column=2,
            sticky="e",
            padx=(6, 20),
            pady=(0, 18)
        )

    def criar_lista_relatorios(self):
        cabecalho = ctk.CTkFrame(
            self.tab_relatorios,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 10)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="Registros",
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

        self.label_quantidade_relatorios = ctk.CTkLabel(
            cabecalho,
            text="0 registros",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        )
        self.label_quantidade_relatorios.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.container_relatorios = ctk.CTkFrame(
            self.tab_relatorios,
            fg_color="transparent"
        )
        self.container_relatorios.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=6,
            pady=(0, 24)
        )
        self.container_relatorios.grid_columnconfigure(0, weight=1)

    def atualizar_relatorios(self):
        if not hasattr(self, "container_relatorios"):
            return

        agravo_mapa = {
            "Todos os agravos": None,
            "Dengue": CheckpointService.AGRAVO_DENGUE,
            "Chikungunya": CheckpointService.AGRAVO_CHIKUNGUNYA
        }
        resultado_mapa = {
            "Todos os resultados": None,
            "Manteve igual": "manteve_igual",
            "Mudou": "mudou"
        }

        agravo = agravo_mapa.get(
            self.filtro_agravo_relatorio.get()
        )
        resultado = resultado_mapa.get(
            self.filtro_resultado_relatorio.get()
        )

        registros = (
            self.checkpoint_service
            .listar_relatorios_obitos(
                agravo=agravo,
                resultado_comparacao=resultado,
                limite=100
            )
        )

        for filho in (
            self.container_relatorios.winfo_children()
        ):
            filho.destroy()

        self.labels_relatorios_wrap = []

        if not registros:
            self.label_quantidade_relatorios.configure(
                text="0 registros"
            )
            self._criar_estado_vazio_relatorios()
            return

        # Sem filtro de agravo, as conferências do mesmo dia
        # são apresentadas dentro de uma única borda.
        if agravo is None:
            registros_por_dia = {}

            for registro in registros:
                data_referencia = registro[
                    "data_referencia"
                ]
                registros_por_dia.setdefault(
                    data_referencia,
                    []
                ).append(registro)

            quantidade_dias = len(
                registros_por_dia
            )
            quantidade_conferencias = len(
                registros
            )

            texto_dias = (
                f"{quantidade_dias} dia"
                if quantidade_dias == 1
                else f"{quantidade_dias} dias"
            )
            texto_conferencias = (
                f"{quantidade_conferencias} conferência"
                if quantidade_conferencias == 1
                else (
                    f"{quantidade_conferencias} "
                    "conferências"
                )
            )

            self.label_quantidade_relatorios.configure(
                text=(
                    f"{texto_dias} • "
                    f"{texto_conferencias}"
                )
            )

            for linha, (
                data_referencia,
                registros_dia
            ) in enumerate(
                registros_por_dia.items()
            ):
                self._criar_card_relatorio_dia(
                    data_referencia=data_referencia,
                    registros=registros_dia,
                    linha=linha
                )

        # Ao selecionar Dengue ou Chikungunya, cada registro
        # volta a ser exibido individualmente.
        else:
            quantidade = len(registros)

            self.label_quantidade_relatorios.configure(
                text=(
                    f"{quantidade} registro"
                    if quantidade == 1
                    else f"{quantidade} registros"
                )
            )

            for linha, registro in enumerate(
                registros
            ):
                self._criar_card_relatorio(
                    registro=registro,
                    linha=linha
                )

        self.after(
            20,
            self._ajustar_wrap_relatorios
        )

    def _criar_estado_vazio_relatorios(self):
        painel = ctk.CTkFrame(
            self.container_relatorios,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=0,
            column=0,
            sticky="ew"
        )
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="○ Nenhum relatório encontrado",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 5)
        )

        ctk.CTkLabel(
            painel,
            text=(
                "Os relatórios aparecerão aqui após a "
                "confirmação de Dengue ou Chikungunya."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=620
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )

    def _criar_card_relatorio_dia(
        self,
        data_referencia: str,
        registros: list[dict],
        linha: int
    ):
        """
        Cria uma única borda por dia.

        Dengue e Chikungunya ficam lado a lado dentro do mesmo
        registro diário. Se o filtro de resultado retornar apenas
        um agravo para a data, o bloco ocupa toda a largura.
        """

        card = ctk.CTkFrame(
            self.container_relatorios,
            fg_color=Colors.SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )
        card.grid_columnconfigure(0, weight=1)

        data_formatada = (
            self._formatar_data_relatorio(
                data_referencia
            )
        )

        cabecalho = ctk.CTkFrame(
            card,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(12, 0)
        )
        cabecalho.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            cabecalho,
            text=data_formatada,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(12, 8),
            pady=11
        )

        quantidade = len(registros)

        ctk.CTkLabel(
            cabecalho,
            text=(
                f"{quantidade} agravo"
                if quantidade == 1
                else f"{quantidade} agravos"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        ).grid(
            row=0,
            column=1,
            sticky="e",
            padx=(8, 12),
            pady=11
        )

        conteudo = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        conteudo.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=12
        )

        if quantidade == 1:
            conteudo.grid_columnconfigure(
                0,
                weight=1
            )
        else:
            conteudo.grid_columnconfigure(
                (0, 1),
                weight=1,
                uniform=f"relatorio_dia_{linha}"
            )

        # Mantém uma ordem previsível: Dengue antes de
        # Chikungunya, independentemente da consulta ao banco.
        ordem_agravos = {
            CheckpointService.AGRAVO_DENGUE: 0,
            CheckpointService.AGRAVO_CHIKUNGUNYA: 1
        }
        registros_ordenados = sorted(
            registros,
            key=lambda item: ordem_agravos.get(
                item.get("agravo"),
                99
            )
        )

        for coluna, registro in enumerate(
            registros_ordenados
        ):
            self._criar_bloco_agravo_relatorio(
                master=conteudo,
                registro=registro,
                coluna=coluna,
                total=quantidade
            )

    def _criar_bloco_agravo_relatorio(
        self,
        master,
        registro: dict,
        coluna: int,
        total: int
    ):
        agravo = (
            "Dengue"
            if registro["agravo"]
            == CheckpointService.AGRAVO_DENGUE
            else "Chikungunya"
        )

        bloco = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        bloco.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=(
                0
                if total == 1
                else (
                    (0, 5)
                    if coluna == 0
                    else (5, 0)
                )
            )
        )
        bloco.grid_columnconfigure(
            0,
            weight=1
        )

        topo = ctk.CTkFrame(
            bloco,
            fg_color="transparent"
        )
        topo.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(13, 0)
        )
        topo.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            topo,
            text=agravo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        resultado = registro.get(
            "resultado_comparacao"
        )

        if resultado == "mudou":
            texto_resultado = "◉ Houve alteração"
            cor_resultado = Colors.PRIMARY
        elif resultado == "manteve_igual":
            texto_resultado = "✔️ Manteve igual"
            cor_resultado = Colors.SUCCESS
        else:
            texto_resultado = (
                "○ Resultado não informado"
            )
            cor_resultado = Colors.TEXT_MUTED

        ctk.CTkLabel(
            bloco,
            text=texto_resultado,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=cor_resultado,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(8, 4)
        )

        horario = (
            self._formatar_horario_relatorio(
                registro.get("confirmado_em")
            )
        )
        responsavel = (
            registro.get("responsavel")
            or "Não informado"
        )

        label_metadados = ctk.CTkLabel(
            bloco,
            text=(
                f"Conferido {horario}\n"
                f"Responsável: {responsavel}"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=300
        )
        label_metadados.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14
        )

        observacao = (
            registro.get("observacao")
            or "Sem observação registrada."
        )

        label_observacao = ctk.CTkLabel(
            bloco,
            text=f"Observação: {observacao}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=300
        )
        label_observacao.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=14,
            pady=(9, 14)
        )

        self.labels_relatorios_wrap.extend([
            label_metadados,
            label_observacao
        ])

    def _criar_card_relatorio(
        self,
        registro: dict,
        linha: int
    ):
        card = ctk.CTkFrame(
            self.container_relatorios,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )
        card.grid_columnconfigure(0, weight=1)

        agravo = (
            "Dengue"
            if registro["agravo"]
            == CheckpointService.AGRAVO_DENGUE
            else "Chikungunya"
        )
        data_formatada = self._formatar_data_relatorio(
            registro["data_referencia"]
        )

        cabecalho = ctk.CTkFrame(
            card,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=6
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(12, 0)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text=f"{data_formatada} — {agravo}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=11
        )

        resultado = registro.get("resultado_comparacao")

        if resultado == "mudou":
            texto_resultado = "◉ Houve alteração"
            cor_resultado = Colors.PRIMARY
        elif resultado == "manteve_igual":
            texto_resultado = "✔️ Manteve igual"
            cor_resultado = Colors.SUCCESS
        else:
            texto_resultado = "○ Resultado não informado"
            cor_resultado = Colors.TEXT_MUTED

        ctk.CTkLabel(
            card,
            text=texto_resultado,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=cor_resultado,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(16, 4)
        )

        horario = self._formatar_horario_relatorio(
            registro.get("confirmado_em")
        )
        responsavel = (
            registro.get("responsavel")
            or "Não informado"
        )

        label_metadados = ctk.CTkLabel(
            card,
            text=(
                f"Conferido {horario} • "
                f"Responsável: {responsavel}"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=650
        )
        label_metadados.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20
        )

        observacao = (
            registro.get("observacao")
            or "Sem observação registrada."
        )

        label_observacao = ctk.CTkLabel(
            card,
            text=f"Observação: {observacao}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=650
        )
        label_observacao.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(10, 18)
        )

        self.labels_relatorios_wrap.extend([
            label_metadados,
            label_observacao
        ])

    def _formatar_data_relatorio(self, data_iso: str) -> str:
        try:
            return datetime.fromisoformat(
                data_iso
            ).strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            return str(data_iso)

    def _formatar_horario_relatorio(
        self,
        horario_iso: str | None
    ) -> str:
        if not horario_iso:
            return "sem horário registrado"

        try:
            return (
                "às "
                + datetime.fromisoformat(
                    horario_iso
                ).strftime("%H:%M")
            )
        except (TypeError, ValueError):
            return str(horario_iso)

    def _ajustar_wrap_relatorios(self):
        if not hasattr(self, "container_relatorios"):
            return

        largura = self.container_relatorios.winfo_width()

        if largura <= 1:
            return

        wraplength = max(largura - 60, 220)

        for label in self.labels_relatorios_wrap:
            try:
                label.configure(wraplength=wraplength)
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Aba Bases
    # ------------------------------------------------------------------

    def criar_aba_bases(self):
        self.criar_painel_status()
        self.criar_titulo_destinos_bases()
        self.criar_cards_destinos_bases()
        self.criar_painel_progresso()
        self.criar_painel_operacoes()

    def criar_painel_status(self):
        """
        Cria um resumo visual equivalente ao painel principal da
        subaba Consulta.
        """

        painel = self._criar_painel(
            self.tab_bases,
            linha=0,
            pady=(30, 18)
        )
        painel.grid_columnconfigure(0, weight=1)

        cabecalho = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=12,
            pady=(12, 0)
        )
        cabecalho.grid_columnconfigure(1, weight=1)

        indicador = ctk.CTkFrame(
            cabecalho,
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
            text="📂",
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=18
            ),
            text_color=Colors.PRIMARY
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            cabecalho,
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
            cabecalho,
            text="Atualização das bases",
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

        self.label_status_base = ctk.CTkLabel(
            painel,
            text="Verificando a situação da rotina de hoje.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_status_base.grid(
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
            text="Progresso da atualização",
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

        self.label_progresso_bases = ctk.CTkLabel(
            cabecalho_progresso,
            text=(
                f"0 de {len(self.ETAPAS_FLUXO_BASES)} "
                "etapas concluídas"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        )
        self.label_progresso_bases.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.barra_resumo_bases = ctk.CTkProgressBar(
            painel,
            height=8,
            corner_radius=4,
            fg_color=Colors.BACKGROUND,
            progress_color=Colors.PRIMARY
        )
        self.barra_resumo_bases.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(8, 16)
        )
        self.barra_resumo_bases.set(0)

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
            uniform="resumo_bases"
        )

        bloco_solicitacoes = ctk.CTkFrame(
            indicadores,
            fg_color=Colors.BACKGROUND,
            corner_radius=6
        )
        bloco_solicitacoes.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6)
        )

        ctk.CTkLabel(
            bloco_solicitacoes,
            text="SOLICITAÇÕES DO DIA",
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

        self.label_solicitacoes_bases = ctk.CTkLabel(
            bloco_solicitacoes,
            text="○ Solicitações pendentes",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_solicitacoes_bases.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        bloco_arquivos = ctk.CTkFrame(
            indicadores,
            fg_color=Colors.BACKGROUND,
            corner_radius=6
        )
        bloco_arquivos.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0)
        )

        ctk.CTkLabel(
            bloco_arquivos,
            text="ARQUIVOS DO DIA",
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

        self.label_arquivos_bases = ctk.CTkLabel(
            bloco_arquivos,
            text="○ Arquivos pendentes",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_arquivos_bases.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_botoes_bases = botoes
        botoes.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(16, 8)
        )

        self.botao_baixar = ctk.CTkButton(
            botoes,
            text="▶ Iniciar rotina",
            command=self.iniciar_download,
            width=180,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )

        self.botao_cancelar_bases = self._criar_botao(
            botoes,
            "■ Cancelar",
            self.cancelar_atualizacao_bases,
            145,
            transparente=True,
            estado="disabled"
        )

        self.botao_atualizar_estado_bases = self._criar_botao(
            botoes,
            "↻ Atualizar estado",
            self.atualizar_estado_bases,
            165,
            transparente=True
        )

        self.botao_resetar_bases = self._criar_botao(
            botoes,
            "↺ Resetar teste",
            self.resetar_atualizacao_bases_teste,
            155,
            transparente=True
        )

        self.botoes_bases = [
            self.botao_baixar,
            self.botao_cancelar_bases,
            self.botao_atualizar_estado_bases,
            self.botao_resetar_bases
        ]

        self.painel_alerta_processamento = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.painel_alerta_processamento.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=22,
            pady=(4, 12)
        )
        self.painel_alerta_processamento.grid_columnconfigure(
            1,
            weight=1
        )

        self.label_icone_alerta_bases = ctk.CTkLabel(
            self.painel_alerta_processamento,
            text="i",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        )
        self.label_icone_alerta_bases.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(12, 8),
            pady=12
        )

        self.label_titulo_alerta_bases = ctk.CTkLabel(
            self.painel_alerta_processamento,
            text="Acompanhamento do SINAN",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.label_titulo_alerta_bases.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 10),
            pady=(11, 2)
        )

        self.label_texto_alerta_bases = ctk.CTkLabel(
            self.painel_alerta_processamento,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_texto_alerta_bases.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 10),
            pady=(0, 11)
        )

        self.botao_correcao_manual_bases = ctk.CTkButton(
            self.painel_alerta_processamento,
            text="Confirmar correção manual",
            command=self.selecionar_correcao_manual_bases,
            width=185,
            height=34,
            corner_radius=6,
            state="disabled",
            fg_color="transparent",
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            )
        )
        self.botao_correcao_manual_bases.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(8, 12),
            pady=12
        )

        self.painel_alerta_processamento.grid_remove()

        self.label_checkpoint_bases = ctk.CTkLabel(
            painel,
            text="○ Atualização das bases pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_checkpoint_bases.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 18)
        )

        botoes.bind(
            "<Configure>",
            self.ajustar_layout_botoes_bases
        )

    def criar_titulo_destinos_bases(self):
        cabecalho = ctk.CTkFrame(
            self.tab_bases,
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
            text="Destinos da atualização",
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

        self.label_descricao_destinos_bases = ctk.CTkLabel(
            cabecalho,
            text=(
                "A mesma dupla validada é distribuída para "
                "o histórico, as pastas de teste e os bancos atuais."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left"
        )
        self.label_descricao_destinos_bases.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(3, 0)
        )

    def criar_cards_destinos_bases(self):
        container = ctk.CTkFrame(
            self.tab_bases,
            fg_color="transparent"
        )
        self.container_destinos_bases = container
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=6
        )

        self.card_destino_historico = (
            self._criar_card_destino_bases(
                master=container,
                coluna=0,
                icone="🗂️",
                titulo="Histórico",
                descricao=(
                    "ZIPs separados por ano, agravo e mês em "
                    "Documents\\SINAN\\Historico."
                ),
                atalhos=(
                    (
                        "📂 Dengue",
                        "historico_dengue"
                    ),
                    (
                        "📂 Chikungunya",
                        "historico_chikungunya"
                    )
                )
            )
        )

        self.card_destino_testes = (
            self._criar_card_destino_bases(
                master=container,
                coluna=1,
                icone="🧪",
                titulo="Pastas de teste",
                descricao=(
                    "DBFs instalados em Teste AB1 e Teste AB2 "
                    "com backup e validação SHA-256."
                ),
                atalhos=(
                    (
                        "📂 Teste AB1",
                        "teste_ab1"
                    ),
                    (
                        "📂 Teste AB2",
                        "teste_ab2"
                    )
                )
            )
        )

        self.card_destino_atuais = (
            self._criar_card_destino_bases(
                master=container,
                coluna=2,
                icone="🗃️",
                titulo="Bancos atuais",
                descricao=(
                    "dengue_AAAA.dbf e chiku_AAAA.dbf em "
                    "Documents\\SINAN\\Bancos_Atuais."
                ),
                atalhos=(
                    (
                        "📂 Abrir Bancos_Atuais",
                        "bancos_atuais"
                    ),
                )
            )
        )

        self.cards_destinos_bases = [
            self.card_destino_historico,
            self.card_destino_testes,
            self.card_destino_atuais
        ]

        container.bind(
            "<Configure>",
            self.ajustar_layout_destinos_bases
        )

    def _criar_card_destino_bases(
        self,
        master,
        coluna: int,
        icone: str,
        titulo: str,
        descricao: str,
        atalhos: tuple[tuple[str, str], ...]
    ) -> dict:
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.SURFACE,
            corner_radius=8,
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
        card.grid_columnconfigure(1, weight=1)

        icone_frame = ctk.CTkFrame(
            card,
            width=44,
            height=44,
            fg_color=Colors.BUTTON,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        icone_frame.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(16, 12),
            pady=(16, 10)
        )
        icone_frame.grid_propagate(False)

        ctk.CTkLabel(
            icone_frame,
            text=icone,
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=21
            ),
            text_color=Colors.TEXT_PRIMARY
        ).place(
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
            padx=(0, 16),
            pady=(16, 1)
        )

        label_status = ctk.CTkLabel(
            card,
            text="○ Aguardando rotina",
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
            sticky="nw",
            padx=(0, 16),
            pady=(1, 10)
        )

        label_descricao = ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=245
        )
        label_descricao.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(2, 12)
        )

        separador = ctk.CTkFrame(
            card,
            height=1,
            fg_color=Colors.DIVIDER
        )
        separador.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(0, 11)
        )

        ctk.CTkLabel(
            card,
            text="ATALHOS",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(0, 7)
        )

        container_atalhos = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        container_atalhos.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(0, 16)
        )

        for indice in range(len(atalhos)):
            container_atalhos.grid_columnconfigure(
                indice,
                weight=1,
                uniform=f"atalhos_{coluna}"
            )

        botoes_atalhos = []

        for indice, (
            texto,
            chave_pasta
        ) in enumerate(atalhos):
            botao = ctk.CTkButton(
                container_atalhos,
                text=texto,
                command=(
                    lambda chave=chave_pasta:
                        self.abrir_pasta_destino_bases(
                            chave
                        )
                ),
                height=34,
                corner_radius=7,
                fg_color="transparent",
                hover_color=Colors.SURFACE_HOVER,
                border_width=1,
                border_color=Colors.BORDER,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11,
                    weight="bold"
                )
            )
            botao.grid(
                row=0,
                column=indice,
                sticky="ew",
                padx=(
                    (0, 5)
                    if indice == 0
                    and len(atalhos) > 1
                    else (
                        (5, 0)
                        if indice == len(atalhos) - 1
                        and len(atalhos) > 1
                        else 0
                    )
                )
            )
            botoes_atalhos.append(botao)

        return {
            "frame": card,
            "status": label_status,
            "descricao": label_descricao,
            "atalhos": botoes_atalhos
        }

    def _obter_pastas_destino_bases(
        self
    ) -> dict[str, Path]:
        """
        Resolve os atalhos usando o mesmo serviço responsável por
        salvar os arquivos.

        Dessa forma, quando os caminhos forem alterados no futuro,
        os botões acompanharão automaticamente a configuração.
        """

        arquivos_service = (
            self.atualizacao_bases_service
            .rotina_service
            .arquivos_service
        )
        hoje = date.today()

        historico_dengue = (
            arquivos_service.caminho_historico(
                agravo=(
                    arquivos_service.AGRAVO_DENGUE
                ),
                data_referencia=hoje
            ).parent
        )
        historico_chikungunya = (
            arquivos_service.caminho_historico(
                agravo=(
                    arquivos_service
                    .AGRAVO_CHIKUNGUNYA
                ),
                data_referencia=hoje
            ).parent
        )

        caminhos_testes = (
            arquivos_service.caminhos_pastas_teste(
                data_referencia=hoje
            )
        )
        caminhos_atuais = (
            arquivos_service.caminhos_bancos_atuais(
                data_referencia=hoje
            )
        )

        return {
            "historico_dengue":
                historico_dengue,
            "historico_chikungunya":
                historico_chikungunya,
            "teste_ab1":
                caminhos_testes[
                    arquivos_service.AGRAVO_DENGUE
                ].parent,
            "teste_ab2":
                caminhos_testes[
                    arquivos_service
                    .AGRAVO_CHIKUNGUNYA
                ].parent,
            "bancos_atuais":
                caminhos_atuais[
                    arquivos_service.AGRAVO_DENGUE
                ].parent
        }

    def abrir_pasta_destino_bases(
        self,
        chave_pasta: str
    ):
        """
        Abre a pasta solicitada no Explorador de Arquivos.

        Nenhum arquivo é alterado por esta ação.
        """

        try:
            pastas = self._obter_pastas_destino_bases()
            pasta = pastas.get(chave_pasta)

            if pasta is None:
                raise KeyError(
                    "Atalho de pasta desconhecido."
                )

            pasta = Path(pasta)

            if not pasta.exists():
                mostrar_dialogo_arbohub(
                    master=self.winfo_toplevel(),
                    titulo="Pasta ainda não disponível",
                    mensagem=(
                        "A pasta deste atalho ainda não existe:\n\n"
                        f"{pasta}\n\n"
                        "Ela será criada automaticamente quando "
                        "a rotina correspondente for concluída."
                    ),
                    tipo="aviso",
                    texto_botao="Entendi"
                )
                return

            if not pasta.is_dir():
                raise NotADirectoryError(
                    f"O caminho não é uma pasta: {pasta}"
                )

            if os.name == "nt":
                os.startfile(
                    str(pasta)
                )
            elif sys.platform == "darwin":
                subprocess.Popen(
                    ["open", str(pasta)]
                )
            else:
                subprocess.Popen(
                    ["xdg-open", str(pasta)]
                )

            self.registrar_operacao(
                f"Pasta aberta: {pasta}"
            )

        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível abrir a pasta",
                mensagem=(
                    "O ArboHub não conseguiu abrir o destino.\n\n"
                    f"{erro}"
                ),
                tipo="erro",
                texto_botao="Fechar"
            )

    def ajustar_layout_destinos_bases(
        self,
        event=None
    ):
        if not hasattr(
            self,
            "container_destinos_bases"
        ):
            return

        largura = (
            event.width
            if event is not None
            else self.container_destinos_bases.winfo_width()
        )

        if largura <= 1:
            return

        vertical = largura < 920

        if (
            self.layout_destinos_bases_vertical == vertical
            and event is not None
        ):
            return

        if vertical:
            for indice, card in enumerate(
                self.cards_destinos_bases
            ):
                card["frame"].grid_configure(
                    row=indice,
                    column=0,
                    sticky="ew",
                    padx=0,
                    pady=(
                        (0, 10)
                        if indice < 2
                        else 0
                    )
                )

            self.container_destinos_bases.grid_columnconfigure(
                0,
                weight=1
            )
            self.container_destinos_bases.grid_columnconfigure(
                (1, 2),
                weight=0
            )
        else:
            self.container_destinos_bases.grid_columnconfigure(
                (0, 1, 2),
                weight=1,
                uniform="destinos_bases"
            )

            for indice, card in enumerate(
                self.cards_destinos_bases
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

        self.layout_destinos_bases_vertical = vertical

        self.after(
            20,
            self._ajustar_wrap_cards_destinos_bases
        )

    def _ajustar_wrap_cards_destinos_bases(self):
        if self._pagina_destruida:
            return

        if not hasattr(
            self,
            "cards_destinos_bases"
        ):
            return

        for card in self.cards_destinos_bases:
            largura = card["frame"].winfo_width()

            if largura <= 1:
                continue

            card["descricao"].configure(
                wraplength=max(
                    largura - 36,
                    180
                )
            )

    def _aplicar_estado_card_destino_bases(
        self,
        card: dict,
        estado: str,
        mensagem: str | None = None
    ):
        apresentacao = {
            "aguardando": (
                "○ Aguardando rotina",
                Colors.TEXT_MUTED
            ),
            "executando": (
                "● Atualizando",
                Colors.PRIMARY
            ),
            "concluido": (
                "✔️ Atualizado",
                Colors.SUCCESS
            ),
            "erro": (
                "× Falha na atualização",
                "#E06C75"
            ),
            "cancelado": (
                "○ Atualização cancelada",
                Colors.TEXT_MUTED
            )
        }

        texto, cor = apresentacao.get(
            estado,
            apresentacao["aguardando"]
        )

        if mensagem and estado in {
            "erro",
            "cancelado"
        }:
            texto = mensagem

        card["status"].configure(
            text=texto,
            text_color=cor
        )

    def _atualizar_resumo_bases_visual(
        self,
        estados: dict[str, str]
    ):
        total = len(self.ETAPAS_FLUXO_BASES)
        concluidas = sum(
            1
            for estado in estados.values()
            if estado == "concluido"
        )

        self.barra_resumo_bases.set(
            concluidas / total
        )
        self.barra_resumo_bases.configure(
            progress_color=(
                Colors.SUCCESS
                if concluidas == total
                else Colors.PRIMARY
            )
        )
        self.label_progresso_bases.configure(
            text=(
                f"{concluidas} de {total} "
                "etapas concluídas"
            )
        )

        estado_solicitacoes = estados.get(
            AtualizacaoBasesService.ETAPA_SOLICITACOES,
            "aguardando"
        )

        if estado_solicitacoes == "concluido":
            self.label_solicitacoes_bases.configure(
                text="✔️ Solicitações do dia prontas",
                text_color=Colors.SUCCESS
            )
        elif estado_solicitacoes == "executando":
            self.label_solicitacoes_bases.configure(
                text="● Preparando solicitações",
                text_color=Colors.PRIMARY
            )
        elif estado_solicitacoes == "erro":
            self.label_solicitacoes_bases.configure(
                text="× Falha nas solicitações",
                text_color="#E06C75"
            )
        else:
            self.label_solicitacoes_bases.configure(
                text="○ Solicitações pendentes",
                text_color=Colors.TEXT_MUTED
            )

        etapas_arquivos = (
            AtualizacaoBasesService.ETAPA_DOWNLOAD,
            AtualizacaoBasesService.ETAPA_HISTORICO,
            AtualizacaoBasesService.ETAPA_EXTRACAO,
            AtualizacaoBasesService.ETAPA_PASTAS_TESTE,
            AtualizacaoBasesService.ETAPA_BANCOS_ATUAIS
        )
        estados_arquivos = [
            estados.get(
                etapa,
                "aguardando"
            )
            for etapa in etapas_arquivos
        ]

        if all(
            estado == "concluido"
            for estado in estados_arquivos
        ):
            self.label_arquivos_bases.configure(
                text="✔️ Arquivos atualizados",
                text_color=Colors.SUCCESS
            )
        elif any(
            estado == "erro"
            for estado in estados_arquivos
        ):
            self.label_arquivos_bases.configure(
                text="× Atualização incompleta",
                text_color="#E06C75"
            )
        elif any(
            estado == "executando"
            for estado in estados_arquivos
        ):
            self.label_arquivos_bases.configure(
                text="● Atualizando arquivos",
                text_color=Colors.PRIMARY
            )
        else:
            self.label_arquivos_bases.configure(
                text="○ Arquivos pendentes",
                text_color=Colors.TEXT_MUTED
            )

        self._aplicar_estado_card_destino_bases(
            self.card_destino_historico,
            estados.get(
                AtualizacaoBasesService.ETAPA_HISTORICO,
                "aguardando"
            ),
            self.mensagens_etapas_bases.get(
                AtualizacaoBasesService.ETAPA_HISTORICO
            )
        )
        self._aplicar_estado_card_destino_bases(
            self.card_destino_testes,
            estados.get(
                AtualizacaoBasesService.ETAPA_PASTAS_TESTE,
                "aguardando"
            ),
            self.mensagens_etapas_bases.get(
                AtualizacaoBasesService.ETAPA_PASTAS_TESTE
            )
        )
        self._aplicar_estado_card_destino_bases(
            self.card_destino_atuais,
            estados.get(
                AtualizacaoBasesService.ETAPA_BANCOS_ATUAIS,
                "aguardando"
            ),
            self.mensagens_etapas_bases.get(
                AtualizacaoBasesService.ETAPA_BANCOS_ATUAIS
            )
        )

    def criar_painel_progresso(self):
        painel = self._criar_painel(
            self.tab_bases,
            linha=3,
            pady=(18, 0)
        )
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Etapas da atualização",
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
            sticky="ew",
            padx=22,
            pady=(18, 4)
        )

        self.label_descricao_bases = ctk.CTkLabel(
            painel,
            text=(
                "A linha do tempo acompanha as etapas reais "
                "da rotina. Solicitações e arquivos existentes "
                "no dia são reutilizados para evitar duplicações."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_descricao_bases.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 16)
        )

        container = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_linha_tempo_bases = container
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 18)
        )
        container.grid_columnconfigure(
            1,
            weight=1
        )

        for indice, (
            identificador,
            titulo,
            detalhe
        ) in enumerate(self.ETAPAS_FLUXO_BASES):
            componentes = self._criar_item_linha_tempo(
                master=container,
                indice=indice,
                quantidade=len(
                    self.ETAPAS_FLUXO_BASES
                ),
                titulo=titulo,
                detalhe=detalhe
            )

            self.componentes_linha_tempo_bases[
                identificador
            ] = componentes

        self.atualizar_linha_tempo_bases()

    def atualizar_linha_tempo_bases(
        self,
        rotina: dict | None = None
    ):
        if not self.componentes_linha_tempo_bases:
            return

        rotina = (
            rotina
            or self.checkpoint_service.obter_rotina()
        )

        etapas = [
            item[0]
            for item in self.ETAPAS_FLUXO_BASES
        ]

        executando = (
            self.atualizacao_bases_service
            .esta_em_execucao()
        )

        if (
            rotina["atualizacao_bases"]
            and not executando
            and all(
                estado == "aguardando"
                for estado in (
                    self.estados_etapas_bases.values()
                )
            )
        ):
            estados = {
                etapa: "concluido"
                for etapa in etapas
            }
        else:
            estados = dict(
                self.estados_etapas_bases
            )

        for indice, etapa in enumerate(etapas):
            mensagem = (
                self.mensagens_etapas_bases.get(
                    etapa
                )
            )

            self._aplicar_estado_item_linha_tempo(
                componentes=(
                    self.componentes_linha_tempo_bases[
                        etapa
                    ]
                ),
                estado=estados.get(
                    etapa,
                    "aguardando"
                ),
                indice=indice,
                mensagem=mensagem
            )

        for etapa in etapas[:-1]:
            conector = (
                self.componentes_linha_tempo_bases[
                    etapa
                ]["conector"]
            )

            if conector is None:
                continue

            conector.configure(
                fg_color=(
                    Colors.SUCCESS
                    if estados.get(etapa) == "concluido"
                    else Colors.BORDER
                )
            )

        self._atualizar_resumo_bases_visual(
            estados
        )

    def criar_painel_operacoes(self):
        painel = self._criar_painel(
            self.tab_bases,
            linha=4,
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
        self.ajustar_layout_acoes_consulta()
        self.ajustar_layout_botoes_bases()
        self.ajustar_layout_destinos_bases()
        self.ajustar_layout_filtros_relatorios()
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

        usar_vertical = largura < 960

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

        # Após reposicionar os cards, lê a largura real de cada
        # um. Isso evita cortes causados por estimativas baseadas
        # somente na largura total do container.
        self.after(
            20,
            self._ajustar_wrap_cards_pela_largura_real
        )

    def _ajustar_wrap_cards_pela_largura_real(self):
        if self._pagina_destruida:
            return

        for card in (
            self.card_dengue,
            self.card_chikungunya
        ):
            largura_card = card["frame"].winfo_width()

            if largura_card <= 1:
                continue

            card["descricao"].configure(
                wraplength=max(
                    largura_card - 44,
                    180
                )
            )

    def ajustar_layout_acoes_consulta(
        self,
        event=None
    ):
        if not hasattr(
            self,
            "container_acoes_consulta"
        ):
            return

        largura = (
            event.width
            if event is not None
            else self.container_acoes_consulta.winfo_width()
        )

        if largura <= 1:
            return

        usar_vertical = largura < 520

        if (
            self.layout_acoes_consulta_vertical
            == usar_vertical
            and event is not None
        ):
            return

        if usar_vertical:
            self.container_acoes_consulta.grid_columnconfigure(
                0,
                weight=1
            )
            self.container_acoes_consulta.grid_columnconfigure(
                1,
                weight=0
            )

            self.botao_iniciar_verificacao.grid_configure(
                row=0,
                column=0,
                sticky="ew",
                padx=0,
                pady=(0, 5)
            )
            self.botao_resetar_consulta.grid_configure(
                row=1,
                column=0,
                sticky="ew",
                padx=0,
                pady=(5, 0)
            )
        else:
            self.container_acoes_consulta.grid_columnconfigure(
                0,
                weight=1
            )
            self.container_acoes_consulta.grid_columnconfigure(
                1,
                weight=0
            )

            self.botao_iniciar_verificacao.grid_configure(
                row=0,
                column=0,
                sticky="ew",
                padx=(0, 6),
                pady=0
            )
            self.botao_resetar_consulta.grid_configure(
                row=0,
                column=1,
                sticky="e",
                padx=(6, 0),
                pady=0
            )

        self.layout_acoes_consulta_vertical = usar_vertical

    def ajustar_layout_filtros_relatorios(self):
        if not hasattr(self, "painel_filtros_relatorios"):
            return

        largura = self.painel_filtros_relatorios.winfo_width()

        if largura <= 1:
            return

        vertical = largura < 680

        if vertical:
            self.painel_filtros_relatorios.grid_columnconfigure(
                0,
                weight=1
            )
            self.painel_filtros_relatorios.grid_columnconfigure(
                (1, 2),
                weight=0
            )

            self.menu_agravo_relatorio.grid_configure(
                row=1,
                column=0,
                sticky="ew",
                padx=20,
                pady=(0, 6)
            )
            self.menu_resultado_relatorio.grid_configure(
                row=2,
                column=0,
                sticky="ew",
                padx=20,
                pady=6
            )
            self.botao_atualizar_relatorios.grid_configure(
                row=3,
                column=0,
                sticky="ew",
                padx=20,
                pady=(6, 18)
            )
        else:
            self.painel_filtros_relatorios.grid_columnconfigure(
                (0, 1),
                weight=1
            )
            self.painel_filtros_relatorios.grid_columnconfigure(
                2,
                weight=0
            )

            self.menu_agravo_relatorio.grid_configure(
                row=1,
                column=0,
                sticky="ew",
                padx=(20, 6),
                pady=(0, 18)
            )
            self.menu_resultado_relatorio.grid_configure(
                row=1,
                column=1,
                sticky="ew",
                padx=6,
                pady=(0, 18)
            )
            self.botao_atualizar_relatorios.grid_configure(
                row=1,
                column=2,
                sticky="e",
                padx=(6, 20),
                pady=(0, 18)
            )

    def ajustar_layout_botoes_bases(self, event=None):
        if not hasattr(
            self,
            "container_botoes_bases"
        ):
            return

        largura = (
            event.width
            if event is not None
            else self.container_botoes_bases.winfo_width()
        )

        if largura <= 1:
            return

        if largura < 520:
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
                    0
                    if colunas == 1
                    else (
                        (0, 5)
                        if coluna == 0
                        else (
                            (5, 0)
                            if coluna == colunas - 1
                            else 5
                        )
                    )
                ),
                pady=(
                    (0, 5)
                    if linha == 0
                    and len(self.botoes_bases) > colunas
                    else (
                        (5, 0)
                        if linha > 0
                        else 0
                    )
                )
            )

        self.layout_botoes_bases = colunas

    def ajustar_quebra_textos(self):
        def aplicar_wrap(label, margem: int, minimo: int = 180):
            try:
                largura_parent = label.master.winfo_width()

                if largura_parent > 1:
                    label.configure(
                        wraplength=max(
                            largura_parent - margem,
                            minimo
                        )
                    )
            except Exception:
                pass

        labels_principais = [
            self.label_descricao_resumo,
            self.label_estado_automacao,
            self.label_descricao_linha_tempo
        ]

        for nome in (
            "label_status_base",
            "label_descricao_bases",
            "label_descricao_destinos_bases"
        ):
            if hasattr(self, nome):
                labels_principais.append(
                    getattr(self, nome)
                )

        for label in labels_principais:
            aplicar_wrap(label, 50)

        for colecao in (
            self.componentes_linha_tempo,
            self.componentes_linha_tempo_bases
        ):
            for componentes in colecao.values():
                aplicar_wrap(
                    componentes["detalhe"],
                    12,
                    160
                )

        if hasattr(
            self,
            "cards_destinos_bases"
        ):
            self._ajustar_wrap_cards_destinos_bases()

        if hasattr(self, "label_descricao_relatorios"):
            aplicar_wrap(
                self.label_descricao_relatorios,
                50
            )
            self._ajustar_wrap_relatorios()

    def iniciar_verificacao_obitos(self):
        if self.consulta_obitos_service.esta_em_execucao():
            return

        rotina = self.checkpoint_service.obter_rotina()

        if rotina["verificacao_obitos"]:
            messagebox.showinfo(
                title="Verificação já concluída",
                message=(
                    "A verificação de óbitos de hoje já foi "
                    "concluída. Use o botão Resetar para iniciar "
                    "uma nova execução."
                ),
                parent=self.winfo_toplevel()
            )
            return

        iniciou = self.consulta_obitos_service.iniciar()

        if not iniciou:
            return

        self.etapa_fluxo_atual = (
            ConsultaObitosService.ETAPA_ABRIR_SINAN
        )
        self.estado_fluxo_atual = "executando"
        self.mensagem_etapa_fluxo = (
            "Iniciando o navegador do SINAN."
        )

        self.label_estado_automacao.configure(
            text="Iniciando a automação do SINAN...",
            text_color=Colors.PRIMARY
        )

        self.atualizar_painel_rotina()

    def _agendar_processamento_eventos(self):
        if self._pagina_destruida:
            return

        self._polling_automacao_id = self.after(
            100,
            self._processar_eventos_automacao
        )

    def _processar_eventos_automacao(self):
        self._polling_automacao_id = None

        if self._pagina_destruida:
            return

        for evento in (
            self.consulta_obitos_service.obter_eventos()
        ):
            self._tratar_evento_automacao(
                evento
            )

        for evento in (
            self.atualizacao_bases_service.obter_eventos()
        ):
            self._tratar_evento_bases(
                evento
            )

        self._agendar_processamento_eventos()

    def _tratar_evento_automacao(
        self,
        evento: dict
    ):
        tipo = evento.get("tipo")

        if tipo == ConsultaObitosService.EVENTO_ETAPA:
            self.etapa_fluxo_atual = evento.get(
                "etapa"
            )
            self.estado_fluxo_atual = "executando"
            self.mensagem_etapa_fluxo = evento.get(
                "mensagem"
            )
            self.atualizar_linha_tempo_consulta()
            return

        if tipo == ConsultaObitosService.EVENTO_STATUS:
            mensagem = evento.get(
                "mensagem",
                "Automação em andamento..."
            )

            self.label_estado_automacao.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )

            self.mensagem_etapa_fluxo = mensagem
            self.atualizar_linha_tempo_consulta()
            return

        if tipo == ConsultaObitosService.EVENTO_ATUALIZAR:
            self.atualizar_painel_rotina()
            return

        if tipo == ConsultaObitosService.EVENTO_CONFIRMAR:
            self._abrir_confirmacao_automacao(
                agravo=evento["agravo"],
                acao_seguinte=evento["acao_seguinte"]
            )
            return

        if tipo == ConsultaObitosService.EVENTO_CONCLUIDO:
            self.etapa_fluxo_atual = (
                ConsultaObitosService.ETAPA_FINALIZACAO
            )
            self.estado_fluxo_atual = "concluido"
            self.mensagem_etapa_fluxo = evento.get(
                "mensagem",
                "Verificação concluída."
            )

            self.atualizar_painel_rotina()
            self.atualizar_linha_tempo_consulta()

            self.label_estado_automacao.configure(
                text=self.mensagem_etapa_fluxo,
                text_color=Colors.SUCCESS
            )
            self._atualizar_controles_automacao()
            return

        if tipo == ConsultaObitosService.EVENTO_CANCELADO:
            self.etapa_fluxo_atual = evento.get(
                "etapa",
                self.etapa_fluxo_atual
            )
            self.estado_fluxo_atual = "cancelado"
            self.mensagem_etapa_fluxo = evento.get(
                "mensagem",
                "Verificação cancelada."
            )

            self.atualizar_painel_rotina()
            self.atualizar_linha_tempo_consulta()

            self.label_estado_automacao.configure(
                text=self.mensagem_etapa_fluxo,
                text_color=Colors.TEXT_MUTED
            )
            self._atualizar_controles_automacao()
            return

        if tipo == ConsultaObitosService.EVENTO_ERRO:
            self.etapa_fluxo_atual = evento.get(
                "etapa",
                self.etapa_fluxo_atual
            )
            self.estado_fluxo_atual = "erro"
            self.mensagem_etapa_fluxo = evento.get(
                "mensagem",
                "A verificação não pôde ser concluída."
            )

            self.atualizar_painel_rotina()
            self.atualizar_linha_tempo_consulta()

            self.label_estado_automacao.configure(
                text="A verificação não pôde ser concluída.",
                text_color=Colors.TEXT_SECONDARY
            )
            self._atualizar_controles_automacao()

            messagebox.showerror(
                title="Erro na verificação do SINAN",
                message=self.mensagem_etapa_fluxo,
                parent=self.winfo_toplevel()
            )

    def _abrir_confirmacao_automacao(
        self,
        agravo: str,
        acao_seguinte: str
    ):
        self.label_estado_automacao.configure(
            text=(
                f"Confira os resultados de {agravo} no SINAN "
                "e responda à janela do ArboHub."
            ),
            text_color=Colors.PRIMARY
        )

        try:
            resultado = (
                solicitar_confirmacao_conferencia_nativa(
                    agravo=agravo,
                    acao_seguinte=acao_seguinte,
                    master=self.winfo_toplevel(),
                    manter_no_topo=True
                )
            )

            self.consulta_obitos_service.responder_confirmacao(
                resultado
            )

        except Exception as erro:
            try:
                self.consulta_obitos_service.cancelar()
            except Exception:
                pass

            if not self._pagina_destruida:
                messagebox.showerror(
                    title="Erro na confirmação",
                    message=str(erro),
                    parent=self.winfo_toplevel()
                )

    def _tratar_evento_bases(
        self,
        evento: dict
    ):
        tipo = evento.get("tipo")

        if (
            tipo
            == AtualizacaoBasesService.EVENTO_ALERTA_PROCESSAMENTO
        ):
            dados = evento.get("dados", {})
            self._mostrar_alerta_processamento_bases(
                dados=dados
            )
            self.registrar_operacao(
                evento.get(
                    "mensagem",
                    "Aviso de processamento do SINAN."
                )
            )
            try:
                self.winfo_toplevel().bell()
            except Exception:
                pass
            return

        if tipo == AtualizacaoBasesService.EVENTO_CORRECAO_MANUAL:
            mensagem = evento.get(
                "mensagem",
                "Validando a correção manual."
            )
            self.botao_correcao_manual_bases.configure(
                state="disabled"
            )
            self.label_status_base.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            self.registrar_operacao(
                mensagem
            )
            self._atualizar_controles_bases()
            return

        if tipo == AtualizacaoBasesService.EVENTO_PENDENTE:
            self._tratar_processamento_pendente_bases(
                evento
            )
            return

        if tipo == AtualizacaoBasesService.EVENTO_ETAPA:
            etapa = evento.get("etapa")
            estado_evento = evento.get(
                "estado",
                "em_andamento"
            )
            mensagem = evento.get(
                "mensagem",
                "Etapa em andamento."
            )
            dados = evento.get("dados", {})

            if dados.get("arquivo_processado"):
                agravo = dados.get("agravo")
                if agravo in self.estado_arquivos_bases:
                    self.estado_arquivos_bases[agravo] = True
                    self._atualizar_indicador_arquivos_bases()

            dengue = dados.get("dengue")
            chikungunya = dados.get("chikungunya")
            if isinstance(dengue, dict) and dengue.get("processado"):
                self.estado_arquivos_bases["dengue"] = True
            if (
                isinstance(chikungunya, dict)
                and chikungunya.get("processado")
            ):
                self.estado_arquivos_bases["chikungunya"] = True
            self._atualizar_indicador_arquivos_bases()

            conversao = {
                "iniciada": "executando",
                "em_andamento": "executando",
                "concluida": "concluido",
                "ignorada": "concluido"
            }

            estado_visual = conversao.get(
                estado_evento,
                "executando"
            )

            if etapa in self.estados_etapas_bases:
                self.etapa_bases_atual = etapa
                self.estado_bases_atual = estado_visual
                self.mensagem_bases_atual = mensagem
                self.estados_etapas_bases[
                    etapa
                ] = estado_visual
                self.mensagens_etapas_bases[
                    etapa
                ] = mensagem

                self.atualizar_linha_tempo_bases()

            self.label_status_base.configure(
                text=mensagem,
                text_color=(
                    Colors.SUCCESS
                    if estado_visual == "concluido"
                    else Colors.PRIMARY
                )
            )
            self.registrar_operacao(
                mensagem
            )
            return

        if tipo == AtualizacaoBasesService.EVENTO_STATUS:
            mensagem = evento.get(
                "mensagem",
                "Rotina de bases em andamento."
            )
            self.label_status_base.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            self.registrar_operacao(
                mensagem
            )
            return

        if tipo == AtualizacaoBasesService.EVENTO_ATUALIZAR:
            self.atualizar_painel_rotina()
            return

        if tipo == AtualizacaoBasesService.EVENTO_CONCLUIDO:
            mensagem = evento.get(
                "mensagem",
                "Atualização das bases concluída."
            )

            self.estado_arquivos_bases["dengue"] = True
            self.estado_arquivos_bases["chikungunya"] = True
            self._atualizar_indicador_arquivos_bases()
            self._ocultar_alerta_processamento_bases()

            self.etapa_bases_atual = (
                AtualizacaoBasesService.ETAPA_FINALIZACAO
            )
            self.estado_bases_atual = "concluido"
            self.mensagem_bases_atual = mensagem

            for etapa in self.estados_etapas_bases:
                self.estados_etapas_bases[
                    etapa
                ] = "concluido"

            self.mensagens_etapas_bases[
                AtualizacaoBasesService.ETAPA_FINALIZACAO
            ] = mensagem

            self.label_status_base.configure(
                text=mensagem,
                text_color=Colors.SUCCESS
            )

            self.atualizar_painel_rotina()
            self.atualizar_linha_tempo_bases()
            self._atualizar_controles_bases()

            self.registrar_operacao(
                mensagem
            )

            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Bases atualizadas",
                mensagem=(
                    "A rotina foi concluída com sucesso.\n\n"
                    "Os ZIPs foram validados no histórico, "
                    "as pastas de teste foram atualizadas e "
                    "Bancos_Atuais recebeu a nova dupla."
                ),
                tipo="sucesso",
                texto_botao="Concluir"
            )
            return

        if tipo == AtualizacaoBasesService.EVENTO_CANCELADO:
            mensagem = evento.get(
                "mensagem",
                "A atualização foi cancelada."
            )

            if (
                self.etapa_bases_atual
                in self.estados_etapas_bases
            ):
                self.estados_etapas_bases[
                    self.etapa_bases_atual
                ] = "cancelado"
                self.mensagens_etapas_bases[
                    self.etapa_bases_atual
                ] = mensagem

            self.estado_bases_atual = "cancelado"
            self.label_status_base.configure(
                text=mensagem,
                text_color=Colors.TEXT_MUTED
            )

            self.atualizar_linha_tempo_bases()
            self._atualizar_controles_bases()
            self.registrar_operacao(
                mensagem
            )
            return

        if tipo == AtualizacaoBasesService.EVENTO_ERRO:
            mensagem = evento.get(
                "mensagem",
                "Não foi possível atualizar as bases."
            )
            etapa = (
                evento.get("etapa")
                or self.etapa_bases_atual
            )
            correcao_manual = bool(
                evento.get(
                    "correcao_manual",
                    False
                )
            )

            if etapa in self.estados_etapas_bases:
                self.estados_etapas_bases[
                    etapa
                ] = "erro"
                self.mensagens_etapas_bases[
                    etapa
                ] = mensagem

            self.estado_bases_atual = (
                "pendente"
                if correcao_manual
                else "erro"
            )
            self.label_status_base.configure(
                text=mensagem,
                text_color=Colors.TEXT_SECONDARY
            )

            self.atualizar_linha_tempo_bases()
            self._atualizar_controles_bases()
            self.after(
                200,
                self._atualizar_controles_bases
            )
            self.registrar_operacao(
                f"Erro na atualização das bases: {mensagem}"
            )

            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo=(
                    "Correção manual não confirmada"
                    if correcao_manual
                    else "Erro na atualização das bases"
                ),
                mensagem=(
                    (
                        "O arquivo selecionado não foi aceito e "
                        "a pendência continua aberta.\n\n"
                        f"{mensagem}\n\n"
                        "Selecione o ZIP correto do agravo "
                        "pendente e tente novamente."
                    )
                    if correcao_manual
                    else (
                        "A rotina não foi concluída.\n\n"
                        f"{mensagem}\n\n"
                        "Os mecanismos de backup e restauração "
                        "permaneceram ativos."
                    )
                ),
                tipo="erro",
                texto_botao="Fechar"
            )

    def _mostrar_alerta_processamento_bases(
        self,
        dados: dict
    ):
        titulo = dados.get(
            "titulo",
            "Acompanhamento do SINAN"
        )
        texto = dados.get(
            "texto",
            "O ArboHub continua acompanhando o processamento."
        )
        marco = dados.get("marco_minutos")
        nivel = dados.get(
            "nivel",
            "informacao"
        )

        if marco:
            texto = (
                f"{texto}\n"
                f"Tempo de espera: {marco} minutos."
            )

        if nivel == "informacao":
            cor = Colors.PRIMARY
            icone = "i"
        else:
            cor = Colors.TEXT_SECONDARY
            icone = "!"

        self.painel_alerta_processamento.configure(
            border_color=cor
        )
        self.label_icone_alerta_bases.configure(
            text=icone,
            text_color=cor
        )
        self.label_titulo_alerta_bases.configure(
            text=titulo
        )
        self.label_texto_alerta_bases.configure(
            text=texto
        )
        self.painel_alerta_processamento.grid()

        # A correção manual só é liberada quando o limite de
        # o tempo máximo configurado for atingido e houver pendência.
        self.botao_correcao_manual_bases.configure(
            state="disabled",
            text="Confirmar correção manual"
        )

    def _ocultar_alerta_processamento_bases(self):
        if not hasattr(
            self,
            "painel_alerta_processamento"
        ):
            return

        self.painel_alerta_processamento.grid_remove()
        self._correcao_manual_bases_habilitada = False
        self._agravos_pendentes_bases = []
        self.botao_correcao_manual_bases.configure(
            state="disabled",
            text="Confirmar correção manual"
        )

    def selecionar_correcao_manual_bases(self):
        """
        Permite selecionar o ZIP obtido manualmente depois que o
        SINAN atingiu o limite de acompanhamento.

        O clique não conclui a rotina por si só. O arquivo é
        validado, identificado como DENGON ou CHIKON e instalado
        apenas no destino correspondente.
        """

        if not self._correcao_manual_bases_habilitada:
            return

        if (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            return

        texto_pendentes = (
            ", ".join(
                self._agravos_pendentes_bases
            )
            if self._agravos_pendentes_bases
            else "o agravo pendente"
        )

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Confirmar correção manual?",
            mensagem=(
                "Selecione o ZIP que foi obtido manualmente para "
                f"resolver a pendência de {texto_pendentes}.\n\n"
                "O ArboHub verificará a integridade do arquivo, "
                "confirmará se ele contém DENGON ou CHIKON e "
                "somente depois atualizará as pastas "
                "correspondentes.\n\n"
                "A rotina não será marcada como concluída se o "
                "arquivo não corresponder ao agravo pendente."
            ),
            texto_confirmar="Selecionar ZIP",
            texto_cancelar="Cancelar"
        )

        if not confirmou:
            return

        caminho_zip = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title=(
                "Selecione o ZIP do agravo pendente"
            ),
            filetypes=(
                ("Arquivos ZIP", "*.zip"),
                ("Todos os arquivos", "*.*")
            )
        )

        if not caminho_zip:
            return

        try:
            iniciou = (
                self.atualizacao_bases_service
                .iniciar_correcao_manual(
                    caminho_zip
                )
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo=(
                    "Não foi possível iniciar a correção"
                ),
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Fechar"
            )
            return

        if not iniciou:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Operação em andamento",
                mensagem=(
                    "Já existe uma operação de Bases em "
                    "andamento. Aguarde a conclusão antes de "
                    "selecionar outro arquivo."
                ),
                tipo="aviso",
                texto_botao="Entendi"
            )
            return

        self.botao_correcao_manual_bases.configure(
            state="disabled"
        )
        self.label_status_base.configure(
            text=(
                "Validando o ZIP selecionado para a correção "
                "manual."
            ),
            text_color=Colors.PRIMARY
        )
        self._atualizar_controles_bases()
        self.registrar_operacao(
            "Correção manual de Bases iniciada."
        )

    def _atualizar_indicador_arquivos_bases(self):
        if not hasattr(
            self,
            "label_arquivos_bases"
        ):
            return

        dengue = self.estado_arquivos_bases["dengue"]
        chikungunya = self.estado_arquivos_bases[
            "chikungunya"
        ]

        if dengue and chikungunya:
            texto = "✔️ Dengue e Chikungunya disponíveis"
            cor = Colors.SUCCESS
        elif dengue:
            texto = "✔️ Dengue • ◐ Chikungunya aguardando"
            cor = Colors.PRIMARY
        elif chikungunya:
            texto = "◐ Dengue aguardando • ✔️ Chikungunya"
            cor = Colors.PRIMARY
        else:
            texto = "○ Arquivos pendentes"
            cor = Colors.TEXT_MUTED

        self.label_arquivos_bases.configure(
            text=texto,
            text_color=cor
        )

    def _tratar_processamento_pendente_bases(
        self,
        evento: dict
    ):
        mensagem = evento.get(
            "mensagem",
            (
                "O tempo máximo de acompanhamento foi atingido."
            )
        )
        dados = evento.get("dados", {})
        tempo_limite_segundos = float(
            dados.get(
                "tempo_limite_segundos",
                1200
            )
        )

        if tempo_limite_segundos % 60 == 0:
            minutos_limite = int(
                tempo_limite_segundos // 60
            )
            unidade_limite = (
                "minuto"
                if minutos_limite == 1
                else "minutos"
            )
            texto_tempo_limite = (
                f"{minutos_limite} {unidade_limite}"
            )
        else:
            texto_tempo_limite = (
                f"{tempo_limite_segundos:g} segundos"
            )

        processados = list(
            dados.get("agravos_processados", ())
        )
        pendentes = list(
            dados.get("agravos_pendentes", ())
        )

        for rotulo in processados:
            chave = (
                "dengue"
                if str(rotulo).casefold() == "dengue"
                else "chikungunya"
            )
            self.estado_arquivos_bases[chave] = True

        self._agravos_pendentes_bases = [
            str(item)
            for item in pendentes
        ]
        self._correcao_manual_bases_habilitada = bool(
            pendentes
            and dados.get(
                "correcao_manual_disponivel",
                True
            )
        )

        self._atualizar_indicador_arquivos_bases()
        self.estado_bases_atual = "pendente"
        self.etapa_bases_atual = (
            AtualizacaoBasesService.ETAPA_PROCESSAMENTO
        )
        self.estados_etapas_bases[
            AtualizacaoBasesService.ETAPA_PROCESSAMENTO
        ] = "erro"
        self.mensagens_etapas_bases[
            AtualizacaoBasesService.ETAPA_PROCESSAMENTO
        ] = mensagem

        texto_processados = (
            ", ".join(processados)
            if processados
            else "Nenhum arquivo"
        )
        texto_pendentes = (
            ", ".join(pendentes)
            if pendentes
            else "Nenhum"
        )

        self.painel_alerta_processamento.grid()
        self.painel_alerta_processamento.configure(
            border_color=Colors.TEXT_SECONDARY
        )
        self.label_icone_alerta_bases.configure(
            text="!",
            text_color=Colors.TEXT_SECONDARY
        )
        self.label_titulo_alerta_bases.configure(
            text="Pendência na atualização das bases"
        )
        self.label_texto_alerta_bases.configure(
            text=(
                f"{mensagem}\n\n"
                f"Processado: {texto_processados}.\n"
                f"Ainda pendente: {texto_pendentes}."
            )
        )
        self.botao_correcao_manual_bases.configure(
            state=(
                "normal"
                if self._correcao_manual_bases_habilitada
                else "disabled"
            ),
            text="Confirmar correção manual"
        )

        self.label_status_base.configure(
            text=mensagem,
            text_color=Colors.TEXT_SECONDARY
        )
        self.atualizar_linha_tempo_bases()
        self._atualizar_controles_bases()
        self.after(
            200,
            self._atualizar_controles_bases
        )
        self.registrar_operacao(mensagem)

        try:
            self.winfo_toplevel().bell()
        except Exception:
            pass

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Exportação ainda indisponível",
            mensagem=(
                "O SINAN não disponibilizou todos os arquivos "
                f"dentro de {texto_tempo_limite}.\n\n"
                f"Arquivos concluídos: {texto_processados}.\n"
                f"Arquivos pendentes: {texto_pendentes}.\n\n"
                "Os arquivos que ficaram disponíveis já foram "
                "identificados, validados e colocados nas pastas "
                "correspondentes.\n\n"
                "Informe sua supervisora sobre a pendência. "
                "Quando o ZIP faltante for obtido manualmente, "
                "use “Confirmar correção manual” para que o "
                "ArboHub valide e finalize a rotina."
            ),
            tipo="aviso",
            texto_botao="Entendi"
        )

    def _atualizar_controles_bases(
        self,
        rotina: dict | None = None
    ):
        if not hasattr(
            self,
            "botao_baixar"
        ):
            return

        rotina = (
            rotina
            or self.checkpoint_service.obter_rotina()
        )

        executando = (
            self.atualizacao_bases_service
            .esta_em_execucao()
        )

        if executando:
            self.botao_baixar.configure(
                text="● Rotina em andamento",
                state="disabled"
            )
            self.botao_cancelar_bases.configure(
                state="normal"
            )
            self.botao_atualizar_estado_bases.configure(
                state="disabled"
            )
            self.botao_resetar_bases.configure(
                state="disabled"
            )
            self.botao_correcao_manual_bases.configure(
                state="disabled"
            )
            return

        self.botao_baixar.configure(
            text=(
                "↻ Executar novamente"
                if rotina["atualizacao_bases"]
                else "▶ Iniciar rotina"
            ),
            state="normal"
        )
        self.botao_cancelar_bases.configure(
            state="disabled"
        )
        self.botao_atualizar_estado_bases.configure(
            state="normal"
        )
        self.botao_resetar_bases.configure(
            state="normal"
        )
        self.botao_correcao_manual_bases.configure(
            state=(
                "normal"
                if self._correcao_manual_bases_habilitada
                else "disabled"
            )
        )

    def _atualizar_controles_automacao(
        self,
        rotina: dict | None = None
    ):
        if not hasattr(
            self,
            "botao_iniciar_verificacao"
        ):
            return

        rotina = (
            rotina
            or self.checkpoint_service.obter_rotina()
        )

        executando = (
            self.consulta_obitos_service.esta_em_execucao()
        )

        if executando:
            self.botao_iniciar_verificacao.configure(
                text="● Verificação em andamento",
                state="disabled"
            )
            self.botao_resetar_consulta.configure(
                state="disabled"
            )
            return

        if rotina["verificacao_obitos"]:
            self.botao_iniciar_verificacao.configure(
                text="✔️ Verificação concluída",
                state="disabled"
            )
            self.botao_resetar_consulta.configure(
                state="normal"
            )
            return

        self.botao_iniciar_verificacao.configure(
            text="▶ Iniciar verificação",
            state="normal"
        )
        self.botao_resetar_consulta.configure(
            state="normal"
        )

    def _ao_destruir_pagina(self, event):
        if event.widget is not self:
            return

        self._pagina_destruida = True

        if self._polling_automacao_id is not None:
            try:
                self.after_cancel(
                    self._polling_automacao_id
                )
            except Exception:
                pass

            self._polling_automacao_id = None

        if self.consulta_obitos_service.esta_em_execucao():
            self.consulta_obitos_service.cancelar()

        if (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            self.atualizacao_bases_service.cancelar()

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
        if self.consulta_obitos_service.esta_em_execucao():
            return

        self.checkpoint_service.resetar_verificacao_obitos()

        self.etapa_fluxo_atual = None
        self.estado_fluxo_atual = "aguardando"
        self.mensagem_etapa_fluxo = None

        self.atualizar_painel_rotina()
        self.registrar_operacao(
            "Checkpoints da consulta foram resetados."
        )

    # Compatibilidade com a versão antiga.

    def concluir_verificacao_obitos(self):
        self.checkpoint_service.marcar_verificacao_obitos()
        self.atualizar_painel_rotina()

    def resetar_atualizacao_bases_teste(self):
        """
        Reseta somente o checkpoint visual da atualização de Bases.

        Solicitações, números capturados, ZIPs históricos e DBFs
        permanecem intactos. Ao executar novamente, o ArboHub
        reutiliza os arquivos do dia e repete as validações e cópias.
        """

        if (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Resetar atualização de Bases?",
            mensagem=(
                "Este reset é destinado a testes.\n\n"
                "Ele apagará somente o checkpoint visual de Bases "
                "do dia atual e reiniciará a linha do tempo.\n\n"
                "Não serão apagados:\n"
                "• números de solicitação;\n"
                "• ZIPs do histórico;\n"
                "• DBFs das pastas de teste;\n"
                "• arquivos de Bancos_Atuais;\n"
                "• verificação de óbitos.\n\n"
                "Na próxima execução, o ArboHub reutilizará os "
                "arquivos já existentes e repetirá a validação e "
                "a distribuição dos DBFs."
            ),
            texto_confirmar="Resetar para teste",
            texto_cancelar="Cancelar",
            tipo="aviso"
        )

        if not confirmou:
            return

        self.checkpoint_service.resetar_atualizacao_bases()

        self.etapa_bases_atual = None
        self.estado_bases_atual = "aguardando"
        self.mensagem_bases_atual = None

        self.estados_etapas_bases = {
            etapa[0]: "aguardando"
            for etapa in self.ETAPAS_FLUXO_BASES
        }
        self.mensagens_etapas_bases = {}

        self.atualizar_painel_rotina()
        self.atualizar_linha_tempo_bases()
        self.atualizar_estado_bases()
        self._atualizar_controles_bases()

        self.registrar_operacao(
            "Checkpoint visual de Bases resetado para teste."
        )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Bases prontas para novo teste",
            mensagem=(
                "O checkpoint visual foi resetado.\n\n"
                "Clique em “Iniciar rotina” para repetir o "
                "procedimento usando as solicitações e os ZIPs "
                "já existentes para hoje."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def concluir_atualizacao_bases(self):
        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Checkpoint automático",
            mensagem=(
                "A atualização das bases é registrada "
                "automaticamente somente após a conclusão de "
                "todas as etapas reais da rotina."
            ),
            tipo="informacao"
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
                    "✔️ Verificação de óbitos concluída"
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
                    "✔️ Atualização das bases concluída"
                    f"{self.formatar_horario(
                        rotina['atualizacao_bases_em']
                    )}"
                ),
                text_color=Colors.SUCCESS
            )

            if not (
                self.atualizacao_bases_service
                .esta_em_execucao()
            ):
                self.label_status_base.configure(
                    text=(
                        "Bases atualizadas e validadas hoje."
                    ),
                    text_color=Colors.SUCCESS
                )
        else:
            self.label_checkpoint_bases.configure(
                text="○ Atualização das bases pendente",
                text_color=Colors.TEXT_MUTED
            )

        if rotina["rotina_concluida"]:
            self.label_rotina_completa.configure(
                text="✔️ Rotina diária completa: concluída",
                text_color=Colors.SUCCESS
            )
        else:
            self.label_rotina_completa.configure(
                text="○ Rotina diária completa: pendente",
                text_color=Colors.TEXT_MUTED
            )

        self._atualizar_controles_automacao(
            rotina
        )
        self._atualizar_controles_bases(
            rotina
        )
        self.atualizar_linha_tempo_consulta(
            rotina
        )
        self.atualizar_linha_tempo_bases(
            rotina
        )

        if hasattr(self, "container_relatorios"):
            self.atualizar_relatorios()

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
                "✔️ Conferido",
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

        texto_botao = {
            CheckpointService.STATUS_AGUARDANDO:
                "Aguardando automação",
            CheckpointService.STATUS_EXECUTANDO:
                "● Consulta em andamento",
            CheckpointService.STATUS_AGUARDANDO_CONFERENCIA:
                "◉ Aguardando conferência",
            CheckpointService.STATUS_CONCLUIDO:
                "✔️ Conferido",
            CheckpointService.STATUS_ERRO:
                "✕ Erro na consulta"
        }.get(
            status,
            "Aguardando automação"
        )

        componentes["botao"].configure(
            text=texto_botao,
            state="disabled"
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
        self.atualizar_estado_bases()

    def remover_pasta(self):
        self.atualizar_estado_bases()

    def iniciar_download(self):
        """
        Inicia a rotina real das bases em segundo plano.

        A confirmação muda conforme o estado do dia. Quando ainda
        não existem solicitações, a interface informa explicitamente
        que serão criadas solicitações reais no SINAN.
        """

        if (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            return

        try:
            estado = (
                self.atualizacao_bases_service
                .avaliar_estado_do_dia()
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível avaliar a rotina",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Fechar"
            )
            return

        autorizacao_solicitacoes = False

        if estado["requer_novas_solicitacoes"]:
            faltantes = ", ".join(
                estado["solicitacoes_faltantes"]
            )

            confirmou = solicitar_confirmacao_arbohub(
                master=self.winfo_toplevel(),
                titulo="Criar solicitações reais?",
                mensagem=(
                    "Ainda faltam solicitações reais para hoje:\n\n"
                    f"{faltantes}\n\n"
                    "O ArboHub abrirá o SINAN, aguardará seu login "
                    "manual e enviará somente as solicitações "
                    "faltantes. Cada número será salvo "
                    "imediatamente após aparecer na tela."
                ),
                texto_confirmar="Solicitar e continuar",
                texto_cancelar="Cancelar",
                tipo="aviso"
            )

            if not confirmou:
                return

            autorizacao_solicitacoes = True

        elif estado["requer_navegador"]:
            confirmou = solicitar_confirmacao_arbohub(
                master=self.winfo_toplevel(),
                titulo="Continuar atualização?",
                mensagem=(
                    "As solicitações de hoje já estão salvas, "
                    "mas os ZIPs ainda precisam ser acompanhados "
                    "ou baixados.\n\n"
                    "O SINAN será aberto e o login continuará "
                    "manual."
                ),
                texto_confirmar="Abrir o SINAN",
                texto_cancelar="Cancelar"
            )

            if not confirmou:
                return

        else:
            confirmou = solicitar_confirmacao_arbohub(
                master=self.winfo_toplevel(),
                titulo="Executar rotina novamente?",
                mensagem=(
                    "As solicitações e os ZIPs válidos de hoje "
                    "já existem.\n\n"
                    "Nenhuma nova solicitação será criada e o "
                    "SINAN não precisará ser aberto. O ArboHub "
                    "validará o histórico e atualizará novamente "
                    "as pastas de teste e Bancos_Atuais."
                ),
                texto_confirmar="Executar novamente",
                texto_cancelar="Cancelar"
            )

            if not confirmou:
                return

        self.etapa_bases_atual = None
        self.estado_bases_atual = "aguardando"
        self.mensagem_bases_atual = None
        self.estados_etapas_bases = {
            etapa[0]: "aguardando"
            for etapa in self.ETAPAS_FLUXO_BASES
        }
        self.mensagens_etapas_bases = {}
        self.estado_arquivos_bases = {
            "dengue": False,
            "chikungunya": False
        }
        self._ocultar_alerta_processamento_bases()
        self._atualizar_indicador_arquivos_bases()

        iniciou = (
            self.atualizacao_bases_service.iniciar(
                solicitacoes_autorizadas=(
                    autorizacao_solicitacoes
                )
            )
        )

        if not iniciou:
            return

        self.label_status_base.configure(
            text="Iniciando a rotina diária das bases.",
            text_color=Colors.PRIMARY
        )
        self.atualizar_linha_tempo_bases()
        self._atualizar_controles_bases()

        self.registrar_operacao(
            "Rotina diária das bases iniciada."
        )

    def cancelar_atualizacao_bases(self):
        if not (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Cancelar atualização?",
            mensagem=(
                "O cancelamento ocorrerá no próximo ponto seguro. "
                "Uma substituição atômica já iniciada não será "
                "interrompida pela metade."
            ),
            texto_confirmar="Solicitar cancelamento",
            texto_cancelar="Continuar rotina",
            tipo="aviso"
        )

        if not confirmou:
            return

        self.atualizacao_bases_service.cancelar()
        self.botao_cancelar_bases.configure(
            state="disabled"
        )
        self.label_status_base.configure(
            text=(
                "Cancelamento solicitado. "
                "Aguardando um ponto seguro."
            ),
            text_color=Colors.TEXT_MUTED
        )
        self.registrar_operacao(
            "Cancelamento da rotina de bases solicitado."
        )

    def atualizar_estado_bases(self):
        if not hasattr(
            self,
            "label_status_base"
        ):
            return

        if (
            self.atualizacao_bases_service
            .esta_em_execucao()
        ):
            return

        try:
            estado = (
                self.atualizacao_bases_service
                .avaliar_estado_do_dia()
            )
        except Exception as erro:
            self.label_status_base.configure(
                text=(
                    "Não foi possível verificar a situação: "
                    f"{erro}"
                ),
                text_color="#E06C75"
            )
            return

        lote_completo = estado["lote_completo"]
        lote_parcial = estado["lote_parcial"]

        if (
            lote_completo is not None
            and estado["historico_completo"]
        ):
            mensagem = (
                "Solicitações e ZIPs válidos de hoje já estão "
                "disponíveis. A rotina pode reutilizar o histórico "
                "e atualizar os destinos sem abrir o SINAN."
            )

        elif lote_completo is not None:
            mensagem = (
                "As solicitações de hoje já estão salvas. "
                "O SINAN será aberto para acompanhar o "
                "processamento e baixar os ZIPs."
            )

        elif lote_parcial is not None:
            faltantes = ", ".join(
                estado["solicitacoes_faltantes"]
            )
            mensagem = (
                "Um lote parcial foi encontrado. Ao iniciar, "
                "será criada somente a solicitação faltante: "
                f"{faltantes}."
            )

        else:
            mensagem = (
                "Ainda não existem solicitações para hoje. "
                "Ao iniciar, o ArboHub solicitará autorização "
                "antes de criar Dengue e Chikungunya no SINAN."
            )

        self.label_status_base.configure(
            text=mensagem,
            text_color=Colors.TEXT_SECONDARY
        )

        if lote_completo is not None:
            self.label_solicitacoes_bases.configure(
                text="✔️ Solicitações do dia prontas",
                text_color=Colors.SUCCESS
            )
        elif lote_parcial is not None:
            self.label_solicitacoes_bases.configure(
                text="● Lote parcial localizado",
                text_color=Colors.PRIMARY
            )
        else:
            self.label_solicitacoes_bases.configure(
                text="○ Solicitações pendentes",
                text_color=Colors.TEXT_MUTED
            )

        if estado["historico_completo"]:
            self.label_arquivos_bases.configure(
                text="✔️ ZIPs do dia disponíveis",
                text_color=Colors.SUCCESS
            )
            self._aplicar_estado_card_destino_bases(
                self.card_destino_historico,
                "concluido"
            )
        else:
            self.label_arquivos_bases.configure(
                text="○ Downloads pendentes",
                text_color=Colors.TEXT_MUTED
            )

            if (
                self.estados_etapas_bases.get(
                    AtualizacaoBasesService.ETAPA_HISTORICO
                )
                == "aguardando"
            ):
                self._aplicar_estado_card_destino_bases(
                    self.card_destino_historico,
                    "aguardando"
                )

        self._atualizar_controles_bases()

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