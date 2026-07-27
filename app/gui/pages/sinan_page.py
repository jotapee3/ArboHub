import customtkinter as ctk


class SinanPage(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(master)

        self.criar_componentes()

    def criar_componentes(self):

        self.titulo = ctk.CTkLabel(
            self,
            text="SINAN",
            font=("Segoe UI", 28, "bold")
        )

        self.titulo.pack(
            anchor="nw",
            padx=30,
            pady=30
        )