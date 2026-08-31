from __future__ import annotations

import os
import queue
import subprocess
import sys
import tkinter as tk
from datetime import date
from pathlib import Path
from threading import Thread

import customtkinter as ctk
from tkinter import filedialog

from app.gui.components.arbohub_dialog import mostrar_dialogo_arbohub
from app.gui.components.icones_navegacao import criar_icone_navegacao
from app.gui.components.seletor_data import (
    CalendarioDialog,
    SemanaEpidemiologicaDialog,
)
from app.gui.themes.colors import Colors
from app.services.configuracoes_service import ConfiguracoesService
from app.services.qualifica.interface_72h import (
    converter_data_interface,
    criar_nome_relatorio_72h,
    formatar_data_digitada,
    obter_caminho_dicionario_municipios,
    obter_pasta_padrao_relatorios_72h,
    validar_nome_relatorio_72h,
)
from app.services.qualifica.relatorio_72h_service import (
    Relatorio72hService,
    ResultadoRelatorio72h,
)


class QualificaPage(ctk.CTkScrollableFrame):
    """Página dos indicadores Qualifica, iniciando pelo relatório de 72h."""

    LIMITE_LAYOUT_VERTICAL = 980

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED,
        )

        self.relatorio_service = Relatorio72hService()
        self.configuracoes_service = ConfiguracoesService()
        configuracoes = self.configuracoes_service.carregar()
        caminho_personalizado = str(
            configuracoes.get("qualifica", {}).get(
                "dicionario_municipios",
                "",
            )
        ).strip()
        self.dicionario_personalizado = bool(caminho_personalizado)
        self.caminho_dicionario = (
            Path(caminho_personalizado)
            if caminho_personalizado
            else obter_caminho_dicionario_municipios()
        )
        self.pasta_saida = obter_pasta_padrao_relatorios_72h()
        self.caminhos_dbf: list[Path] = []
        self.ultimo_relatorio: Path | None = None
        self._eventos: queue.Queue[dict] = queue.Queue()
        self._thread: Thread | None = None
        self._polling_id = None
        self._redimensionamento_id = None
        self._aguardando_resultado = False
        self._pagina_destruida = False
        self._formatando_data = False
        self._layout_vertical: bool | None = None
        self._ultimo_nome_sugerido = ""

        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        self.data_inicial_var = tk.StringVar(
            value=inicio_mes.strftime("%d/%m/%Y")
        )
        self.data_final_var = tk.StringVar(
            value=hoje.strftime("%d/%m/%Y")
        )
        self.nome_saida_var = tk.StringVar(value="")

        self._icone_calendario = criar_icone_navegacao(
            "calendario",
            tamanho=18,
        )

        self.grid_columnconfigure(0, weight=1)
        self._criar_cabecalho()
        self._criar_abas()
        self._criar_workspace()

        self.data_inicial_var.trace_add(
            "write",
            lambda *_: self._ao_alterar_data(
                self.data_inicial_var
            ),
        )
        self.data_final_var.trace_add(
            "write",
            lambda *_: self._ao_alterar_data(
                self.data_final_var
            ),
        )
        self.nome_saida_var.trace_add(
            "write",
            lambda *_: self._atualizar_prontidao(),
        )

        self.bind("<Configure>", self._ao_redimensionar, add="+")
        self.bind("<Destroy>", self._ao_destruir, add="+")
        self.after(60, self._validar_dicionario_inicial)
        self.after(90, self._ajustar_layout_responsivo)

    # ------------------------------------------------------------------
    # Construção visual
    # ------------------------------------------------------------------

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
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
            text="Qualifica",
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
                "Indicadores de oportunidade e qualidade da "
                "vigilância epidemiológica."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 0),
        )

    def _criar_abas(self):
        self.container_abas = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE_SECONDARY,
            corner_radius=9,
        )
        self.container_abas.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 14),
        )
        self.container_abas.grid_columnconfigure(
            (0, 1, 2, 3),
            weight=1,
            uniform="qualifica_abas",
        )

        abas = (
            ("72 horas", True),
            ("60 dias", False),
            ("GAL × SINAN", False),
            ("Certidões", False),
        )
        for coluna, (texto, ativa) in enumerate(abas):
            botao = ctk.CTkButton(
                self.container_abas,
                text=texto,
                height=42,
                corner_radius=7,
                fg_color=(
                    Colors.PRIMARY
                    if ativa
                    else "transparent"
                ),
                hover_color=(
                    Colors.PRIMARY_HOVER
                    if ativa
                    else Colors.SURFACE_HOVER
                ),
                text_color=(
                    Colors.TEXT_ON_PRIMARY
                    if ativa
                    else Colors.TEXT_DISABLED
                ),
                state="normal" if ativa else "disabled",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=13,
                    weight="bold",
                ),
            )
            botao.grid(
                row=0,
                column=coluna,
                sticky="ew",
                padx=(
                    5 if coluna == 0 else 2,
                    5 if coluna == 3 else 2,
                ),
                pady=5,
            )

    def _criar_workspace(self):
        self.workspace = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.workspace.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=40,
            pady=(0, 36),
        )
        self.workspace.grid_columnconfigure(0, weight=3)
        self.workspace.grid_columnconfigure(1, weight=1)

        self.painel_formulario = ctk.CTkFrame(
            self.workspace,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.painel_formulario.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )
        self.painel_formulario.grid_columnconfigure(0, weight=1)

        self._criar_cabecalho_formulario()
        self._criar_formulario()

        self.coluna_lateral = ctk.CTkFrame(
            self.workspace,
            fg_color="transparent",
        )
        self.coluna_lateral.grid(
            row=0,
            column=1,
            sticky="new",
            padx=(7, 0),
        )
        self.coluna_lateral.grid_columnconfigure(0, weight=1)

        self._criar_painel_regra()
        self._criar_painel_resultado()

    def _criar_cabecalho_formulario(self):
        cabecalho = ctk.CTkFrame(
            self.painel_formulario,
            fg_color=Colors.SURFACE_SECONDARY,
            corner_radius=9,
        )
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.grid_columnconfigure(1, weight=1)

        bloco_icone = ctk.CTkFrame(
            cabecalho,
            width=42,
            height=42,
            fg_color=Colors.SURFACE_SELECTED,
            corner_radius=9,
        )
        bloco_icone.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(18, 12),
            pady=16,
        )
        bloco_icone.grid_propagate(False)

        ctk.CTkLabel(
            bloco_icone,
            text="72h",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold",
            ),
            text_color=Colors.PRIMARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            cabecalho,
            text="Oportunidade de digitação em até 72 horas",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 18),
            pady=(16, 2),
        )

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Compare a data de notificação com a data de "
                "digitação no SINAN."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=1,
            column=1,
            sticky="nw",
            padx=(0, 18),
            pady=(0, 16),
        )

    def _criar_formulario(self):
        formulario = ctk.CTkFrame(
            self.painel_formulario,
            fg_color="transparent",
        )
        formulario.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=20,
        )
        formulario.grid_columnconfigure(1, weight=1)

        conteudo_dicionario = self._criar_etapa(
            formulario,
            linha=0,
            numero="1",
            titulo="Dicionário de municípios",
        )
        self._criar_entrada_dicionario(conteudo_dicionario)

        conteudo_dbf = self._criar_etapa(
            formulario,
            linha=1,
            numero="2",
            titulo="Bancos brutos do SINAN",
            pady=(20, 0),
        )
        self._criar_entrada_dbf(conteudo_dbf)

        conteudo_datas = self._criar_etapa(
            formulario,
            linha=2,
            numero="3",
            titulo="Período de primeiros sintomas",
            pady=(20, 0),
        )
        self._criar_entrada_datas(conteudo_datas)

        self._criar_destino_saida(formulario, linha=3)
        self._criar_rodape_formulario(formulario, linha=4)

    def _criar_etapa(
        self,
        master,
        *,
        linha: int,
        numero: str,
        titulo: str,
        pady: tuple[int, int] = (0, 0),
    ) -> ctk.CTkFrame:
        marcador = ctk.CTkFrame(
            master,
            width=28,
            height=28,
            corner_radius=14,
            fg_color=Colors.SURFACE_SELECTED,
        )
        marcador.grid(
            row=linha,
            column=0,
            sticky="n",
            padx=(0, 11),
            pady=pady,
        )
        marcador.grid_propagate(False)
        ctk.CTkLabel(
            marcador,
            text=numero,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            text_color=Colors.PRIMARY,
        ).place(relx=0.5, rely=0.5, anchor="center")

        conteudo = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        conteudo.grid(
            row=linha,
            column=1,
            sticky="ew",
            pady=pady,
        )
        conteudo.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            conteudo,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 7))
        return conteudo

    def _criar_entrada_dicionario(self, master):
        campo = ctk.CTkFrame(
            master,
            height=46,
            fg_color=Colors.INPUT,
            corner_radius=7,
            border_width=1,
            border_color=Colors.INPUT_BORDER,
        )
        campo.grid(row=1, column=0, sticky="ew")
        campo.grid_columnconfigure(1, weight=1)

        self.label_dicionario_icone = ctk.CTkLabel(
            campo,
            text="✓",
            width=34,
            text_color=Colors.SUCCESS,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.label_dicionario_icone.grid(
            row=0,
            column=0,
            padx=(8, 0),
            pady=8,
        )

        self.label_dicionario = ctk.CTkLabel(
            campo,
            text=(
                f"{self.caminho_dicionario.name} · carregando "
                "automaticamente"
            ),
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            anchor="w",
        )
        self.label_dicionario.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(4, 10),
            pady=8,
        )

        self.label_dicionario_ajuda = ctk.CTkLabel(
            master,
            text=(
                "Para substituir o arquivo, use Configurações → "
                "Dados e arquivos → Dicionário do Qualifica."
            ),
            text_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
            ),
            anchor="w",
        )
        self.label_dicionario_ajuda.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(6, 0),
        )

    def _criar_entrada_dbf(self, master):
        linha = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        linha.grid(row=1, column=0, sticky="ew")
        linha.grid_columnconfigure(0, weight=1)

        campo = ctk.CTkFrame(
            linha,
            height=44,
            fg_color=Colors.INPUT,
            corner_radius=7,
            border_width=1,
            border_color=Colors.INPUT_BORDER,
        )
        campo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        campo.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            campo,
            text="▤",
            width=34,
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI Symbol",
                size=16,
            ),
        ).grid(row=0, column=0, padx=(8, 0), pady=7)

        self.label_quantidade_dbf = ctk.CTkLabel(
            campo,
            text="Nenhum banco DBF selecionado",
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
        )
        self.label_quantidade_dbf.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(4, 10),
            pady=7,
        )

        self.botao_adicionar_dbf = ctk.CTkButton(
            linha,
            text="Adicionar DBFs",
            command=self._selecionar_dbfs,
            width=132,
            height=44,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
        )
        self.botao_adicionar_dbf.grid(row=0, column=1, sticky="e")

        self.container_arquivos_dbf = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        self.container_arquivos_dbf.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )
        self.container_arquivos_dbf.grid_columnconfigure(0, weight=1)
        self._renderizar_arquivos_dbf()

    def _criar_entrada_datas(self, master):
        self.container_datas = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        self.container_datas.grid(row=1, column=0, sticky="ew")
        self.container_datas.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="datas_qualifica",
        )

        self.entrada_data_inicial = self._criar_campo_data(
            self.container_datas,
            coluna=0,
            titulo="Data inicial",
            variavel=self.data_inicial_var,
            ao_abrir=lambda: self._abrir_calendario(
                self.data_inicial_var
            ),
            padx=(0, 5),
        )
        self.entrada_data_final = self._criar_campo_data(
            self.container_datas,
            coluna=1,
            titulo="Data final",
            variavel=self.data_final_var,
            ao_abrir=lambda: self._abrir_calendario(
                self.data_final_var
            ),
            padx=(5, 0),
        )

        ajuda = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        ajuda.grid(row=2, column=0, sticky="ew", pady=(7, 0))
        ajuda.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            ajuda,
            text=(
                "Digite somente os números: as barras aparecem "
                "automaticamente."
            ),
            text_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
            ),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        self.botao_semana = ctk.CTkButton(
            ajuda,
            text="Escolher por SE",
            command=self._abrir_seletor_semana,
            width=112,
            height=30,
            corner_radius=7,
            fg_color=Colors.SURFACE_SELECTED,
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
        )
        self.botao_semana.grid(row=0, column=1, sticky="e")

    def _criar_campo_data(
        self,
        master,
        *,
        coluna: int,
        titulo: str,
        variavel: tk.StringVar,
        ao_abrir,
        padx: tuple[int, int],
    ) -> ctk.CTkEntry:
        container = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        container.grid(
            row=0,
            column=coluna,
            sticky="ew",
            padx=padx,
        )
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text=titulo,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        entrada = ctk.CTkEntry(
            container,
            textvariable=variavel,
            height=42,
            corner_radius=7,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text="DD/MM/AAAA",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
            ),
        )
        entrada.grid(row=1, column=0, sticky="ew")

        botao = ctk.CTkButton(
            container,
            text="",
            image=self._icone_calendario,
            command=ao_abrir,
            width=42,
            height=42,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
        )
        botao.grid(row=1, column=1, sticky="e", padx=(6, 0))
        return entrada

    def _criar_destino_saida(self, master, *, linha: int):
        self.painel_destino = ctk.CTkFrame(
            master,
            fg_color=Colors.INPUT,
            corner_radius=8,
            border_width=1,
            border_color=Colors.INPUT_BORDER,
        )
        self.painel_destino.grid(
            row=linha,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 0),
        )
        self.painel_destino.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.painel_destino,
            text="▦",
            width=36,
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI Symbol",
                size=17,
            ),
        ).grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(12, 2),
            pady=12,
        )

        ctk.CTkLabel(
            self.painel_destino,
            text="Arquivo Excel de saída — nome editável",
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 8),
            pady=(11, 0),
        )

        self.label_pasta_saida = ctk.CTkLabel(
            self.painel_destino,
            text=str(self.pasta_saida),
            text_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
            ),
            anchor="w",
        )
        self.label_pasta_saida.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(5, 8),
            pady=(2, 0),
        )

        self.entry_nome_saida = ctk.CTkEntry(
            self.painel_destino,
            textvariable=self.nome_saida_var,
            fg_color=Colors.BACKGROUND,
            border_width=1,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
            height=30,
        )
        self.entry_nome_saida.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(5, 8),
            pady=(5, 11),
        )

        self.botao_alterar_pasta = ctk.CTkButton(
            self.painel_destino,
            text="Alterar pasta",
            command=self._selecionar_pasta_saida,
            width=104,
            height=32,
            corner_radius=7,
            fg_color=Colors.SURFACE_SELECTED,
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
        )
        self.botao_alterar_pasta.grid(
            row=0,
            column=2,
            rowspan=3,
            sticky="e",
            padx=12,
            pady=12,
        )
        self._atualizar_destino_visual()

    def _criar_rodape_formulario(self, master, *, linha: int):
        divisor = ctk.CTkFrame(
            master,
            height=1,
            fg_color=Colors.DIVIDER,
        )
        divisor.grid(
            row=linha,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 0),
        )

        rodape = ctk.CTkFrame(
            master,
            fg_color="transparent",
        )
        rodape.grid(
            row=linha + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(14, 0),
        )
        rodape.grid_columnconfigure(0, weight=1)

        self.label_status = ctk.CTkLabel(
            rodape,
            text="Selecione pelo menos um banco DBF para continuar.",
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
            ),
            anchor="w",
        )
        self.label_status.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 12),
        )

        self.botao_gerar = ctk.CTkButton(
            rodape,
            text="▶  Gerar relatório de 72h",
            command=self._iniciar_relatorio,
            width=222,
            height=42,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold",
            ),
            state="disabled",
        )
        self.botao_gerar.grid(row=0, column=1, sticky="e")

    def _criar_painel_regra(self):
        painel = ctk.CTkFrame(
            self.coluna_lateral,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        painel.grid(row=0, column=0, sticky="ew")
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Regra do indicador",
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(17, 10),
        )

        regras = (
            (
                "▦",
                "Filtra casos pela data dos primeiros sintomas.",
            ),
            (
                "◷",
                "Considera no prazo digitações entre 0 e 3 dias.",
            ),
            (
                "⌖",
                "Consolida resultados por município, CRS e estado.",
            ),
        )
        for linha, (icone, texto) in enumerate(regras, start=1):
            item = ctk.CTkFrame(
                painel,
                fg_color="transparent",
            )
            item.grid(
                row=linha,
                column=0,
                sticky="ew",
                padx=18,
                pady=(0, 12 if linha < 3 else 17),
            )
            item.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                item,
                text=icone,
                width=22,
                text_color=Colors.PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI Symbol",
                    size=14,
                ),
            ).grid(row=0, column=0, sticky="n", padx=(0, 6))
            ctk.CTkLabel(
                item,
                text=texto,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                ),
                justify="left",
                anchor="w",
                wraplength=210,
            ).grid(row=0, column=1, sticky="ew")

    def _criar_painel_resultado(self):
        self.painel_resultado = ctk.CTkFrame(
            self.coluna_lateral,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.painel_resultado.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(14, 0),
        )
        self.painel_resultado.grid_columnconfigure((0, 1, 2), weight=1)

        self.label_resultado_status = ctk.CTkLabel(
            self.painel_resultado,
            text="✓  Relatório concluído com sucesso",
            text_color=Colors.SUCCESS,
            fg_color=Colors.SURFACE_SECONDARY,
            corner_radius=7,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold",
            ),
            anchor="w",
        )
        self.label_resultado_status.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(14, 10),
            ipady=9,
        )

        self.labels_resultado = {}
        for coluna, (chave, rotulo) in enumerate(
            (
                ("notificacoes", "Notificações"),
                ("prazo", "No prazo"),
                ("estado", "Estado"),
            )
        ):
            bloco = ctk.CTkFrame(
                self.painel_resultado,
                fg_color=Colors.INPUT,
                corner_radius=7,
            )
            bloco.grid(
                row=1,
                column=coluna,
                sticky="nsew",
                padx=(
                    14 if coluna == 0 else 4,
                    14 if coluna == 2 else 4,
                ),
                pady=(0, 10),
            )
            ctk.CTkLabel(
                bloco,
                text=rotulo,
                text_color=Colors.TEXT_MUTED,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=8,
                ),
            ).pack(fill="x", padx=8, pady=(9, 2))
            label_valor = ctk.CTkLabel(
                bloco,
                text="—",
                text_color=Colors.TEXT_PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=17,
                    weight="bold",
                ),
            )
            label_valor.pack(fill="x", padx=8, pady=(0, 9))
            self.labels_resultado[chave] = label_valor

        botoes = ctk.CTkFrame(
            self.painel_resultado,
            fg_color="transparent",
        )
        botoes.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(0, 14),
        )
        botoes.grid_columnconfigure((0, 1), weight=1)

        self.botao_abrir_excel = ctk.CTkButton(
            botoes,
            text="Abrir Excel",
            command=self._abrir_ultimo_relatorio,
            height=36,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        self.botao_abrir_excel.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 4),
        )

        self.botao_abrir_pasta = ctk.CTkButton(
            botoes,
            text="Abrir pasta",
            command=lambda: self._abrir_caminho(self.pasta_saida),
            height=36,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        self.botao_abrir_pasta.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(4, 0),
        )

        self.painel_resultado.grid_remove()

    # ------------------------------------------------------------------
    # Entradas e estado
    # ------------------------------------------------------------------

    def _validar_dicionario_inicial(self):
        try:
            municipios = self.relatorio_service.carregar_municipios(
                self.caminho_dicionario
            )
        except Exception as erro:
            self.label_dicionario_icone.configure(
                text="!",
                text_color=Colors.ERROR,
            )
            self.label_dicionario.configure(
                text="Dicionário configurado indisponível",
                text_color=Colors.ERROR,
            )
            self.label_dicionario_ajuda.configure(text=str(erro))
            self._atualizar_prontidao()
            return

        self.label_dicionario.configure(
            text=(
                f"{self.caminho_dicionario.name} · "
                f"{len(municipios)} municípios · "
                + (
                    "personalizado"
                    if self.dicionario_personalizado
                    else "padrão do ArboHub"
                )
            )
        )
        self._atualizar_prontidao()

    def _selecionar_dbfs(self):
        selecionados = filedialog.askopenfilenames(
            parent=self.winfo_toplevel(),
            title="Selecionar bancos brutos do SINAN",
            filetypes=(
                ("Bancos DBF do SINAN", "*.dbf"),
                ("Todos os arquivos", "*.*"),
            ),
        )
        if not selecionados:
            return

        novos = [Path(caminho) for caminho in selecionados]
        invalidos = [
            caminho.name
            for caminho in novos
            if caminho.suffix.casefold() != ".dbf"
        ]
        if invalidos:
            mostrar_dialogo_arbohub(
                master=self,
                titulo="Arquivo incompatível",
                mensagem=(
                    "Selecione somente bancos com extensão DBF.\n\n"
                    "Arquivos ignorados:\n- "
                    + "\n- ".join(invalidos)
                ),
                tipo="aviso",
            )
            novos = [
                caminho
                for caminho in novos
                if caminho.suffix.casefold() == ".dbf"
            ]

        existentes = {
            str(caminho.resolve()).casefold()
            for caminho in self.caminhos_dbf
        }
        for caminho in novos:
            chave = str(caminho.resolve()).casefold()
            if chave not in existentes:
                self.caminhos_dbf.append(caminho)
                existentes.add(chave)

        self._renderizar_arquivos_dbf()
        self._atualizar_prontidao()

    def _renderizar_arquivos_dbf(self):
        for widget in self.container_arquivos_dbf.winfo_children():
            widget.destroy()

        quantidade = len(self.caminhos_dbf)
        if quantidade == 0:
            self.label_quantidade_dbf.configure(
                text="Nenhum banco DBF selecionado",
                text_color=Colors.TEXT_SECONDARY,
            )
            ctk.CTkLabel(
                self.container_arquivos_dbf,
                text=(
                    "Os arquivos selecionados aparecerão aqui para "
                    "conferência."
                ),
                text_color=Colors.TEXT_MUTED,
                fg_color=Colors.SURFACE_SECONDARY,
                corner_radius=7,
                anchor="w",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                ),
            ).grid(
                row=0,
                column=0,
                sticky="ew",
                ipady=9,
                padx=0,
            )
            return

        self.label_quantidade_dbf.configure(
            text=(
                f"{quantidade} banco DBF selecionado"
                if quantidade == 1
                else f"{quantidade} bancos DBF selecionados"
            ),
            text_color=Colors.TEXT_PRIMARY,
        )

        for linha, caminho in enumerate(self.caminhos_dbf):
            item = ctk.CTkFrame(
                self.container_arquivos_dbf,
                fg_color=Colors.SURFACE_SECONDARY,
                corner_radius=7,
                border_width=1,
                border_color=Colors.BORDER_MUTED,
            )
            item.grid(
                row=linha,
                column=0,
                sticky="ew",
                pady=(0, 6),
            )
            item.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                item,
                text="▤",
                width=30,
                text_color=Colors.PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI Symbol",
                    size=14,
                ),
            ).grid(
                row=0,
                column=0,
                rowspan=2,
                padx=(8, 2),
                pady=7,
            )

            ctk.CTkLabel(
                item,
                text=caminho.name,
                text_color=Colors.TEXT_PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold",
                ),
                anchor="w",
            ).grid(
                row=0,
                column=1,
                sticky="ew",
                padx=(3, 8),
                pady=(7, 0),
            )

            ctk.CTkLabel(
                item,
                text=str(caminho.parent),
                text_color=Colors.TEXT_MUTED,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=8,
                ),
                anchor="w",
            ).grid(
                row=1,
                column=1,
                sticky="ew",
                padx=(3, 8),
                pady=(0, 7),
            )

            ctk.CTkButton(
                item,
                text="×",
                command=(
                    lambda valor=caminho: self._remover_dbf(valor)
                ),
                width=30,
                height=30,
                corner_radius=6,
                fg_color="transparent",
                hover_color=Colors.SURFACE_HOVER,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(size=17),
            ).grid(
                row=0,
                column=2,
                rowspan=2,
                padx=7,
                pady=7,
            )

    def _remover_dbf(self, caminho: Path):
        if self._thread is not None and self._thread.is_alive():
            return
        self.caminhos_dbf = [
            item
            for item in self.caminhos_dbf
            if item != caminho
        ]
        self._renderizar_arquivos_dbf()
        self._atualizar_prontidao()

    def _ao_alterar_data(self, variavel: tk.StringVar):
        if self._formatando_data:
            return
        valor = variavel.get()
        formatado = formatar_data_digitada(valor)
        if valor != formatado:
            self._formatando_data = True
            variavel.set(formatado)
            self._formatando_data = False
        self._atualizar_destino_visual()
        self._atualizar_prontidao()

    def _abrir_calendario(self, variavel: tk.StringVar):
        try:
            data_atual = converter_data_interface(variavel.get())
        except ValueError:
            data_atual = date.today()

        CalendarioDialog(
            master=self,
            data_atual=data_atual,
            ao_selecionar=(
                lambda valor: variavel.set(
                    valor.strftime("%d/%m/%Y")
                )
            ),
        )

    def _abrir_seletor_semana(self):
        try:
            referencia = converter_data_interface(
                self.data_inicial_var.get()
            )
        except ValueError:
            referencia = date.today()

        SemanaEpidemiologicaDialog(
            master=self,
            data_referencia=referencia,
            ao_selecionar=self._aplicar_semana,
        )

    def _aplicar_semana(self, inicio: date, fim: date):
        self.data_inicial_var.set(inicio.strftime("%d/%m/%Y"))
        self.data_final_var.set(fim.strftime("%d/%m/%Y"))

    def _selecionar_pasta_saida(self):
        selecionada = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Escolher pasta dos relatórios de 72 horas",
            initialdir=str(self.pasta_saida),
        )
        if not selecionada:
            return
        self.pasta_saida = Path(selecionada)
        self._atualizar_destino_visual()

    def _atualizar_destino_visual(self):
        if not hasattr(self, "entry_nome_saida"):
            return
        self.label_pasta_saida.configure(text=str(self.pasta_saida))
        nome_sugerido = ""
        try:
            inicio = converter_data_interface(
                self.data_inicial_var.get()
            )
            fim = converter_data_interface(
                self.data_final_var.get()
            )
            nome_sugerido = criar_nome_relatorio_72h(inicio, fim)
        except (TypeError, ValueError):
            pass

        nome_atual = self.nome_saida_var.get().strip()
        if not nome_atual or nome_atual == self._ultimo_nome_sugerido:
            self.nome_saida_var.set(nome_sugerido)
        self._ultimo_nome_sugerido = nome_sugerido

    def _atualizar_prontidao(self):
        if not hasattr(self, "botao_gerar"):
            return
        processando = self._thread is not None and self._thread.is_alive()
        dicionario_ok = self.caminho_dicionario.is_file()
        dbfs_ok = bool(self.caminhos_dbf)
        datas_ok = False
        nome_ok = False
        try:
            inicio = converter_data_interface(
                self.data_inicial_var.get()
            )
            fim = converter_data_interface(
                self.data_final_var.get()
            )
            datas_ok = inicio <= fim
        except ValueError:
            pass

        try:
            validar_nome_relatorio_72h(
                self.nome_saida_var.get()
            )
            nome_ok = True
        except ValueError:
            pass

        pronto = (
            dicionario_ok
            and dbfs_ok
            and datas_ok
            and nome_ok
            and not processando
        )
        self.botao_gerar.configure(
            state="normal" if pronto else "disabled"
        )

        if processando:
            return
        if not dicionario_ok:
            texto = "O dicionário configurado do Qualifica está indisponível."
        elif not dbfs_ok:
            texto = "Selecione pelo menos um banco DBF para continuar."
        elif not datas_ok:
            texto = "Confira as datas inicial e final do relatório."
        elif not nome_ok:
            texto = "Informe um nome válido para o arquivo Excel."
        else:
            texto = "Tudo pronto para gerar o relatório."
        self.label_status.configure(text=texto)

    # ------------------------------------------------------------------
    # Processamento em segundo plano
    # ------------------------------------------------------------------

    def _iniciar_relatorio(self):
        if self._thread is not None and self._thread.is_alive():
            return

        try:
            inicio = converter_data_interface(
                self.data_inicial_var.get()
            )
            fim = converter_data_interface(
                self.data_final_var.get()
            )
            nome = validar_nome_relatorio_72h(
                self.nome_saida_var.get()
            )
            if not self.caminhos_dbf:
                raise ValueError(
                    "Selecione pelo menos um banco DBF do SINAN."
                )
            if not self.caminho_dicionario.is_file():
                raise FileNotFoundError(
                    "O dicionário configurado do Qualifica não foi "
                    "encontrado. Confira Configurações → Dados e arquivos."
                )
            inexistentes = [
                caminho.name
                for caminho in self.caminhos_dbf
                if not caminho.is_file()
            ]
            if inexistentes:
                raise FileNotFoundError(
                    "Alguns bancos selecionados não estão mais "
                    "disponíveis:\n- "
                    + "\n- ".join(inexistentes)
                )
        except (FileNotFoundError, TypeError, ValueError) as erro:
            mostrar_dialogo_arbohub(
                master=self,
                titulo="Confira os dados do relatório",
                mensagem=str(erro),
                tipo="aviso",
            )
            return

        destino = self.pasta_saida / nome
        self.painel_resultado.grid_remove()
        self._definir_processando(True)
        self._aguardando_resultado = True

        self._thread = Thread(
            target=self._executar_relatorio,
            kwargs={
                "inicio": inicio,
                "fim": fim,
                "destino": destino,
                "dbfs": tuple(self.caminhos_dbf),
            },
            daemon=True,
        )
        self._thread.start()
        self._agendar_eventos()

    def _executar_relatorio(
        self,
        *,
        inicio: date,
        fim: date,
        destino: Path,
        dbfs: tuple[Path, ...],
    ):
        try:
            resultado = self.relatorio_service.gerar_relatorio(
                caminho_dicionario=self.caminho_dicionario,
                caminhos_dbf=dbfs,
                data_inicial=inicio,
                data_final=fim,
                caminho_saida=destino,
                callback_status=(
                    lambda mensagem: self._eventos.put(
                        {
                            "tipo": "status",
                            "mensagem": mensagem,
                        }
                    )
                ),
            )
        except Exception as erro:
            self._eventos.put(
                {
                    "tipo": "erro",
                    "mensagem": str(erro),
                }
            )
            return

        self._eventos.put(
            {
                "tipo": "concluido",
                "resultado": resultado,
                "destino": destino,
            }
        )

    def _agendar_eventos(self):
        if self._pagina_destruida:
            return
        if self._polling_id is None:
            self._polling_id = self.after(
                100,
                self._processar_eventos,
            )

    def _processar_eventos(self):
        self._polling_id = None
        if self._pagina_destruida:
            return

        while True:
            try:
                evento = self._eventos.get_nowait()
            except queue.Empty:
                break

            tipo = evento.get("tipo")
            if tipo == "status":
                self.label_status.configure(
                    text=str(evento.get("mensagem", ""))
                )
            elif tipo == "erro":
                self._aguardando_resultado = False
                self._definir_processando(False)
                mostrar_dialogo_arbohub(
                    master=self,
                    titulo="Relatório não concluído",
                    mensagem=(
                        "O ArboHub preservou os arquivos existentes e "
                        "não conseguiu concluir o relatório.\n\n"
                        f"Detalhe: {evento.get('mensagem', '')}"
                    ),
                    tipo="erro",
                )
            elif tipo == "concluido":
                self._aguardando_resultado = False
                self._concluir_relatorio(
                    evento["resultado"],
                    evento["destino"],
                )

        if self._aguardando_resultado:
            self._agendar_eventos()

    def _definir_processando(self, processando: bool):
        estado = "disabled" if processando else "normal"
        for controle in (
            self.botao_adicionar_dbf,
            self.entrada_data_inicial,
            self.entrada_data_final,
            self.botao_semana,
            self.botao_alterar_pasta,
        ):
            controle.configure(state=estado)

        self.botao_gerar.configure(
            text=(
                "Gerando relatório..."
                if processando
                else "▶  Gerar relatório de 72h"
            ),
            state="disabled" if processando else "normal",
        )
        if processando:
            self.label_status.configure(
                text="Preparando a leitura segura dos bancos DBF."
            )
        else:
            self._atualizar_prontidao()

    def _concluir_relatorio(
        self,
        resultado: ResultadoRelatorio72h,
        destino: Path,
    ):
        self.ultimo_relatorio = destino
        self._definir_processando(False)
        self.label_status.configure(
            text="Excel salvo automaticamente e validado."
        )
        self.labels_resultado["notificacoes"].configure(
            text=str(resultado.total_notificacoes)
        )
        self.labels_resultado["prazo"].configure(
            text=str(resultado.total_dentro_do_prazo)
        )
        self.labels_resultado["estado"].configure(
            text=(
                f"{resultado.percentual_estadual:.2f}%"
                .replace(".", ",")
            )
        )
        self.painel_resultado.grid()

        if resultado.avisos:
            mostrar_dialogo_arbohub(
                master=self,
                titulo="Relatório concluído com avisos",
                mensagem=(
                    "O Excel foi criado normalmente. Confira também "
                    "os seguintes avisos:\n\n- "
                    + "\n- ".join(resultado.avisos)
                ),
                tipo="aviso",
            )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _abrir_ultimo_relatorio(self):
        if self.ultimo_relatorio is None:
            return
        self._abrir_caminho(self.ultimo_relatorio)

    def _abrir_caminho(self, caminho: Path):
        caminho = Path(caminho)
        if not caminho.exists():
            mostrar_dialogo_arbohub(
                master=self,
                titulo="Caminho indisponível",
                mensagem=f"O caminho não foi encontrado:\n\n{caminho}",
                tipo="aviso",
            )
            return

        try:
            if sys.platform == "win32":
                os.startfile(caminho)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(caminho)])
            else:
                subprocess.Popen(["xdg-open", str(caminho)])
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self,
                titulo="Não foi possível abrir",
                mensagem=(
                    f"Abra o caminho manualmente:\n\n{caminho}"
                    f"\n\nDetalhe: {erro}"
                ),
                tipo="erro",
            )

    def _ao_redimensionar(self, event=None):
        if event is not None and event.widget is not self:
            return
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
        if not self.winfo_exists():
            return
        largura = self.winfo_width()
        vertical = largura < self.LIMITE_LAYOUT_VERTICAL
        if vertical == self._layout_vertical:
            return
        self._layout_vertical = vertical

        self.painel_formulario.grid_forget()
        self.coluna_lateral.grid_forget()

        if vertical:
            self.workspace.grid_columnconfigure(0, weight=1)
            self.workspace.grid_columnconfigure(1, weight=0)
            self.painel_formulario.grid(
                row=0,
                column=0,
                sticky="nsew",
            )
            self.coluna_lateral.grid(
                row=1,
                column=0,
                sticky="ew",
                pady=(14, 0),
            )
        else:
            self.workspace.grid_columnconfigure(0, weight=3)
            self.workspace.grid_columnconfigure(1, weight=1)
            self.painel_formulario.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=(0, 7),
            )
            self.coluna_lateral.grid(
                row=0,
                column=1,
                sticky="new",
                padx=(7, 0),
            )

    def _ao_destruir(self, event):
        if event.widget is not self:
            return
        self._pagina_destruida = True
        if self._polling_id is not None:
            try:
                self.after_cancel(self._polling_id)
            except Exception:
                pass
            self._polling_id = None
        if self._redimensionamento_id is not None:
            try:
                self.after_cancel(self._redimensionamento_id)
            except Exception:
                pass
            self._redimensionamento_id = None
