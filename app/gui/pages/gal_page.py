import customtkinter as ctk

from app.gui.themes.colors import Colors


class GalPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        titulo = ctk.CTkLabel(
            self,
            text="GAL",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY
        )
        titulo.pack(
            anchor="w",
            padx=36,
            pady=(32, 4)
        )

        descricao = ctk.CTkLabel(
            self,
            text="Automação e gerenciamento dos bancos de dados do GAL.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14
            ),
            text_color=Colors.TEXT_SECONDARY
        )
        descricao.pack(
            anchor="w",
            padx=36
        )