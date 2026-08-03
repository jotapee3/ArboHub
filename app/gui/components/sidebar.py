from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app.gui.themes.colors import Colors


class Sidebar(ctk.CTkFrame):
    """
    Navegação principal do ArboHub.

    Configurações permanece no rodapé, visualmente separada dos
    módulos operacionais.
    """

    LARGURA = 230

    def __init__(
        self,
        master,
        comando_inicio,
        comando_sinan,
        comando_gal,
        comando_configuracoes
    ):
        super().__init__(
            master,
            width=self.LARGURA,
            corner_radius=0,
            fg_color=Colors.SIDEBAR,
            border_width=0
        )

        self.comando_inicio = comando_inicio
        self.comando_sinan = comando_sinan
        self.comando_gal = comando_gal
        self.comando_configuracoes = (
            comando_configuracoes
        )

        self.grid_propagate(
            False
        )
        self.grid_rowconfigure(
            2,
            weight=1
        )
        self.grid_columnconfigure(
            0,
            weight=1
        )

        self.botoes = {}

        self._criar_marca()
        self._criar_menu()
        self._criar_rodape()

    def _criar_marca(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(22, 14)
        )
        cabecalho.grid_columnconfigure(
            0,
            weight=1
        )

        caminho_logo = self._localizar_logo()

        if caminho_logo is not None:
            try:
                imagem = Image.open(
                    caminho_logo
                )
                self.logo_imagem = ctk.CTkImage(
                    light_image=imagem,
                    dark_image=imagem,
                    size=(176, 52)
                )

                ctk.CTkLabel(
                    cabecalho,
                    text="",
                    image=self.logo_imagem
                ).grid(
                    row=0,
                    column=0,
                    sticky="w"
                )
                return
            except Exception:
                pass

        ctk.CTkLabel(
            cabecalho,
            text="ArboHub",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=24,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkLabel(
            cabecalho,
            text="Vigilância integrada",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0)
        )

    def _criar_menu(self):
        ctk.CTkLabel(
            self,
            text="NAVEGAÇÃO",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(5, 8)
        )

        menu = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        menu.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12
        )
        menu.grid_columnconfigure(
            0,
            weight=1
        )

        itens = (
            (
                "inicio",
                "⌂",
                "Início",
                self.comando_inicio
            ),
            (
                "sinan",
                "S",
                "SINAN",
                self.comando_sinan
            ),
            (
                "gal",
                "G",
                "GAL",
                self.comando_gal
            )
        )

        for linha, (
            chave,
            icone,
            texto,
            comando
        ) in enumerate(itens):
            self.botoes[chave] = (
                self._criar_botao_menu(
                    master=menu,
                    linha=linha,
                    icone=icone,
                    texto=texto,
                    comando=comando,
                    compacto=False
                )
            )

    def _criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        rodape.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=12,
            pady=(10, 14)
        )
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkFrame(
            rodape,
            height=1,
            fg_color=Colors.BORDER
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=7,
            pady=(0, 10)
        )

        self.botoes[
            "configuracoes"
        ] = self._criar_botao_menu(
            master=rodape,
            linha=1,
            icone="⚙",
            texto="Configurações",
            comando=self.comando_configuracoes,
            compacto=True
        )

        ctk.CTkLabel(
            rodape,
            text="CEVS • Antropozoonoses",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=10,
            pady=(8, 0)
        )

    def _criar_botao_menu(
        self,
        master,
        linha: int,
        icone: str,
        texto: str,
        comando,
        compacto: bool
    ):
        botao = ctk.CTkButton(
            master,
            text=f"{icone}   {texto}",
            command=comando,
            height=(
                36
                if compacto
                else 42
            ),
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.SIDEBAR,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=(
                    11
                    if compacto
                    else 12
                ),
                weight="bold"
            )
        )
        botao.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(
                2
                if compacto
                else 3
            )
        )

        return botao

    def selecionar(
        self,
        chave: str
    ):
        for nome, botao in self.botoes.items():
            ativo = nome == chave

            botao.configure(
                fg_color=(
                    Colors.BUTTON
                    if ativo
                    else "transparent"
                ),
                border_color=(
                    Colors.BORDER
                    if ativo
                    else Colors.SIDEBAR
                ),
                text_color=(
                    Colors.TEXT_PRIMARY
                    if ativo
                    else Colors.TEXT_SECONDARY
                )
            )

    # Compatibilidade com versões anteriores.
    def selecionar_item(
        self,
        chave: str
    ):
        self.selecionar(
            chave
        )

    def definir_ativo(
        self,
        chave: str
    ):
        self.selecionar(
            chave
        )

    def _localizar_logo(self) -> Path | None:
        raiz = Path(__file__).resolve().parents[3]

        candidatos = (
            raiz
            / "assets"
            / "arbohub_sidebar.png",
            raiz
            / "app"
            / "assets"
            / "arbohub_sidebar.png",
            raiz
            / "assets"
            / "arbohub_original.png"
        )

        for caminho in candidatos:
            if caminho.exists():
                return caminho

        return None
