import customtkinter as ctk


class Sidebar(ctk.CTkFrame):

    def __init__(self, master, comando_dashboard, comando_sinan):
        super().__init__(master)

        self.comando_dashboard = comando_dashboard
        self.comando_sinan = comando_sinan

        self.configure(
            width=220,
            corner_radius=0
        )

        self.pack_propagate(False)

        self.pack(
            side="left",
            fill="y"
        )

        self.criar_componentes()

    def criar_componentes(self):
        self.titulo = ctk.CTkLabel(
            self,
            text="ArboHub",
            font=("Segoe UI", 24, "bold")
        )

        self.titulo.pack(
            pady=(30, 5)
        )

        self.subtitulo = ctk.CTkLabel(
            self,
            text="Sistema de Apoio",
            font=("Segoe UI", 13)
        )

        self.subtitulo.pack(
            pady=(0, 30)
        )

        self.botao_dashboard = ctk.CTkButton(
            self,
            text="Dashboard",
            command=self.comando_dashboard
        )

        self.botao_dashboard.pack(
            fill="x",
            padx=15,
            pady=5
        )

        self.botao_sinan = ctk.CTkButton(
            self,
            text="SINAN",
            command=self.comando_sinan
        )

        self.botao_sinan.pack(
            fill="x",
            padx=15,
            pady=5
        )