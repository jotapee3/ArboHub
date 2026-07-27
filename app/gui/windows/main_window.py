import customtkinter as ctk

from app.gui.components.sidebar import Sidebar
from app.gui.components.content_area import ContentArea
from app.gui.pages.dashboard_page import DashboardPage
from app.gui.pages.sinan_page import SinanPage


class MainWindow(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("ArboHub")
        self.geometry("1000x600")
        self.minsize(800, 500)

        self.centralizar_janela()

        self.content_area = ContentArea(self)

        self.sidebar = Sidebar(
            self,
            comando_dashboard=lambda: self.content_area.mostrar_pagina(
                DashboardPage
            ),
            comando_sinan=lambda: self.content_area.mostrar_pagina(
                SinanPage
            )
        )

        self.mainloop()

    def centralizar_janela(self):
        self.update_idletasks()

        largura = 1000
        altura = 600

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        posicao_x = (largura_tela - largura) // 2
        posicao_y = (altura_tela - altura) // 2

        self.geometry(
            f"{largura}x{altura}+{posicao_x}+{posicao_y}"
        )