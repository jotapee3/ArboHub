import customtkinter as ctk

from app.gui.themes.colors import Colors


class ContentArea(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.pagina_atual = None

    def limpar_area(self):
        if self.pagina_atual is not None:
            self.pagina_atual.destroy()
            self.pagina_atual = None

    def mostrar_pagina(self, pagina):
        self.limpar_area()

        self.pagina_atual = pagina(self)

        self.pagina_atual.pack(
            fill="both",
            expand=True
        )