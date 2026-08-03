from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

from app.gui.components.content_area import ContentArea
from app.gui.components.sidebar import Sidebar
from app.gui.pages.configuracoes_page import (
    ConfiguracoesPage
)
from app.gui.pages.gal_page import GalPage
from app.gui.pages.inicio_page import InicioPage
from app.gui.pages.sinan_page import SinanPage
from app.gui.themes.colors import Colors
from app.services.configuracoes_service import (
    ConfiguracoesService
)


class MainWindow(ctk.CTk):
    """
    Janela principal e roteamento das páginas do ArboHub.
    """

    def __init__(self):
        self.configuracoes_service = (
            ConfiguracoesService()
        )
        self.configuracoes = (
            self.configuracoes_service.obter()
        )

        ctk.set_appearance_mode(
            "dark"
        )
        ctk.set_widget_scaling(
            self.configuracoes[
                "geral"
            ]["escala_interface"] / 100
        )

        super().__init__()

        self.title("ArboHub")
        self.geometry("1180x720")
        self.minsize(900, 620)
        self.configure(
            fg_color=Colors.BACKGROUND
        )

        self.grid_columnconfigure(
            1,
            weight=1
        )
        self.grid_rowconfigure(
            0,
            weight=1
        )

        self._configurar_icone()

        self.sidebar = Sidebar(
            self,
            comando_inicio=self.abrir_inicio,
            comando_sinan=self.abrir_sinan,
            comando_gal=self.abrir_gal,
            comando_configuracoes=(
                self.abrir_configuracoes
            )
        )
        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsw"
        )

        self.content_area = ContentArea(
            self
        )
        self.content_area.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.after(
            20,
            self._aplicar_estado_janela
        )
        self.after(
            40,
            self._abrir_pagina_inicial
        )

        self.mainloop()

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def abrir_inicio(self):
        self.sidebar.selecionar(
            "inicio"
        )
        self.content_area.mostrar_pagina(
            lambda master: InicioPage(
                master,
                comando_sinan=self.abrir_sinan,
                comando_gal=self.abrir_gal
            )
        )

    def abrir_sinan(self):
        self.sidebar.selecionar(
            "sinan"
        )
        self.content_area.mostrar_pagina(
            lambda master: SinanPage(
                master
            )
        )

    def abrir_gal(self):
        self.sidebar.selecionar(
            "gal"
        )
        self.content_area.mostrar_pagina(
            lambda master: GalPage(
                master
            )
        )

    def abrir_configuracoes(self):
        self.sidebar.selecionar(
            "configuracoes"
        )
        self.content_area.mostrar_pagina(
            lambda master: ConfiguracoesPage(
                master,
                ao_salvar=(
                    self._ao_salvar_configuracoes
                )
            )
        )

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

    # ------------------------------------------------------------------
    # Configurações
    # ------------------------------------------------------------------

    def _ao_salvar_configuracoes(
        self,
        configuracoes: dict
    ):
        self.configuracoes = configuracoes

        escala = (
            configuracoes[
                "geral"
            ]["escala_interface"]
            / 100
        )
        ctk.set_widget_scaling(
            escala
        )

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
                self._centralizar()
        except Exception:
            self._centralizar()

    # ------------------------------------------------------------------
    # Janela
    # ------------------------------------------------------------------

    def _centralizar(self):
        self.update_idletasks()

        largura = max(
            self.winfo_width(),
            1180
        )
        altura = max(
            self.winfo_height(),
            720
        )

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        x = max(
            0,
            int(
                (largura_tela - largura)
                / 2
            )
        )
        y = max(
            0,
            int(
                (altura_tela - altura)
                / 2
            )
        )

        self.geometry(
            f"{largura}x{altura}+{x}+{y}"
        )

    def _configurar_icone(self):
        raiz = Path(__file__).resolve().parents[3]

        candidatos = (
            raiz / "arbohub.ico",
            raiz / "assets" / "arbohub.ico",
            raiz / "assets" / "arbohub_icon.ico"
        )

        for caminho in candidatos:
            if not caminho.exists():
                continue

            try:
                self.iconbitmap(
                    str(caminho)
                )
                return
            except Exception:
                continue
