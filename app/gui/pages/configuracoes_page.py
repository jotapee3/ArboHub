from __future__ import annotations

from pathlib import Path

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
    Preferências gerais do ArboHub.

    Esta primeira versão não armazena credenciais e não altera os
    caminhos ou o comportamento das automações do SINAN.
    """

    PAGINAS = {
        "Início": "inicio",
        "SINAN": "sinan",
        "GAL": "gal"
    }

    PAGINAS_INVERSAS = {
        valor: chave
        for chave, valor in PAGINAS.items()
    }

    INTERVALOS = {
        "30 segundos": 30,
        "60 segundos": 60,
        "2 minutos": 120,
        "5 minutos": 300
    }

    INTERVALOS_INVERSOS = {
        valor: chave
        for chave, valor in INTERVALOS.items()
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
            self.configuracoes_service.carregar()
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self._criar_variaveis()
        self._criar_cabecalho()
        self._criar_secao_geral()
        self._criar_secao_dashboard()
        self._criar_secao_sobre()
        self._criar_rodape()

    def _criar_variaveis(self):
        geral = self.configuracoes[
            "geral"
        ]
        dashboard = self.configuracoes[
            "dashboard"
        ]

        self.pagina_inicial_var = ctk.StringVar(
            value=self.PAGINAS_INVERSAS.get(
                geral["pagina_inicial"],
                "Início"
            )
        )
        self.abrir_maximizado_var = ctk.BooleanVar(
            value=geral[
                "abrir_maximizado"
            ]
        )
        self.dashboard_automatico_var = ctk.BooleanVar(
            value=dashboard[
                "atualizacao_automatica"
            ]
        )
        self.intervalo_dashboard_var = ctk.StringVar(
            value=self.INTERVALOS_INVERSOS.get(
                dashboard[
                    "intervalo_segundos"
                ],
                "60 segundos"
            )
        )

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
                "Personalize preferências gerais sem alterar "
                "as rotinas operacionais."
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

        ctk.CTkButton(
            cabecalho,
            text="Salvar alterações",
            command=self.salvar_configuracoes,
            width=155,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).grid(
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
                "Defina como o ArboHub deve abrir nesta conta "
                "do Windows."
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
                "Tela exibida ao abrir o aplicativo."
            ),
            variavel=self.pagina_inicial_var,
            valores=list(
                self.PAGINAS.keys()
            )
        )

        self._criar_opcao_switch(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Abrir maximizado",
            descricao=(
                "Usa toda a área disponível da tela."
            ),
            variavel=self.abrir_maximizado_var
        )

    def _criar_secao_dashboard(self):
        painel = self._criar_painel(
            linha=2,
            titulo="Dashboard",
            descricao=(
                "Controle a atualização dos indicadores da aba Início."
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
            uniform="config_dashboard"
        )

        self._criar_opcao_switch(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Atualização automática",
            descricao=(
                "Mantém os indicadores atualizados sem ação manual."
            ),
            variavel=self.dashboard_automatico_var
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Intervalo de atualização",
            descricao=(
                "Tempo entre cada atualização automática."
            ),
            variavel=self.intervalo_dashboard_var,
            valores=list(
                self.INTERVALOS.keys()
            )
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
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.INFO
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "O botão Atualizar da aba Início continuará funcionando "
                "mesmo quando a atualização automática estiver desativada."
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

    def _criar_secao_sobre(self):
        painel = self._criar_painel(
            linha=3,
            titulo="Sobre",
            descricao=(
                "Informações desta instalação do ArboHub."
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

        raiz_projeto = Path(
            __file__
        ).resolve().parents[3]

        informacoes = (
            (
                "Aplicativo",
                "ArboHub v0.5"
            ),
            (
                "Finalidade",
                (
                    "Plataforma de apoio à vigilância em "
                    "antropozoonoses"
                )
            ),
            (
                "Configurações locais",
                str(
                    self.configuracoes_service
                    .caminho_arquivo
                )
            ),
            (
                "Banco operacional",
                str(
                    raiz_projeto
                    / "data"
                    / "arbohub.db"
                )
            )
        )

        for linha, (rotulo, valor) in enumerate(
            informacoes
        ):
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
                wraplength=690
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
            row=4,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 30)
        )
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkButton(
            rodape,
            text="Restaurar padrões",
            command=self.restaurar_padroes,
            width=155,
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
            hover_color=Colors.PRIMARY_HOVER,
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
            wraplength=345
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14
        )

        return card

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
            master,
            linha,
            coluna,
            titulo,
            descricao
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
            master,
            linha,
            coluna,
            titulo,
            descricao
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

    def salvar_configuracoes(self):
        configuracoes = {
            "versao": 1,
            "geral": {
                "pagina_inicial": self.PAGINAS[
                    self.pagina_inicial_var.get()
                ],
                "abrir_maximizado": (
                    self.abrir_maximizado_var.get()
                )
            },
            "dashboard": {
                "atualizacao_automatica": (
                    self.dashboard_automatico_var.get()
                ),
                "intervalo_segundos": self.INTERVALOS[
                    self.intervalo_dashboard_var.get()
                ]
            }
        }

        self.configuracoes = (
            self.configuracoes_service.salvar(
                configuracoes
            )
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Configurações salvas",
            mensagem=(
                "As preferências foram salvas para esta conta do "
                "Windows.\n\n"
                "A página inicial será aplicada na próxima abertura. "
                "O estado da janela e o intervalo do dashboard já "
                "podem ser aplicados nesta execução."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def restaurar_padroes(self):
        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Restaurar configurações?",
            mensagem=(
                "As preferências gerais desta conta do Windows "
                "voltarão aos valores padrão.\n\n"
                "Nenhum banco, relatório, ZIP ou DBF será alterado."
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
        dashboard = self.configuracoes[
            "dashboard"
        ]

        self.pagina_inicial_var.set(
            self.PAGINAS_INVERSAS[
                geral["pagina_inicial"]
            ]
        )
        self.abrir_maximizado_var.set(
            geral["abrir_maximizado"]
        )
        self.dashboard_automatico_var.set(
            dashboard[
                "atualizacao_automatica"
            ]
        )
        self.intervalo_dashboard_var.set(
            self.INTERVALOS_INVERSOS[
                dashboard[
                    "intervalo_segundos"
                ]
            ]
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
