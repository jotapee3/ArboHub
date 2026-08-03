from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.gui.components.arbohub_dialog import (
    mostrar_dialogo_arbohub,
    solicitar_confirmacao_arbohub
)
from app.gui.themes.colors import Colors
from app.services.configuracoes_service import (
    ConfiguracoesService
)


class ConfiguracoesPage(ctk.CTkScrollableFrame):
    """
    Preferências locais e não sensíveis do ArboHub.
    """

    PAGINAS_EXIBICAO = {
        "Início": "inicio",
        "SINAN": "sinan",
        "GAL": "gal"
    }

    PAGINAS_INVERTIDAS = {
        valor: chave
        for chave, valor
        in PAGINAS_EXIBICAO.items()
    }

    INTERVALOS_EXIBICAO = {
        "30 segundos": 30,
        "60 segundos": 60,
        "2 minutos": 120,
        "5 minutos": 300
    }

    INTERVALOS_INVERTIDOS = {
        valor: chave
        for chave, valor
        in INTERVALOS_EXIBICAO.items()
    }

    ESCALAS_EXIBICAO = {
        "90%": 90,
        "100%": 100,
        "110%": 110,
        "125%": 125
    }

    ESCALAS_INVERTIDAS = {
        valor: chave
        for chave, valor
        in ESCALAS_EXIBICAO.items()
    }

    def __init__(
        self,
        master,
        ao_salvar=None
    ):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.ao_salvar = ao_salvar
        self.configuracoes_service = (
            ConfiguracoesService()
        )
        self.configuracoes = (
            self.configuracoes_service.obter()
        )

        self.campos_caminhos = {}

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self._criar_variaveis()
        self._criar_cabecalho()
        self._criar_secao_geral()
        self._criar_secao_rotinas()
        self._criar_secao_caminhos()
        self._criar_secao_sobre()
        self._criar_rodape()

    def _criar_variaveis(self):
        geral = self.configuracoes[
            "geral"
        ]
        rotinas = self.configuracoes[
            "rotinas"
        ]

        self.pagina_inicial_var = ctk.StringVar(
            value=self.PAGINAS_INVERTIDAS.get(
                geral["pagina_inicial"],
                "Início"
            )
        )
        self.abrir_maximizado_var = ctk.BooleanVar(
            value=geral[
                "abrir_maximizado"
            ]
        )
        self.dashboard_automatico_var = (
            ctk.BooleanVar(
                value=geral[
                    "dashboard_atualizacao_automatica"
                ]
            )
        )
        self.intervalo_dashboard_var = ctk.StringVar(
            value=self.INTERVALOS_INVERTIDOS.get(
                geral[
                    "dashboard_intervalo_segundos"
                ],
                "60 segundos"
            )
        )
        self.escala_var = ctk.StringVar(
            value=self.ESCALAS_INVERTIDAS.get(
                geral["escala_interface"],
                "100%"
            )
        )
        self.modo_teste_var = ctk.BooleanVar(
            value=rotinas[
                "modo_teste"
            ]
        )

    # ------------------------------------------------------------------
    # Estrutura
    # ------------------------------------------------------------------

    def _criar_cabecalho(self):
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
        cabecalho.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            cabecalho,
            text="Configurações",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
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
                "Personalize o comportamento do ArboHub "
                "nesta conta do Windows."
            ),
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

        self.botao_salvar_topo = ctk.CTkButton(
            cabecalho,
            text="Salvar alterações",
            command=self.salvar_configuracoes,
            width=150,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.botao_salvar_topo.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e"
        )

    def _criar_secao_geral(self):
        painel = self._criar_painel(
            linha=1,
            titulo="Geral",
            descricao=(
                "Defina como o aplicativo deve abrir e "
                "atualizar o painel principal."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_geral"
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Página inicial",
            descricao=(
                "Tela exibida quando o ArboHub for aberto."
            ),
            variavel=self.pagina_inicial_var,
            valores=list(
                self.PAGINAS_EXIBICAO.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Escala da interface",
            descricao=(
                "Ajusta o tamanho dos componentes do aplicativo."
            ),
            variavel=self.escala_var,
            valores=list(
                self.ESCALAS_EXIBICAO.keys()
            )
        )

        self._criar_opcao_switch(
            master=grade,
            linha=1,
            coluna=0,
            titulo="Abrir maximizado",
            descricao=(
                "Usa toda a área disponível da tela ao iniciar."
            ),
            variavel=self.abrir_maximizado_var
        )

        self._criar_opcao_switch(
            master=grade,
            linha=1,
            coluna=1,
            titulo="Atualização automática",
            descricao=(
                "Mantém os indicadores da aba Início atualizados."
            ),
            variavel=self.dashboard_automatico_var
        )

        self._criar_opcao_menu(
            master=grade,
            linha=2,
            coluna=0,
            titulo="Intervalo do dashboard",
            descricao=(
                "Frequência da atualização automática."
            ),
            variavel=self.intervalo_dashboard_var,
            valores=list(
                self.INTERVALOS_EXIBICAO.keys()
            )
        )

        self._criar_opcao_informativa(
            master=grade,
            linha=2,
            coluna=1,
            titulo="Aparência",
            descricao=(
                "Tema escuro ativo — identidade visual "
                "atual do ArboHub."
            ),
            valor="Escuro"
        )

    def _criar_secao_rotinas(self):
        painel = self._criar_painel(
            linha=2,
            titulo="Rotinas e testes",
            descricao=(
                "Controle recursos de desenvolvimento sem "
                "alterar os dados operacionais."
            )
        )

        caixa = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        caixa.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        caixa.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            caixa,
            text="Modo de teste",
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
            sticky="ew",
            padx=(16, 12),
            pady=(15, 3)
        )

        ctk.CTkLabel(
            caixa,
            text=(
                "Registra que esta instalação ainda utiliza "
                "ferramentas e caminhos de validação. O botão "
                "Resetar teste da aba Bases continua sendo uma "
                "ação manual e confirmada."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=690
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(16, 12),
            pady=(0, 15)
        )

        ctk.CTkSwitch(
            caixa,
            text="Ativado",
            variable=self.modo_teste_var,
            onvalue=True,
            offvalue=False,
            progress_color=Colors.PRIMARY,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e",
            padx=16,
            pady=15
        )

        aviso = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        aviso.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        aviso.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkLabel(
            aviso,
            text="i",
            width=30,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "Credenciais e login automático não fazem parte "
                "desta versão. Esta página armazena apenas "
                "preferências não sensíveis."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=720
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=12
        )

    def _criar_secao_caminhos(self):
        painel = self._criar_painel(
            linha=3,
            titulo="Pastas e arquivos",
            descricao=(
                "Defina os destinos usados pela rotina de Bases."
            )
        )

        caminhos = self.configuracoes[
            "caminhos"
        ]

        itens = (
            (
                "historico_sinan",
                "Histórico do SINAN",
                (
                    "ZIPs organizados por ano, agravo e mês."
                )
            ),
            (
                "teste_ab1",
                "Pasta Teste AB1",
                (
                    "Destino temporário do banco de Dengue."
                )
            ),
            (
                "teste_ab2",
                "Pasta Teste AB2",
                (
                    "Destino temporário do banco de Chikungunya."
                )
            ),
            (
                "bancos_atuais",
                "Bancos_Atuais",
                (
                    "Versões vigentes utilizadas pelo setor."
                )
            )
        )

        container = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        container.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        container.grid_columnconfigure(
            0,
            weight=1
        )

        for linha, (
            chave,
            titulo,
            descricao
        ) in enumerate(itens):
            self._criar_linha_caminho(
                master=container,
                linha=linha,
                chave=chave,
                titulo=titulo,
                descricao=descricao,
                valor=caminhos[chave]
            )

    def _criar_secao_sobre(self):
        painel = self._criar_painel(
            linha=4,
            titulo="Sobre",
            descricao=(
                "Informações técnicas desta instalação."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        grade.grid_columnconfigure(
            1,
            weight=1
        )

        informacoes = (
            (
                "Aplicativo",
                "ArboHub — versão de desenvolvimento"
            ),
            (
                "Finalidade",
                (
                    "Apoio às rotinas de vigilância em "
                    "antropozoonoses"
                )
            ),
            (
                "Sistema",
                (
                    f"{platform.system()} "
                    f"{platform.release()}"
                )
            ),
            (
                "Python",
                platform.python_version()
            ),
            (
                "Configurações",
                str(
                    self.configuracoes_service
                    .caminho_arquivo
                )
            )
        )

        for linha, (
            rotulo,
            valor
        ) in enumerate(informacoes):
            ctk.CTkLabel(
                grade,
                text=rotulo,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11,
                    weight="bold"
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).grid(
                row=linha,
                column=0,
                sticky="w",
                padx=(16, 18),
                pady=(
                    (14, 7)
                    if linha == 0
                    else (
                        (7, 14)
                        if linha == len(informacoes) - 1
                        else 7
                    )
                )
            )

            ctk.CTkLabel(
                grade,
                text=valor,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=620
            ).grid(
                row=linha,
                column=1,
                sticky="ew",
                padx=(0, 16),
                pady=(
                    (14, 7)
                    if linha == 0
                    else (
                        (7, 14)
                        if linha == len(informacoes) - 1
                        else 7
                    )
                )
            )

    def _criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        rodape.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 30)
        )
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkButton(
            rodape,
            text="Restaurar padrões",
            command=self.restaurar_padroes,
            width=150,
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
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkButton(
            rodape,
            text="Salvar alterações",
            command=self.salvar_configuracoes,
            width=170,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    # ------------------------------------------------------------------
    # Componentes
    # ------------------------------------------------------------------

    def _criar_painel(
        self,
        linha: int,
        titulo: str,
        descricao: str
    ):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 16)
        )
        painel.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            painel,
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
            pady=(18, 3)
        )

        ctk.CTkLabel(
            painel,
            text=descricao,
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
            padx=20,
            pady=(0, 12)
        )

        return painel

    def _criar_opcao_menu(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        variavel,
        valores: list[str]
    ):
        card = self._criar_card_opcao(
            master=master,
            linha=linha,
            coluna=coluna,
            titulo=titulo,
            descricao=descricao
        )

        ctk.CTkOptionMenu(
            card,
            variable=variavel,
            values=valores,
            height=34,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

    def _criar_opcao_switch(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        variavel
    ):
        card = self._criar_card_opcao(
            master=master,
            linha=linha,
            coluna=coluna,
            titulo=titulo,
            descricao=descricao
        )

        ctk.CTkSwitch(
            card,
            text="Ativado",
            variable=variavel,
            onvalue=True,
            offvalue=False,
            progress_color=Colors.PRIMARY,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=14,
            pady=(10, 16)
        )

    def _criar_opcao_informativa(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        valor: str
    ):
        card = self._criar_card_opcao(
            master=master,
            linha=linha,
            coluna=coluna,
            titulo=titulo,
            descricao=descricao
        )

        ctk.CTkLabel(
            card,
            text=valor,
            height=34,
            fg_color=Colors.BUTTON,
            corner_radius=6,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

    def _criar_card_opcao(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=coluna,
            sticky="nsew",
            padx=(
                (0, 6)
                if coluna == 0
                else (6, 0)
            ),
            pady=6
        )
        card.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            card,
            text=titulo,
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
            sticky="ew",
            padx=14,
            pady=(13, 3)
        )

        ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=340
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14
        )

        return card

    def _criar_linha_caminho(
        self,
        master,
        linha: int,
        chave: str,
        titulo: str,
        descricao: str,
        valor: str
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(
                (0, 8)
                if linha < 3
                else 0
            )
        )
        card.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            card,
            text=titulo,
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
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(13, 2)
        )

        ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(0, 9)
        )

        campo = ctk.CTkEntry(
            card,
            height=35,
            corner_radius=6,
            border_width=1,
            border_color=Colors.BORDER,
            fg_color=Colors.SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text="Selecione uma pasta",
            font=ctk.CTkFont(
                family="Consolas",
                size=10
            )
        )
        campo.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(14, 6),
            pady=(0, 14)
        )
        campo.insert(
            0,
            valor
        )

        self.campos_caminhos[chave] = campo

        ctk.CTkButton(
            card,
            text="Selecionar",
            command=lambda c=chave:
                self.selecionar_pasta(c),
            width=90,
            height=35,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            )
        ).grid(
            row=2,
            column=1,
            padx=6,
            pady=(0, 14)
        )

        ctk.CTkButton(
            card,
            text="Testar",
            command=lambda c=chave:
                self.testar_caminho(c),
            width=72,
            height=35,
            corner_radius=6,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            )
        ).grid(
            row=2,
            column=2,
            padx=(6, 14),
            pady=(0, 14)
        )

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------

    def selecionar_pasta(
        self,
        chave: str
    ):
        campo = self.campos_caminhos[
            chave
        ]
        atual = campo.get().strip()

        pasta = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Selecione a pasta",
            initialdir=(
                atual
                if atual
                and Path(atual).exists()
                else str(Path.home())
            )
        )

        if not pasta:
            return

        campo.delete(
            0,
            "end"
        )
        campo.insert(
            0,
            pasta
        )

    def testar_caminho(
        self,
        chave: str
    ):
        caminho_texto = (
            self.campos_caminhos[
                chave
            ].get().strip()
        )
        caminho = Path(
            caminho_texto
        ).expanduser()

        if not caminho.exists():
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Pasta não encontrada",
                mensagem=(
                    "O caminho informado não existe ou não está "
                    "disponível neste momento:\n\n"
                    f"{caminho}"
                ),
                tipo="aviso",
                texto_botao="Entendi"
            )
            return

        if not caminho.is_dir():
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Caminho inválido",
                mensagem=(
                    "O caminho informado existe, mas não é uma "
                    "pasta:\n\n"
                    f"{caminho}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        try:
            if os.name == "nt":
                os.startfile(
                    str(caminho)
                )
        except OSError:
            pass

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Pasta validada",
            mensagem=(
                "A pasta foi localizada com sucesso:\n\n"
                f"{caminho}"
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def salvar_configuracoes(self):
        caminhos = {
            chave: campo.get().strip()
            for chave, campo
            in self.campos_caminhos.items()
        }

        vazios = [
            chave
            for chave, valor
            in caminhos.items()
            if not valor
        ]

        if vazios:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Preencha todos os caminhos",
                mensagem=(
                    "Nenhum caminho pode ficar vazio antes de "
                    "salvar as configurações."
                ),
                tipo="aviso",
                texto_botao="Entendi"
            )
            return

        configuracoes = {
            "versao_configuracao": 1,
            "geral": {
                "pagina_inicial":
                    self.PAGINAS_EXIBICAO[
                        self.pagina_inicial_var.get()
                    ],
                "abrir_maximizado":
                    self.abrir_maximizado_var.get(),
                "dashboard_atualizacao_automatica":
                    self.dashboard_automatico_var.get(),
                "dashboard_intervalo_segundos":
                    self.INTERVALOS_EXIBICAO[
                        self.intervalo_dashboard_var.get()
                    ],
                "escala_interface":
                    self.ESCALAS_EXIBICAO[
                        self.escala_var.get()
                    ]
            },
            "rotinas": {
                "modo_teste":
                    self.modo_teste_var.get()
            },
            "caminhos": caminhos
        }

        self.configuracoes = (
            self.configuracoes_service.salvar(
                configuracoes
            )
        )

        ctk.set_widget_scaling(
            self.configuracoes[
                "geral"
            ]["escala_interface"] / 100
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Configurações salvas",
            mensagem=(
                "As preferências foram salvas para esta conta "
                "do Windows.\n\n"
                "A página inicial será aplicada na próxima "
                "abertura. A escala e o estado da janela podem "
                "ser aplicados imediatamente."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def restaurar_padroes(self):
        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Restaurar configurações?",
            mensagem=(
                "As preferências desta conta do Windows voltarão "
                "aos valores padrão.\n\n"
                "Nenhum banco, relatório, ZIP ou DBF será apagado."
            ),
            texto_confirmar="Restaurar padrões",
            texto_cancelar="Cancelar",
            tipo="aviso"
        )

        if not confirmou:
            return

        self.configuracoes = (
            self.configuracoes_service
            .restaurar_padroes()
        )

        geral = self.configuracoes[
            "geral"
        ]

        self.pagina_inicial_var.set(
            self.PAGINAS_INVERTIDAS[
                geral["pagina_inicial"]
            ]
        )
        self.abrir_maximizado_var.set(
            geral["abrir_maximizado"]
        )
        self.dashboard_automatico_var.set(
            geral[
                "dashboard_atualizacao_automatica"
            ]
        )
        self.intervalo_dashboard_var.set(
            self.INTERVALOS_INVERTIDOS[
                geral[
                    "dashboard_intervalo_segundos"
                ]
            ]
        )
        self.escala_var.set(
            self.ESCALAS_INVERTIDAS[
                geral["escala_interface"]
            ]
        )
        self.modo_teste_var.set(
            self.configuracoes[
                "rotinas"
            ]["modo_teste"]
        )

        for chave, campo in (
            self.campos_caminhos.items()
        ):
            campo.delete(
                0,
                "end"
            )
            campo.insert(
                0,
                self.configuracoes[
                    "caminhos"
                ][chave]
            )

        ctk.set_widget_scaling(
            geral["escala_interface"] / 100
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Padrões restaurados",
            mensagem=(
                "As configurações padrão foram restauradas."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )
