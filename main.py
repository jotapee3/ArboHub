import customtkinter as ctk

from app.gui.windows.main_window import MainWindow
from app.services.configuracoes_service import (
    ConfiguracoesService
)
from app.services.escala_interface_service import (
    EscalaInterfaceService
)


def aplicar_escala_interface():
    """
    Aplica a escala antes que qualquer janela seja criada.
    """

    try:
        configuracoes = (
            ConfiguracoesService().carregar()
        )
        EscalaInterfaceService().aplicar_das_configuracoes(
            configuracoes
        )
    except Exception:
        # Uma preferência inválida nunca deve impedir a abertura.
        ctk.set_widget_scaling(1.0)


def main():
    ctk.set_appearance_mode("dark")
    aplicar_escala_interface()

    MainWindow()


if __name__ == "__main__":
    main()
