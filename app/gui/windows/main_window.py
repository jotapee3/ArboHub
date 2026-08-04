import customtkinter as ctk

from pathlib import Path
from app.gui.components.sidebar import Sidebar
from app.gui.components.content_area import ContentArea
from app.gui.pages.inicio_page import InicioPage
from app.gui.pages.sinan_page import SinanPage
from app.gui.pages.gal_page import GalPage
from app.gui.pages.configuracoes_page import ConfiguracoesPage
from app.gui.themes.colors import Colors
from app.services.configuracoes_service import ConfiguracoesService


class MainWindow(ctk.CTk):

    def __init__(self):
        self.configuracoes_service = (
            ConfiguracoesService()
        )
        self.configuracoes = (
            self.configuracoes_service.carregar()
        )

        super().__init__()

        self.title("ArboHub")

        caminho_icone = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "arbohub.ico"
        )

        self.iconbitmap(caminho_icone)

        self.geometry("1360x840")
        self.minsize(900, 550)
        self.configure(fg_color=Colors.BACKGROUND)

        self.centralizar_janela()
        self.criar_interface()
        self._abrir_pagina_inicial()

        self.after(
            20,
            self._aplicar_estado_janela
        )

        self.mainloop()

    def criar_interface(self):
        self.content_area = ContentArea(self)

        self.sidebar = Sidebar(
            self,
            comando_inicio=self.abrir_inicio,
            comando_sinan=self.abrir_sinan,
            comando_gal=self.abrir_gal,
            comando_configuracoes=(
                self.abrir_configuracoes
            )
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.content_area.pack(
            side="right",
            fill="both",
            expand=True
        )

    def abrir_inicio(self):
        self.content_area.mostrar_pagina(
            lambda master: InicioPage(
                master,
                comando_sinan=self.abrir_sinan,
                comando_gal=self.abrir_gal
            )
        )

        self.sidebar.selecionar_inicio()

    def abrir_sinan(self):
        self.content_area.mostrar_pagina(SinanPage)
        self.sidebar.selecionar_sinan()

    def abrir_gal(self):
        self.content_area.mostrar_pagina(GalPage)
        self.sidebar.selecionar_gal()

    def abrir_configuracoes(self):
        self.content_area.mostrar_pagina(
            lambda master: ConfiguracoesPage(
                master,
                ao_salvar=self._ao_salvar_configuracoes
            )
        )
        self.sidebar.selecionar_configuracoes()

    def _abrir_pagina_inicial(self):
        pagina = self.configuracoes[
            "geral"
        ]["pagina_inicial"]

        comandos = {
            "inicio": self.abrir_inicio,
            "sinan": self.abrir_sinan,
            "gal": self.abrir_gal
        }

        comandos.get(
            pagina,
            self.abrir_inicio
        )()

    def _ao_salvar_configuracoes(
        self,
        configuracoes
    ):
        self.configuracoes = configuracoes
        self._aplicar_estado_janela()

    def _aplicar_estado_janela(self):
        maximizado = self.configuracoes[
            "geral"
        ]["abrir_maximizado"]

        try:
            if maximizado:
                self.state("zoomed")
            else:
                self.state("normal")
                self.centralizar_janela()
        except Exception:
            self.centralizar_janela()

    def centralizar_janela(self):
        self.update_idletasks()

        largura = 1360
        altura = 840

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        posicao_x = (largura_tela - largura) // 2
        posicao_y = (altura_tela - altura) // 2

        self.geometry(
            f"{largura}x{altura}+{posicao_x}+{posicao_y}"
        )
