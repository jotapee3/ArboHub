import customtkinter as ctk

from app.gui.themes.colors import Colors


class InicioPage(ctk.CTkFrame):

    def __init__(
        self,
        master,
        comando_sinan,
        comando_gal
    ):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.comando_sinan = comando_sinan
        self.comando_gal = comando_gal

        self.grid_columnconfigure(0, weight=1)

        # Os elementos superiores mantêm o tamanho necessário.
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)

        # O espaço vazio restante fica abaixo do painel.
        self.grid_rowconfigure(3, weight=1)

        self.criar_cabecalho()
        self.criar_cards()
        self.criar_atividade_recente()

    def criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(34, 24)
        )

        titulo = ctk.CTkLabel(
            cabecalho,
            text="Início",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.pack(fill="x")

        descricao = ctk.CTkLabel(
            cabecalho,
            text="Visão geral das operações do ArboHub.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        descricao.pack(
            fill="x",
            pady=(5, 0)
        )

    def criar_cards(self):
        container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        container.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40
        )

        container.grid_columnconfigure((0, 1), weight=1)

        self.criar_card_sistema(
            master=container,
            coluna=0,
            nome="SINAN",
            descricao="Banco de dados e automações do SINAN.",
            comando=self.comando_sinan
        )

        self.criar_card_sistema(
            master=container,
            coluna=1,
            nome="GAL",
            descricao="Banco de dados e automações do GAL.",
            comando=self.comando_gal
        )

    def criar_card_sistema(
        self,
        master,
        coluna,
        nome,
        descricao,
        comando
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=0,
            column=coluna,
            sticky="nsew",
            padx=(0, 8) if coluna == 0 else (8, 0)
        )

        nome_sistema = ctk.CTkLabel(
            card,
            text=nome,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=20,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        nome_sistema.pack(
            fill="x",
            padx=22,
            pady=(20, 5)
        )

        texto_descricao = ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        texto_descricao.pack(
            fill="x",
            padx=22
        )

        status = ctk.CTkLabel(
            card,
            text="Banco ainda não baixado",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        status.pack(
            fill="x",
            padx=22,
            pady=(18, 12)
        )

        botao = ctk.CTkButton(
            card,
            text=f"Abrir {nome}",
            command=comando,
            width=174,
            height=38,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        botao.pack(
            anchor="w",
            padx=22,
            pady=(0, 22)
        )

    def criar_atividade_recente(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(24, 20)
        )

        titulo = ctk.CTkLabel(
            painel,
            text="Atividade recente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.pack(
            fill="x",
            padx=22,
            pady=(18, 6)
        )

        mensagem = ctk.CTkLabel(
            painel,
            text="Nenhuma operação foi realizada até o momento.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        mensagem.pack(
            fill="x",
            padx=22,
            pady=(0, 18)
        )