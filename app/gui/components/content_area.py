import customtkinter as ctk

from app.gui.pages.dashboard_page import DashboardPage


class ContentArea(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.configure(corner_radius=0)

        self.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.mostrar_pagina(DashboardPage)

    def limpar_area(self):
        for componente in self.winfo_children():
            componente.destroy()

    def mostrar_pagina(self, pagina):
        self.limpar_area()

        self.pagina_atual = pagina(self)

        self.pagina_atual.pack(
            fill="both",
            expand=True
        )