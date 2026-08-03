from __future__ import annotations

import customtkinter as ctk

from app.gui.themes.colors import Colors


class GalPage(ctk.CTkScrollableFrame):
    """
    Estado visual do módulo GAL enquanto a automação é construída.
    """

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self._criar_cabecalho()
        self._criar_destaque()
        self._criar_etapas_planejadas()
        self._criar_rodape()

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(30, 18)
        )

        ctk.CTkLabel(
            cabecalho,
            text="GAL",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).pack(
            fill="x"
        )

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Integração e acompanhamento das rotinas "
                "laboratoriais."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).pack(
            fill="x",
            pady=(5, 0)
        )

    def _criar_destaque(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40
        )
        painel.grid_columnconfigure(
            1,
            weight=1
        )

        icone = ctk.CTkFrame(
            painel,
            width=66,
            height=66,
            fg_color=Colors.BUTTON,
            corner_radius=14,
            border_width=1,
            border_color=Colors.BORDER
        )
        icone.grid(
            row=0,
            column=0,
            rowspan=4,
            padx=(24, 20),
            pady=26
        )
        icone.grid_propagate(
            False
        )

        ctk.CTkLabel(
            icone,
            text="G",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=27,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            painel,
            text="EM DESENVOLVIMENTO",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 24),
            pady=(25, 2)
        )

        ctk.CTkLabel(
            painel,
            text="Uma nova integração está a caminho",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=21,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 24)
        )

        ctk.CTkLabel(
            painel,
            text=(
                "Estamos preparando uma experiência integrada "
                "para tornar a rotina do GAL mais simples, "
                "segura e eficiente."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=690
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 24),
            pady=(6, 3)
        )

        ctk.CTkLabel(
            painel,
            text=(
                "O módulo será liberado gradualmente após "
                "validação dos fluxos e das regras operacionais."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=690
        ).grid(
            row=3,
            column=1,
            sticky="new",
            padx=(0, 24),
            pady=(0, 25)
        )

    def _criar_etapas_planejadas(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(16, 0)
        )
        painel.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="gal_planejado"
        )

        ctk.CTkLabel(
            painel,
            text="Visão do módulo",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(18, 3)
        )

        ctk.CTkLabel(
            painel,
            text=(
                "Os recursos serão construídos mantendo o mesmo "
                "padrão de segurança e rastreabilidade do SINAN."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(0, 14)
        )

        itens = (
            (
                "Integração",
                (
                    "Acesso organizado às rotinas "
                    "laboratoriais."
                )
            ),
            (
                "Automação",
                (
                    "Redução de etapas repetitivas com "
                    "validação humana."
                )
            ),
            (
                "Rastreabilidade",
                (
                    "Acompanhamento de execução e histórico "
                    "operacional."
                )
            )
        )

        for coluna, (
            titulo,
            descricao
        ) in enumerate(itens):
            card = ctk.CTkFrame(
                painel,
                fg_color=Colors.BACKGROUND,
                corner_radius=8,
                border_width=1,
                border_color=Colors.BORDER
            )
            card.grid(
                row=2,
                column=coluna,
                sticky="nsew",
                padx=(
                    (20, 6)
                    if coluna == 0
                    else (
                        (6, 20)
                        if coluna == 2
                        else 6
                    )
                ),
                pady=(0, 20)
            )

            ctk.CTkLabel(
                card,
                text=titulo,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=13,
                    weight="bold"
                ),
                text_color=Colors.TEXT_PRIMARY,
                anchor="w"
            ).pack(
                fill="x",
                padx=15,
                pady=(14, 4)
            )

            ctk.CTkLabel(
                card,
                text=descricao,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=245
            ).pack(
                fill="x",
                padx=15
            )

            ctk.CTkLabel(
                card,
                text="○ Planejado",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold"
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).pack(
                fill="x",
                padx=15,
                pady=(10, 14)
            )

    def _criar_rodape(self):
        ctk.CTkLabel(
            self,
            text=(
                "ArboHub • Plataforma de apoio à vigilância"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED
        ).grid(
            row=3,
            column=0,
            pady=(22, 30)
        )
