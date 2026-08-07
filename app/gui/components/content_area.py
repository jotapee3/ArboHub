import customtkinter as ctk

from app.gui.themes.colors import Colors


class ContentArea(ctk.CTkFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.pagina_atual = None
        self.chave_pagina_atual = None
        self.paginas = {}

    def _ocultar_pagina_atual(self):
        if self.pagina_atual is None:
            return

        self.pagina_atual.pack_forget()

    def mostrar_pagina(
        self,
        chave,
        fabrica_pagina
    ):
        """
        Exibe uma pagina sem reconstrui-la a cada troca de aba.

        Cada pagina e criada somente na primeira abertura e depois
        permanece em cache. Isso evita destruir e recriar centenas de
        widgets e services durante a navegacao pela sidebar.
        """

        if (
            self.chave_pagina_atual == chave
            and self.pagina_atual is not None
            and self.pagina_atual.winfo_exists()
        ):
            return self.pagina_atual

        self._ocultar_pagina_atual()

        pagina = self.paginas.get(chave)

        if (
            pagina is None
            or not pagina.winfo_exists()
        ):
            pagina = fabrica_pagina(self)
            self.paginas[chave] = pagina

        self.pagina_atual = pagina
        self.chave_pagina_atual = chave

        self.pagina_atual.pack(
            fill="both",
            expand=True
        )

        return self.pagina_atual

    def obter_pagina(self, chave):
        pagina = self.paginas.get(chave)

        if (
            pagina is None
            or not pagina.winfo_exists()
        ):
            return None

        return pagina

    def descartar_pagina(self, chave):
        """
        Remove uma pagina do cache quando ela realmente precisa ser
        recriada, por exemplo apos a alteracao de uma configuracao que
        seja lida somente na inicializacao daquela tela.
        """

        pagina = self.paginas.pop(
            chave,
            None
        )

        if pagina is None:
            return

        if pagina is self.pagina_atual:
            self.pagina_atual = None
            self.chave_pagina_atual = None

        if pagina.winfo_exists():
            pagina.destroy()