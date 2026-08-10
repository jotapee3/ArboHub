import os
import sys
import customtkinter as ctk

from pathlib import Path
from app.gui.components.arbohub_dialog import mostrar_dialogo_arbohub
from app.gui.components.sidebar import Sidebar
from app.gui.components.content_area import ContentArea
from app.gui.pages.inicio_page import InicioPage
from app.gui.pages.sinan_page import SinanPage
from app.gui.pages.gal_page import GalPage
from app.gui.pages.historico_page import HistoricoPage
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

        pasta_assets = (
            Path(__file__).resolve().parent.parent
            / "assets"
        )
        nome_icone = (
            "arbohub_light.ico"
            if Colors.TEMA_ATUAL == "claro"
            else "arbohub_dark.ico"
        )
        caminho_icone = (
            pasta_assets
            / nome_icone
        )

        if not caminho_icone.exists():
            caminho_icone = (
                pasta_assets
                / "arbohub.ico"
            )

        try:
            self.iconbitmap(
                caminho_icone
            )
        except Exception:
            pass

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
            comando_historico=self.abrir_historico,
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
            "inicio",
            lambda master: InicioPage(
                master,
                comando_sinan=self.abrir_sinan,
                comando_gal=self.abrir_gal
            )
        )

        self.sidebar.selecionar_inicio()

    def abrir_sinan(self):
        self.content_area.mostrar_pagina(
            "sinan",
            SinanPage
        )
        self.sidebar.selecionar_sinan()

    def abrir_gal(self):
        self.content_area.mostrar_pagina(
            "gal",
            GalPage
        )
        self.sidebar.selecionar_gal()

    def abrir_historico(self):
        self.content_area.mostrar_pagina(
            "historico",
            HistoricoPage
        )
        self.sidebar.selecionar_historico()

    def abrir_configuracoes(self):
        self.content_area.mostrar_pagina(
            "configuracoes",
            lambda master: ConfiguracoesPage(
                master,
                ao_salvar=self._ao_salvar_configuracoes,
                ao_reiniciar=self.reiniciar_aplicativo
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
        operacional_anterior = self.configuracoes.get(
            "operacional",
            {}
        )
        self.configuracoes = configuracoes

        if (
            operacional_anterior
            != configuracoes.get(
                "operacional",
                {}
            )
        ):
            pagina_sinan = self.content_area.obter_pagina(
                "sinan"
            )

            if (
                pagina_sinan is not None
                and hasattr(
                    pagina_sinan,
                    "recarregar_configuracoes_operacionais"
                )
            ):
                pagina_sinan.recarregar_configuracoes_operacionais()

        self._aplicar_estado_janela()

    def reiniciar_aplicativo(self):
        """
        Reinicia o ArboHub usando a mesma execução atual.

        Em desenvolvimento, substitui somente o processo main.py e
        preserva o supervisor dev.py. Em uma versão empacotada, abre
        novamente o próprio executável.
        """

        if getattr(sys, "frozen", False):
            comando = [
                sys.executable,
                *sys.argv[1:]
            ]
        else:
            raiz_projeto = (
                Path(__file__).resolve().parents[3]
            )
            comando = [
                sys.executable,
                str(raiz_projeto / "main.py"),
                *sys.argv[1:]
            ]

        try:
            self.withdraw()
            self.update_idletasks()
            os.execv(
                comando[0],
                comando
            )
        except Exception as erro:
            self.deiconify()
            self.lift()

            mostrar_dialogo_arbohub(
                master=self,
                titulo="Reinicialização não concluída",
                mensagem=(
                    "As configurações continuam salvas, mas o "
                    "ArboHub não conseguiu reiniciar "
                    "automaticamente.\n\n"
                    "Feche o programa e abra-o novamente para "
                    "aplicar todas as alterações.\n\n"
                    f"Detalhe: {erro}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )

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
