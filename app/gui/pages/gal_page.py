from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app.gui.components.arbohub_dialog import (
    mostrar_dialogo_arbohub,
    solicitar_confirmacao_arbohub
)
from app.gui.themes.colors import Colors
from app.services.atualizacao_gal_service import AtualizacaoGalService
from app.services.notificacoes_service import NotificacoesService


class GalPage(ctk.CTkFrame):
    """Tela da rotina semanal do GAL no padrão visual de Bases."""

    ETAPAS = (
        (
            AtualizacaoGalService.ETAPA_ACESSO,
            "Acesso ao GAL",
            "Login e CAPTCHA permanecem manuais."
        ),
        (
            AtualizacaoGalService.ETAPA_RELATORIO,
            "Relatório epidemiológico",
            "Configuração por data de liberação e exame."
        ),
        (
            AtualizacaoGalService.ETAPA_DOWNLOAD,
            "Download",
            "Recebimento e reconhecimento do arquivo gerado."
        ),
        (
            AtualizacaoGalService.ETAPA_HISTORICO,
            "Histórico semanal",
            "ZIP gal_aaaa-mm-dd contendo o CSV de mesmo nome."
        ),
        (
            AtualizacaoGalService.ETAPA_BANCO_ATUAL,
            "Banco atual",
            "Atualização de Documents\\GAL\\Banco_Atual."
        ),
        (
            AtualizacaoGalService.ETAPA_TESTE_SORO,
            "Banco TesteSORO",
            "Atualização do banco de teste na unidade F:."
        ),
        (
            AtualizacaoGalService.ETAPA_FINALIZACAO,
            "Finalização",
            "Validação dos destinos e registro no painel."
        )
    )

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.atualizacao_service = AtualizacaoGalService()
        self.notificacoes_service = NotificacoesService()
        self._pagina_destruida = False
        self._polling_id = None
        self._redimensionamento_id = None
        self._concluida_hoje = False
        self._layout_destinos_colunas = None
        self._layout_botoes_colunas = None
        self._estados_etapas: dict[str, str] = {}
        self._mensagens_etapas: dict[str, str] = {}
        self._componentes_etapas: dict[str, dict] = {}
        self._icone_gal: ctk.CTkImage | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_cabecalho()
        self._criar_conteudo()
        self._atualizar_estado_geral()
        self._atualizar_linha_tempo()
        self._atualizar_controles()

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

        self._agendar_eventos()
        self.after(80, self._ajustar_layout_responsivo)

    # ------------------------------------------------------------------
    # Construção da página
    # ------------------------------------------------------------------

    def _criar_cabecalho(self):
        self.cabecalho = ctk.CTkFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )
        self.cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(34, 18)
        )

        ctk.CTkLabel(
            self.cabecalho,
            text="GAL",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            self.cabecalho,
            text=(
                "Atualização semanal e gerenciamento do banco "
                "laboratorial de arbovírus."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x", pady=(5, 0))

    def _criar_conteudo(self):
        # Repete a mesma hierarquia usada pela subaba SINAN > Bases:
        # um frame-base ocupa a area disponivel e, dentro dele, o
        # CTkScrollableFrame controla sozinho largura e rolagem.
        self.conteudo_base = ctk.CTkFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )
        self.conteudo_base.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=34,
            pady=(0, 30)
        )
        self.conteudo_base.grid_columnconfigure(0, weight=1)
        self.conteudo_base.grid_rowconfigure(0, weight=1)

        self.conteudo = ctk.CTkScrollableFrame(
            self.conteudo_base,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            orientation="vertical",
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )
        self.conteudo.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        self.conteudo.grid_columnconfigure(0, weight=1)

        self._criar_painel_status()
        self._criar_titulo_destinos()
        self._criar_cards_destinos()
        self._criar_painel_progresso()

    def _novo_painel(
        self,
        linha: int,
        pady: tuple[int, int]
    ) -> ctk.CTkFrame:
        painel = ctk.CTkFrame(
            self.conteudo,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=8,
            pady=pady
        )
        painel.grid_columnconfigure(0, weight=1)
        return painel

    def _criar_painel_status(self):
        painel = self._novo_painel(0, (30, 18))

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

        self._icone_gal = self._carregar_icone_gal()
        self.label_icone_estado = ctk.CTkLabel(
            indicador,
            text="" if self._icone_gal else "GAL",
            image=self._icone_gal,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        )
        self.label_icone_estado.place(
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
            text="Atualização semanal do GAL",
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

        self.label_status_execucao = ctk.CTkLabel(
            painel,
            text="Verificando a situação da rotina semanal.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_status_execucao.grid(
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
        cabecalho_progresso.grid_columnconfigure(0, weight=1)

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
        ).grid(row=0, column=0, sticky="w")

        self.label_progresso = ctk.CTkLabel(
            cabecalho_progresso,
            text=f"0 de {len(self.ETAPAS)} etapas concluídas",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        )
        self.label_progresso.grid(row=0, column=1, sticky="e")

        self.barra_progresso = ctk.CTkProgressBar(
            painel,
            height=8,
            corner_radius=4,
            fg_color=Colors.BACKGROUND,
            progress_color=Colors.PRIMARY
        )
        self.barra_progresso.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(8, 16)
        )
        self.barra_progresso.set(0)

        indicadores = ctk.CTkFrame(painel, fg_color="transparent")
        indicadores.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22
        )
        indicadores.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="resumo_gal"
        )

        bloco_acesso = self._criar_bloco_resumo(
            indicadores,
            coluna=0,
            titulo="ACESSO AO PORTAL",
            padx=(0, 6)
        )
        self.label_acesso = self._criar_label_estado_resumo(
            bloco_acesso,
            "○ Login pendente"
        )

        bloco_arquivos = self._criar_bloco_resumo(
            indicadores,
            coluna=1,
            titulo="ARQUIVOS DO DIA",
            padx=(6, 0)
        )
        self.label_arquivos = self._criar_label_estado_resumo(
            bloco_arquivos,
            "○ Arquivos pendentes"
        )

        self.container_botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        self.container_botoes.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(16, 8)
        )

        self.botao_iniciar = ctk.CTkButton(
            self.container_botoes,
            text="▶ Iniciar rotina",
            command=self._iniciar_atualizacao,
            width=180,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_cancelar = self._criar_botao_secundario(
            self.container_botoes,
            "■ Cancelar",
            self._cancelar_atualizacao,
            130,
            estado="disabled"
        )
        self.botao_atualizar_estado = self._criar_botao_secundario(
            self.container_botoes,
            "↻ Atualizar estado",
            self._atualizar_estado_manual,
            165
        )
        self.botao_resetar = self._criar_botao_secundario(
            self.container_botoes,
            "↺ Resetar teste",
            self._resetar_teste,
            155
        )
        self.botoes_execucao = (
            self.botao_iniciar,
            self.botao_cancelar,
            self.botao_atualizar_estado,
            self.botao_resetar
        )
        self.container_botoes.bind(
            "<Configure>",
            self._ajustar_layout_botoes,
            add="+"
        )

        self.label_checkpoint = ctk.CTkLabel(
            painel,
            text="○ Atualização semanal pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_checkpoint.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=22,
            pady=(6, 18)
        )

    def _criar_bloco_resumo(
        self,
        master,
        coluna: int,
        titulo: str,
        padx: tuple[int, int]
    ) -> ctk.CTkFrame:
        bloco = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=6
        )
        bloco.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=padx
        )
        ctk.CTkLabel(
            bloco,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).pack(fill="x", padx=12, pady=(10, 3))
        return bloco

    def _criar_label_estado_resumo(
        self,
        master,
        texto: str
    ) -> ctk.CTkLabel:
        label = ctk.CTkLabel(
            master,
            text=texto,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        label.pack(fill="x", padx=12, pady=(0, 10))
        return label

    def _criar_botao_secundario(
        self,
        master,
        texto: str,
        comando,
        largura: int,
        estado: str = "normal"
    ) -> ctk.CTkButton:
        return ctk.CTkButton(
            master,
            text=texto,
            command=comando,
            width=largura,
            height=38,
            corner_radius=7,
            state=estado,
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

    def _criar_titulo_destinos(self):
        cabecalho = ctk.CTkFrame(
            self.conteudo,
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
        ).grid(row=0, column=0, sticky="ew")

        self.label_descricao_destinos = ctk.CTkLabel(
            cabecalho,
            text=(
                "O mesmo CSV validado substitui a versão da semana "
                "no histórico, no Banco_Atual e no TesteSORO."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left"
        )
        self.label_descricao_destinos.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(3, 0)
        )

    def _criar_cards_destinos(self):
        self.container_destinos = ctk.CTkFrame(
            self.conteudo,
            fg_color="transparent"
        )
        self.container_destinos.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=6
        )

        self.card_historico = self._criar_card_destino(
            coluna=0,
            icone="🗂️",
            titulo="Histórico",
            descricao=(
                "ZIP gal_aaaa-mm-dd.zip contendo "
                "gal_aaaa-mm-dd.csv, organizado por ano e mês em "
                "Documents\\GAL\\Historico."
            ),
            texto_atalho="📂 Abrir histórico",
            chave_pasta="historico"
        )
        self.card_banco_atual = self._criar_card_destino(
            coluna=1,
            icone="🗃️",
            titulo="Banco atual",
            descricao=(
                "gal_sorotipo.csv substituído em "
                "Documents\\GAL\\Banco_Atual."
            ),
            texto_atalho="📂 Abrir Banco_Atual",
            chave_pasta="banco_atual"
        )
        self.card_teste_soro = self._criar_card_destino(
            coluna=2,
            icone="🧪",
            titulo="TesteSORO",
            descricao=(
                "gal_sorotipo-TESTE.csv substituído em "
                "F:\\Antropozoonoses\\TesteSORO."
            ),
            texto_atalho="📂 Abrir TesteSORO",
            chave_pasta="teste_soro"
        )

        self.cards_destinos = (
            self.card_historico,
            self.card_banco_atual,
            self.card_teste_soro
        )
        self.container_destinos.bind(
            "<Configure>",
            self._ajustar_layout_destinos,
            add="+"
        )

    def _criar_card_destino(
        self,
        coluna: int,
        icone: str,
        titulo: str,
        descricao: str,
        texto_atalho: str,
        chave_pasta: str
    ) -> dict:
        card = ctk.CTkFrame(
            self.container_destinos,
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
                else ((6, 0) if coluna == 2 else 6)
            )
        )
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(2, weight=1)

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
        ).place(relx=0.5, rely=0.5, anchor="center")

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
            font=ctk.CTkFont(family="Segoe UI", size=11),
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

        ctk.CTkFrame(
            card,
            height=1,
            fg_color=Colors.DIVIDER
        ).grid(
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

        botao = ctk.CTkButton(
            card,
            text=texto_atalho,
            command=lambda: self._abrir_pasta(chave_pasta),
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
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(0, 16)
        )

        return {
            "frame": card,
            "status": label_status,
            "descricao": label_descricao,
            "atalho": botao
        }

    def _criar_painel_progresso(self):
        painel = self._novo_painel(3, (18, 20))

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

        self.label_descricao_progresso = ctk.CTkLabel(
            painel,
            text=(
                "A linha do tempo acompanha as etapas reais. O painel "
                "só é concluído depois da confirmação dos três destinos."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_descricao_progresso.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 16)
        )

        container = ctk.CTkFrame(painel, fg_color="transparent")
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 18)
        )
        container.grid_columnconfigure(1, weight=1)

        for indice, (chave, titulo, detalhe) in enumerate(self.ETAPAS):
            self._componentes_etapas[chave] = (
                self._criar_item_linha_tempo(
                    master=container,
                    indice=indice,
                    titulo=titulo,
                    detalhe=detalhe
                )
            )

    def _criar_item_linha_tempo(
        self,
        master,
        indice: int,
        titulo: str,
        detalhe: str
    ) -> dict:
        linha = indice * 2
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
            row=linha,
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
        label_indicador.place(relx=0.5, rely=0.5, anchor="center")

        textos = ctk.CTkFrame(master, fg_color="transparent")
        textos.grid(
            row=linha,
            column=1,
            sticky="ew",
            pady=(0, 4)
        )
        textos.grid_columnconfigure(0, weight=1)

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
        label_titulo.grid(row=0, column=0, sticky="ew")

        label_detalhe = ctk.CTkLabel(
            textos,
            text=detalhe,
            font=ctk.CTkFont(family="Segoe UI", size=10),
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
        if indice < len(self.ETAPAS) - 1:
            conector = ctk.CTkFrame(
                master,
                width=2,
                height=22,
                fg_color=Colors.BORDER,
                corner_radius=0
            )
            conector.grid(
                row=linha + 1,
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

    def _carregar_icone_gal(self) -> ctk.CTkImage | None:
        raiz = Path(__file__).resolve().parents[3]
        pasta = raiz / "assets" / "sistemas"
        original = pasta / "gal_logo.png"
        claro = pasta / "gal_logo_light.png"
        escuro = pasta / "gal_logo_dark.png"

        if not original.is_file():
            return None

        try:
            with Image.open(original) as arquivo:
                imagem_original = arquivo.convert("RGBA")

            if claro.is_file():
                with Image.open(claro) as arquivo:
                    imagem_clara = arquivo.convert("RGBA")
            else:
                imagem_clara = imagem_original.copy()

            if escuro.is_file():
                with Image.open(escuro) as arquivo:
                    imagem_escura = arquivo.convert("RGBA")
            else:
                imagem_escura = imagem_original.copy()

            return ctk.CTkImage(
                light_image=imagem_clara,
                dark_image=imagem_escura,
                size=(27, 27)
            )
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Ações e eventos
    # ------------------------------------------------------------------

    def _iniciar_atualizacao(self):
        if self.atualizacao_service.esta_em_execucao():
            return

        if self.atualizacao_service.esta_concluida_hoje():
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="GAL já atualizado",
                mensagem=(
                    "A atualização do GAL já foi concluída hoje. "
                    "O ArboHub bloqueou uma nova execução para evitar "
                    "substituições desnecessárias."
                ),
                tipo="informacao"
            )
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Iniciar atualização do GAL",
            mensagem=(
                "O navegador será aberto no portal oficial do GAL.\n\n"
                "Faça o login e preencha o CAPTCHA manualmente. "
                "Depois disso, não feche o navegador: o ArboHub "
                "continuará a rotina automaticamente."
            ),
            texto_confirmar="Abrir GAL",
            texto_cancelar="Agora não"
        )

        if not confirmou:
            return

        self._reiniciar_progresso()
        if self.atualizacao_service.iniciar():
            self._registrar_operacao(
                "Atualização semanal iniciada; aguardando o acesso ao GAL."
            )
            self.label_status_execucao.configure(
                text="Preparando a atualização semanal do GAL...",
                text_color=Colors.PRIMARY
            )
            self._atualizar_controles()

    def _cancelar_atualizacao(self):
        if self.atualizacao_service.esta_em_execucao():
            self.atualizacao_service.cancelar()
            self.botao_cancelar.configure(state="disabled")
            self._registrar_operacao("Cancelamento solicitado.")

    def _agendar_eventos(self):
        if self._pagina_destruida:
            return
        self._polling_id = self.after(120, self._processar_eventos)

    def _processar_eventos(self):
        self._polling_id = None
        if self._pagina_destruida:
            return

        for evento in self.atualizacao_service.obter_eventos():
            self._tratar_evento(evento)

        self._atualizar_controles()
        self._agendar_eventos()

    def _tratar_evento(self, evento: dict):
        tipo = evento.get("tipo")
        mensagem = str(evento.get("mensagem", ""))

        if tipo == AtualizacaoGalService.EVENTO_ETAPA:
            etapa = str(evento.get("etapa", ""))
            self._estados_etapas[etapa] = str(
                evento.get("estado", "em_andamento")
            )
            self._mensagens_etapas[etapa] = mensagem
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            self._registrar_operacao(mensagem)
            self._atualizar_linha_tempo()
            return

        if tipo == AtualizacaoGalService.EVENTO_STATUS:
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            self._registrar_operacao(mensagem)
            return

        if tipo == AtualizacaoGalService.EVENTO_CONCLUIDO:
            resultado = evento.get("resultado", {})
            self._registrar_operacao(mensagem)
            self._atualizar_estado_geral()
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.SUCCESS
            )
            self._atualizar_controles()
            self.notificacoes_service.tocar_conclusao()

            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="GAL atualizado",
                mensagem=(
                    f"{mensagem}\n\n"
                    f"Histórico:\n{resultado.get('arquivo_historico', '')}\n\n"
                    f"Banco_Atual:\n{resultado.get('arquivo_banco_atual', '')}\n\n"
                    f"TesteSORO:\n{resultado.get('arquivo_teste', '')}"
                ),
                tipo="sucesso",
                texto_botao="Concluir"
            )
            return

        if tipo == AtualizacaoGalService.EVENTO_CANCELADO:
            etapa = str(evento.get("etapa", ""))
            if etapa:
                self._estados_etapas[etapa] = "cancelada"
                self._mensagens_etapas[etapa] = mensagem
                self._atualizar_linha_tempo()

            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.WARNING
            )
            self._registrar_operacao(mensagem)
            return

        if tipo == AtualizacaoGalService.EVENTO_ERRO:
            etapa = str(evento.get("etapa", ""))
            if etapa:
                self._estados_etapas[etapa] = "erro"
                self._mensagens_etapas[etapa] = mensagem
                self._atualizar_linha_tempo()

            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.ERROR
            )
            self._registrar_operacao(mensagem)
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Atualização do GAL não concluída",
                mensagem=(
                    f"{mensagem}\n\n"
                    "O banco não foi marcado como concluído. "
                    "Feche o navegador do GAL e inicie a rotina "
                    "novamente."
                ),
                tipo="erro"
            )

    # ------------------------------------------------------------------
    # Estado visual
    # ------------------------------------------------------------------

    def _reiniciar_progresso(self):
        self._estados_etapas.clear()
        self._mensagens_etapas.clear()
        self._atualizar_linha_tempo()

    def _atualizar_linha_tempo(self):
        estados_normalizados: dict[str, str] = {}
        restaurar_conclusao = (
            self._concluida_hoje
            and not self.atualizacao_service.esta_em_execucao()
            and all(
                estado in {"aguardando", "concluida", "concluido"}
                for estado in self._estados_etapas.values()
            )
        )

        for indice, (chave, _titulo, _detalhe) in enumerate(self.ETAPAS):
            if restaurar_conclusao:
                estado = "concluido"
            else:
                estado_original = self._estados_etapas.get(
                    chave,
                    "aguardando"
                )
                estado = {
                    "iniciada": "executando",
                    "em_andamento": "executando",
                    "concluida": "concluido",
                    "ignorada": "concluido"
                }.get(estado_original, estado_original)
            estados_normalizados[chave] = estado
            self._aplicar_estado_item(
                componentes=self._componentes_etapas.get(chave),
                estado=estado,
                indice=indice,
                mensagem=self._mensagens_etapas.get(chave)
            )

        for chave, _titulo, _detalhe in self.ETAPAS[:-1]:
            componentes = self._componentes_etapas.get(chave)
            if not componentes or componentes["conector"] is None:
                continue
            componentes["conector"].configure(
                fg_color=(
                    Colors.SUCCESS
                    if estados_normalizados[chave] == "concluido"
                    else Colors.BORDER
                )
            )

        self._atualizar_resumo_visual(estados_normalizados)

    def _aplicar_estado_item(
        self,
        componentes: dict | None,
        estado: str,
        indice: int,
        mensagem: str | None
    ):
        if not componentes:
            return

        configuracoes = {
            "aguardando": (
                str(indice + 1),
                Colors.BUTTON,
                Colors.BORDER,
                Colors.TEXT_MUTED,
                Colors.TEXT_SECONDARY,
                Colors.TEXT_MUTED
            ),
            "executando": (
                "●",
                Colors.PRIMARY,
                Colors.PRIMARY,
                Colors.TEXT_PRIMARY,
                Colors.TEXT_PRIMARY,
                Colors.PRIMARY
            ),
            "concluido": (
                "✔",
                Colors.SUCCESS,
                Colors.SUCCESS,
                Colors.TEXT_PRIMARY,
                Colors.TEXT_PRIMARY,
                Colors.TEXT_SECONDARY
            ),
            "erro": (
                "✕",
                Colors.BUTTON,
                Colors.ERROR,
                Colors.ERROR,
                Colors.TEXT_PRIMARY,
                Colors.ERROR
            ),
            "cancelada": (
                "–",
                Colors.BUTTON,
                Colors.TEXT_MUTED,
                Colors.TEXT_MUTED,
                Colors.TEXT_SECONDARY,
                Colors.TEXT_MUTED
            )
        }
        visual = configuracoes.get(
            estado,
            configuracoes["aguardando"]
        )

        componentes["indicador"].configure(
            fg_color=visual[1],
            border_color=visual[2]
        )
        componentes["label_indicador"].configure(
            text=visual[0],
            text_color=visual[3]
        )
        componentes["titulo"].configure(text_color=visual[4])
        componentes["detalhe"].configure(
            text=(
                mensagem
                or (
                    "Etapa concluída."
                    if estado == "concluido"
                    else componentes["detalhe_padrao"]
                )
            ),
            text_color=visual[5]
        )

    def _atualizar_resumo_visual(self, estados: dict[str, str]):
        total = len(self.ETAPAS)
        concluidas = sum(
            estado == "concluido"
            for estado in estados.values()
        )
        self.barra_progresso.set(concluidas / total)
        self.barra_progresso.configure(
            progress_color=(
                Colors.SUCCESS
                if concluidas == total
                else Colors.PRIMARY
            )
        )
        self.label_progresso.configure(
            text=f"{concluidas} de {total} etapas concluídas"
        )

        self._configurar_indicador_resumo(
            self.label_acesso,
            estados.get(
                AtualizacaoGalService.ETAPA_ACESSO,
                "aguardando"
            ),
            pendente="Login pendente",
            executando="Aguardando acesso manual",
            concluido="Acesso confirmado",
            erro="Falha no acesso"
        )

        etapas_arquivos = (
            AtualizacaoGalService.ETAPA_DOWNLOAD,
            AtualizacaoGalService.ETAPA_HISTORICO,
            AtualizacaoGalService.ETAPA_BANCO_ATUAL,
            AtualizacaoGalService.ETAPA_TESTE_SORO
        )
        estados_arquivos = [
            estados.get(chave, "aguardando")
            for chave in etapas_arquivos
        ]
        if all(item == "concluido" for item in estados_arquivos):
            estado_arquivo = "concluido"
        elif any(item == "erro" for item in estados_arquivos):
            estado_arquivo = "erro"
        elif any(item == "executando" for item in estados_arquivos):
            estado_arquivo = "executando"
        else:
            estado_arquivo = "aguardando"

        self._configurar_indicador_resumo(
            self.label_arquivos,
            estado_arquivo,
            pendente="Arquivos pendentes",
            executando="Atualizando arquivos",
            concluido="Arquivos atualizados",
            erro="Atualização incompleta"
        )

        self._aplicar_estado_card(
            self.card_historico,
            estados.get(
                AtualizacaoGalService.ETAPA_HISTORICO,
                "aguardando"
            )
        )
        self._aplicar_estado_card(
            self.card_banco_atual,
            estados.get(
                AtualizacaoGalService.ETAPA_BANCO_ATUAL,
                "aguardando"
            )
        )
        self._aplicar_estado_card(
            self.card_teste_soro,
            estados.get(
                AtualizacaoGalService.ETAPA_TESTE_SORO,
                "aguardando"
            )
        )

    def _configurar_indicador_resumo(
        self,
        label,
        estado: str,
        pendente: str,
        executando: str,
        concluido: str,
        erro: str
    ):
        apresentacao = {
            "aguardando": (f"○ {pendente}", Colors.TEXT_MUTED),
            "executando": (f"● {executando}", Colors.PRIMARY),
            "concluido": (f"✔️ {concluido}", Colors.SUCCESS),
            "erro": (f"× {erro}", Colors.ERROR),
            "cancelada": ("○ Atualização cancelada", Colors.TEXT_MUTED)
        }
        texto, cor = apresentacao.get(
            estado,
            apresentacao["aguardando"]
        )
        label.configure(text=texto, text_color=cor)

    def _aplicar_estado_card(self, card: dict, estado: str):
        apresentacao = {
            "aguardando": ("○ Aguardando rotina", Colors.TEXT_MUTED),
            "executando": ("● Atualizando", Colors.PRIMARY),
            "concluido": ("✔️ Atualizado", Colors.SUCCESS),
            "erro": ("× Falha na atualização", Colors.ERROR),
            "cancelada": ("○ Atualização cancelada", Colors.TEXT_MUTED)
        }
        texto, cor = apresentacao.get(
            estado,
            apresentacao["aguardando"]
        )
        card["status"].configure(text=texto, text_color=cor)

    def _atualizar_estado_geral(self):
        hoje = date.today()
        estado = (
            self.atualizacao_service.dashboard_service
            .obter_estado_dia(hoje)
        )["gal"]
        self._concluida_hoje = bool(estado["concluido"])
        data_inicio, data_fim = (
            self.atualizacao_service.arquivos_service
            .intervalo_semanal(hoje)
        )

        periodo = (
            f"{data_inicio.strftime('%d/%m/%Y')} a "
            f"{data_fim.strftime('%d/%m/%Y')}"
        )

        if estado["concluido"]:
            horario = self._formatar_horario(
                estado.get("atualizacao_em")
            )
            self.label_status_execucao.configure(
                text=(
                    f"O relatório semanal de {periodo} já está "
                    "disponível. Use “Resetar teste” somente se "
                    "precisar repetir a rotina."
                ),
                text_color=Colors.TEXT_SECONDARY
            )
            self.label_checkpoint.configure(
                text=(
                    "✔️ Atualização semanal concluída"
                    f"{f' às {horario}' if horario else ''}"
                ),
                text_color=Colors.SUCCESS
            )
        elif estado["programado"]:
            self.label_status_execucao.configure(
                text=(
                    f"A rotina desta semana consulta as liberações "
                    f"de {periodo}. O intervalo avança "
                    "automaticamente toda segunda-feira."
                ),
                text_color=Colors.TEXT_SECONDARY
            )
            self.label_checkpoint.configure(
                text="○ Atualização semanal pendente",
                text_color=Colors.TEXT_MUTED
            )
        else:
            self.label_status_execucao.configure(
                text=(
                    f"A rotina semanal consulta as liberações de "
                    f"{periodo}. O intervalo muda automaticamente "
                    "toda segunda-feira."
                ),
                text_color=Colors.TEXT_SECONDARY
            )
            self.label_checkpoint.configure(
                text="○ Atualização disponível",
                text_color=Colors.TEXT_MUTED
            )

    def _atualizar_controles(self):
        executando = self.atualizacao_service.esta_em_execucao()
        concluida = self._concluida_hoje
        self.botao_iniciar.configure(
            state="disabled" if executando or concluida else "normal",
            text=(
                "● Rotina em andamento"
                if executando
                else (
                    "✓ Atualizada hoje"
                    if concluida
                    else "▶ Iniciar rotina"
                )
            )
        )
        self.botao_cancelar.configure(
            state="normal" if executando else "disabled"
        )
        self.botao_atualizar_estado.configure(
            state="disabled" if executando else "normal"
        )
        self.botao_resetar.configure(
            state="disabled" if executando else "normal"
        )
        self._ajustar_layout_botoes()

    @staticmethod
    def _formatar_horario(valor: str | None) -> str:
        if not valor:
            return ""
        try:
            return datetime.fromisoformat(valor).strftime("%H:%M")
        except (TypeError, ValueError):
            return ""

    def _atualizar_estado_manual(self):
        if self.atualizacao_service.esta_em_execucao():
            return
        self._atualizar_estado_geral()
        self._atualizar_linha_tempo()
        self._atualizar_controles()

    def _resetar_teste(self):
        if self.atualizacao_service.esta_em_execucao():
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Resetar atualização do GAL?",
            mensagem=(
                "Este reset é destinado a testes.\n\n"
                "Ele apagará somente o checkpoint visual do GAL "
                "do dia atual e reiniciará as sete etapas.\n\n"
                "Não serão apagados:\n"
                "• o ZIP do histórico;\n"
                "• o arquivo do Banco_Atual;\n"
                "• o arquivo do TesteSORO;\n"
                "• os checkpoints do SINAN."
            ),
            texto_confirmar="Resetar para teste",
            texto_cancelar="Cancelar",
            tipo="aviso"
        )
        if not confirmou:
            return

        (
            self.atualizacao_service.dashboard_service
            .resetar_gal()
        )
        self._estados_etapas.clear()
        self._mensagens_etapas.clear()
        self._atualizar_estado_geral()
        self._atualizar_linha_tempo()
        self._atualizar_controles()

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="GAL pronto para novo teste",
            mensagem=(
                "O checkpoint visual foi resetado.\n\n"
                "Clique em “Iniciar rotina” para repetir o fluxo. "
                "Os arquivos já existentes foram preservados."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def _registrar_operacao(self, mensagem: str):
        if mensagem:
            self._ultima_operacao = mensagem

    # ------------------------------------------------------------------
    # Pastas e responsividade
    # ------------------------------------------------------------------

    def _obter_pastas_destino(self) -> dict[str, Path]:
        arquivos = self.atualizacao_service.arquivos_service
        _inicio, fim = arquivos.intervalo_semanal()
        return {
            "historico": arquivos.pasta_historico_mes(fim),
            "banco_atual": arquivos.pasta_banco_atual,
            "teste_soro": arquivos.pasta_teste_soro
        }

    def _abrir_pasta(self, chave: str):
        try:
            pasta = self._obter_pastas_destino().get(chave)
            if pasta is None:
                raise KeyError("Atalho de pasta desconhecido.")
            pasta = Path(pasta)

            if not pasta.exists():
                mostrar_dialogo_arbohub(
                    master=self.winfo_toplevel(),
                    titulo="Pasta ainda não disponível",
                    mensagem=(
                        "A pasta deste atalho ainda não existe:\n\n"
                        f"{pasta}\n\n"
                        "Ela será criada automaticamente quando a "
                        "rotina correspondente for concluída."
                    ),
                    tipo="aviso"
                )
                return

            if not pasta.is_dir():
                raise NotADirectoryError(
                    f"O caminho não é uma pasta: {pasta}"
                )

            if os.name == "nt":
                os.startfile(str(pasta))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(pasta)])
            else:
                subprocess.Popen(["xdg-open", str(pasta)])

            self._registrar_operacao(f"Pasta aberta: {pasta}")
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

    def _ao_redimensionar(self, _event=None):
        if self._redimensionamento_id is not None:
            try:
                self.after_cancel(self._redimensionamento_id)
            except Exception:
                pass
        self._redimensionamento_id = self.after(
            80,
            self._ajustar_layout_responsivo
        )

    def _ajustar_layout_responsivo(self):
        self._redimensionamento_id = None
        if self._pagina_destruida:
            return

        largura = max(self.winfo_width(), 1)
        if largura < 720:
            margem_cabecalho = 16
            margem_conteudo = 10
        elif largura < 980:
            margem_cabecalho = 26
            margem_conteudo = 20
        else:
            margem_cabecalho = 40
            margem_conteudo = 34

        self.cabecalho.grid_configure(padx=margem_cabecalho)
        self.conteudo_base.grid_configure(padx=margem_conteudo)
        self._ajustar_layout_botoes()
        self._ajustar_layout_destinos()
        self._ajustar_quebra_textos()

    def _ajustar_layout_botoes(self, event=None):
        largura = (
            event.width
            if event is not None
            else self.container_botoes.winfo_width()
        )
        if largura <= 1:
            return

        if largura < 520:
            colunas = 1
        elif largura < 900:
            colunas = 2
        else:
            colunas = 4

        if self._layout_botoes_colunas == colunas:
            return

        for indice in range(4):
            self.container_botoes.grid_columnconfigure(
                indice,
                weight=1 if indice < colunas else 0,
                uniform="botoes_gal" if indice < colunas else ""
            )

        for indice, botao in enumerate(self.botoes_execucao):
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
                    and len(self.botoes_execucao) > colunas
                    else ((5, 0) if linha > 0 else 0)
                )
            )

        self._layout_botoes_colunas = colunas

    def _ajustar_layout_destinos(self, event=None):
        largura = (
            event.width
            if event is not None
            else self.container_destinos.winfo_width()
        )
        if largura <= 1:
            return

        colunas = 1 if largura < 920 else 3

        if self._layout_destinos_colunas == colunas and event is not None:
            return

        for coluna in range(3):
            self.container_destinos.grid_columnconfigure(
                coluna,
                weight=1 if coluna < colunas else 0,
                uniform="destinos_gal" if coluna < colunas else ""
            )

        if colunas == 1:
            for indice, card in enumerate(self.cards_destinos):
                card["frame"].grid_configure(
                    row=indice,
                    column=0,
                    columnspan=1,
                    sticky="ew",
                    padx=0,
                    pady=(0, 10 if indice < 2 else 0)
                )
        else:
            for indice, card in enumerate(self.cards_destinos):
                card["frame"].grid_configure(
                    row=0,
                    column=indice,
                    columnspan=1,
                    sticky="nsew",
                    padx=(
                        (0, 6)
                        if indice == 0
                        else ((6, 0) if indice == 2 else 6)
                    ),
                    pady=0
                )

        self._layout_destinos_colunas = colunas
        self.after(20, self._ajustar_quebra_cards)

    def _ajustar_quebra_cards(self):
        if self._pagina_destruida:
            return
        for card in self.cards_destinos:
            largura = card["frame"].winfo_width()
            if largura > 1:
                card["descricao"].configure(
                    wraplength=max(
                        min(largura - 64, 245),
                        180
                    )
                )

    def _ajustar_quebra_textos(self):
        largura = max(self.conteudo.winfo_width() - 70, 220)
        for label in (
            self.label_status_execucao,
            self.label_descricao_progresso
        ):
            label.configure(wraplength=largura)
        self.label_descricao_destinos.configure(
            wraplength=max(largura, 220)
        )
        self._ajustar_quebra_cards()

    def _ao_destruir(self, event):
        if event.widget is not self:
            return

        self._pagina_destruida = True
        for identificador in (
            self._polling_id,
            self._redimensionamento_id
        ):
            if identificador is None:
                continue
            try:
                self.after_cancel(identificador)
            except Exception:
                pass
