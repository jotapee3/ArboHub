from __future__ import annotations

import sys
from typing import Any

import customtkinter as ctk

from app.gui.themes.colors import Colors


class TemaInterfaceService:
    """
    Resolve e aplica o tema antes da criação das janelas.

    A opção "sistema" consulta o tema de aplicativos do Windows em
    cada abertura. Se a consulta não estiver disponível, o ArboHub
    usa o tema escuro, que permanece o padrão oficial.
    """

    TEMAS_VALIDOS = {
        "escuro",
        "claro",
        "sistema"
    }

    def aplicar_das_configuracoes(
        self,
        configuracoes: dict[str, Any]
    ) -> str:
        tema = (
            configuracoes.get(
                "aparencia",
                {}
            ).get(
                "tema",
                "escuro"
            )
        )
        return self.aplicar(tema)

    def aplicar(self, tema: str) -> str:
        tema_resolvido = self.resolver(tema)

        ctk.set_appearance_mode(
            "light"
            if tema_resolvido == "claro"
            else "dark"
        )
        Colors.aplicar_tema(
            tema_resolvido
        )

        return tema_resolvido

    def resolver(self, tema: str) -> str:
        normalizado = str(
            tema
        ).strip().casefold()

        if normalizado not in self.TEMAS_VALIDOS:
            normalizado = "escuro"

        if normalizado == "sistema":
            return self._obter_tema_windows()

        return normalizado

    def _obter_tema_windows(self) -> str:
        if sys.platform != "win32":
            return "escuro"

        try:
            import winreg

            caminho = (
                r"Software\Microsoft\Windows\CurrentVersion"
                r"\Themes\Personalize"
            )

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                caminho
            ) as chave:
                valor, _ = winreg.QueryValueEx(
                    chave,
                    "AppsUseLightTheme"
                )

            return (
                "claro"
                if int(valor) == 1
                else "escuro"
            )

        except (
            OSError,
            TypeError,
            ValueError
        ):
            return "escuro"
