import sys

from app.core.ambiente_execucao import preparar_ambiente_execucao


preparar_ambiente_execucao()


import customtkinter as ctk

from app.services.configuracoes_service import (
    ConfiguracoesService
)
from app.services.escala_interface_service import (
    EscalaInterfaceService
)
from app.services.tema_interface_service import (
    TemaInterfaceService
)


def preparar_interface():
    """
    Aplica tema e escala antes que qualquer página seja importada.

    Isso garante que cores avaliadas durante a importação já usem a
    paleta correta e evita componentes misturados entre temas.
    """

    configuracoes = (
        ConfiguracoesService().carregar()
    )

    try:
        TemaInterfaceService().aplicar_das_configuracoes(
            configuracoes
        )
    except Exception:
        TemaInterfaceService().aplicar(
            "escuro"
        )

    try:
        EscalaInterfaceService().aplicar_das_configuracoes(
            configuracoes
        )
    except Exception:
        # Uma preferência inválida nunca deve impedir a abertura.
        ctk.set_widget_scaling(1.0)


def main():
    if "--verificar-distribuicao" in sys.argv:
        from app.core.verificacao_distribuicao import (
            executar_verificacao_distribuicao,
        )

        return executar_verificacao_distribuicao()

    preparar_interface()

    # A janela e as páginas são importadas somente depois da paleta.
    from app.gui.windows.main_window import MainWindow

    MainWindow()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
