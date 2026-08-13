from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app.core.versao import ROTULO_VERSAO_ARBOHUB
from app.gui.themes.colors import Colors


class Sidebar(ctk.CTkFrame):

    # Controla o tamanho visível do ícone.
    TAMANHO_ICONE = 58

    # Controla o tamanho do cartão atrás do ícone.
    TAMANHO_CONTAINER_ICONE = 64

    def __init__(
        self,
        master,
        comando_inicio,
        comando_sinan,
        comando_gal,
        comando_historico,
        comando_configuracoes
    ):
        super().__init__(
            master,
            width=230,
            corner_radius=0,
            fg_color=Colors.SIDEBAR
        )

        self.pack_propagate(False)

        self.comando_inicio = comando_inicio
        self.comando_sinan = comando_sinan
        self.comando_gal = comando_gal
        self.comando_historico = comando_historico
        self.comando_configuracoes = (
            comando_configuracoes
        )

        self.botao_ativo = None
        self.imagem_logo = None

        self.criar_cabecalho()
        self.criar_menu()
        self.criar_rodape()

    def criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.pack(
            fill="x",
            padx=18,
            pady=(24, 20)
        )

        marca = ctk.CTkFrame(
            cabecalho,
            fg_color="transparent"
        )
        marca.pack(
            fill="x",
            anchor="w"
        )

        container_icone = ctk.CTkFrame(
            marca,
            width=self.TAMANHO_CONTAINER_ICONE,
            height=self.TAMANHO_CONTAINER_ICONE,
            corner_radius=0,
            fg_color="transparent",
            border_width=0
        )

        container_icone.pack(side="left")
        container_icone.pack_propagate(False)

        pasta_assets = (
            Path(__file__).resolve().parent.parent
            / "assets"
        )

        imagem_clara = self._preparar_logo(
            pasta_assets
            / "arbohub_icon_light.png"
        )
        imagem_escura = self._preparar_logo(
            pasta_assets
            / "arbohub_icon_dark.png"
        )

        self.imagem_logo = ctk.CTkImage(
            light_image=imagem_clara,
            dark_image=imagem_escura,
            size=(
                self.TAMANHO_ICONE,
                self.TAMANHO_ICONE
            )
        )

        icone = ctk.CTkLabel(
            container_icone,
            text="",
            image=self.imagem_logo,
            fg_color="transparent",
            width=self.TAMANHO_CONTAINER_ICONE,
            height=self.TAMANHO_CONTAINER_ICONE
        )
        icone.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        nome = ctk.CTkLabel(
            marca,
            text="ArboHub",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=26,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        nome.pack(
            side="left",
            padx=(10, 0)
        )

        subtitulo = ctk.CTkLabel(
            cabecalho,
            text="Software para vigilância em saúde",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        subtitulo.pack(
            fill="x",
            anchor="w",
            pady=(8, 0)
        )

        divisor = ctk.CTkFrame(
            cabecalho,
            height=1,
            fg_color=Colors.DIVIDER
        )
        divisor.pack(
            fill="x",
            pady=(20, 0)
        )

    def _preparar_logo(
        self,
        caminho: Path
    ) -> Image.Image:
        """
        Recorta margens transparentes e mantém a proporção do ícone.
        """

        imagem_original = Image.open(
            caminho
        ).convert("RGBA")

        caixa_conteudo = imagem_original.getchannel(
            "A"
        ).getbbox()

        if caixa_conteudo is not None:
            imagem_original = imagem_original.crop(
                caixa_conteudo
            )

        largura, altura = imagem_original.size
        tamanho_quadrado = max(
            largura,
            altura
        )

        imagem_quadrada = Image.new(
            mode="RGBA",
            size=(
                tamanho_quadrado,
                tamanho_quadrado
            ),
            color=(0, 0, 0, 0)
        )

        imagem_quadrada.paste(
            imagem_original,
            (
                (tamanho_quadrado - largura) // 2,
                (tamanho_quadrado - altura) // 2
            ),
            imagem_original
        )

        return imagem_quadrada

    def criar_menu(self):
        self.botao_inicio = self.criar_botao_menu(
            texto="Início",
            comando=self.comando_inicio
        )

        self.botao_sinan = self.criar_botao_menu(
            texto="SINAN",
            comando=self.comando_sinan
        )

        self.botao_gal = self.criar_botao_menu(
            texto="GAL",
            comando=self.comando_gal
        )

    def criar_botao_menu(
        self,
        texto,
        comando
    ):
        botao = ctk.CTkButton(
            self,
            text=texto,
            command=comando,
            height=46,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold"
            ),
            anchor="w"
        )

        botao.pack(
            fill="x",
            padx=14,
            pady=4
        )

        return botao

    def selecionar_botao(
        self,
        botao
    ):
        if self.botao_ativo is not None:
            self.botao_ativo.configure(
                fg_color="transparent",
                text_color=Colors.TEXT_SECONDARY
            )

        botao.configure(
            fg_color=Colors.SURFACE_SELECTED,
            text_color=Colors.PRIMARY
        )

        self.botao_ativo = botao

    def selecionar_inicio(self):
        self.selecionar_botao(
            self.botao_inicio
        )

    def selecionar_sinan(self):
        self.selecionar_botao(
            self.botao_sinan
        )

    def selecionar_gal(self):
        self.selecionar_botao(
            self.botao_gal
        )

    def selecionar_historico(self):
        self.selecionar_botao(
            self.botao_historico
        )

    def selecionar_configuracoes(self):
        self.selecionar_botao(
            self.botao_configuracoes
        )

    def criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        rodape.pack(
            side="bottom",
            fill="x",
            padx=14,
            pady=20
        )

        divisor = ctk.CTkFrame(
            rodape,
            height=1,
            fg_color=Colors.DIVIDER
        )
        divisor.pack(
            fill="x",
            padx=6,
            pady=(0, 10)
        )

        self.botao_historico = ctk.CTkButton(
            rodape,
            text="🕘  Histórico",
            command=self.comando_historico,
            height=38,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            anchor="w"
        )
        self.botao_historico.pack(
            fill="x",
            pady=(0, 4)
        )

        self.botao_configuracoes = ctk.CTkButton(
            rodape,
            text="⚙  Configurações",
            command=self.comando_configuracoes,
            height=38,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            anchor="w"
        )
        self.botao_configuracoes.pack(
            fill="x",
            pady=(0, 12)
        )

        status = ctk.CTkLabel(
            rodape,
            text="● Sistema disponível",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.SUCCESS,
            anchor="w"
        )
        status.pack(
            fill="x",
            padx=6
        )

        versao = ctk.CTkLabel(
            rodape,
            text=ROTULO_VERSAO_ARBOHUB,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        versao.pack(
            fill="x",
            padx=6,
            pady=(4, 0)
        )
