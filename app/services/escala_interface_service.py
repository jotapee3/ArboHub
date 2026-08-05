from __future__ import annotations

from typing import Any

import customtkinter as ctk


class EscalaInterfaceService:
    """
    Aplica a escala visual antes da criação das janelas.

    A escala personalizada atua sobre dimensões dos componentes e
    textos do CustomTkinter. A geometria base da janela principal é
    preservada para evitar que 110% ou 125% ultrapassem a área útil
    de monitores menores.
    """

    ESCALAS_VALIDAS = {
        90,
        100,
        110,
        125
    }

    ESCALA_PADRAO = 100

    def aplicar_das_configuracoes(
        self,
        configuracoes: dict[str, Any]
    ) -> int:
        aparencia = configuracoes.get(
            "aparencia",
            {}
        )

        return self.aplicar(
            aparencia.get(
                "escala_percentual",
                self.ESCALA_PADRAO
            )
        )

    def aplicar(
        self,
        escala_percentual: Any
    ) -> int:
        try:
            escala = int(
                escala_percentual
            )
        except (
            TypeError,
            ValueError
        ):
            escala = self.ESCALA_PADRAO

        if escala not in self.ESCALAS_VALIDAS:
            escala = self.ESCALA_PADRAO

        ctk.set_widget_scaling(
            escala / 100
        )

        return escala
