from __future__ import annotations

from typing import Literal
import math

import customtkinter as ctk

from app.gui.themes.colors import Colors


TipoDialogo = Literal[
    "informacao",
    "sucesso",
    "aviso",
    "erro",
    "confirmacao"
]


class ArboHubDialog(ctk.CTkToplevel):
    """
    Diálogo modal no mesmo padrão visual do ArboHub.

    Substitui as pequenas janelas nativas do tkinter em ações da
    interface, mantendo tipografia, cores, bordas e espaçamento
    consistentes com o restante do software.
    """

    LARGURA = 540
    ALTURA_MINIMA = 360
    ALTURA_MAXIMA = 540

    CONFIGURACOES = {
        "informacao": {
            "icone": "i",
            "rotulo": "INFORMAÇÃO",
            "cor": Colors.PRIMARY
        },
        "sucesso": {
            "icone": "✓",
            "rotulo": "OPERAÇÃO CONCLUÍDA",
            "cor": Colors.SUCCESS
        },
        "aviso": {
            "icone": "!",
            "rotulo": "ATENÇÃO",
            "cor": Colors.WARNING
        },
        "erro": {
            "icone": "×",
            "rotulo": "NÃO FOI POSSÍVEL CONCLUIR",
            "cor": Colors.ERROR
        },
        "confirmacao": {
            "icone": "?",
            "rotulo": "CONFIRMAÇÃO",
            "cor": Colors.PRIMARY
        }
    }

    def __init__(
        self,
        master,
        titulo: str,
        mensagem: str,
        tipo: TipoDialogo = "informacao",
        texto_confirmar: str = "Entendi",
        texto_cancelar: str = "Cancelar",
        exibir_cancelar: bool = False
    ):
        super().__init__(master)

        if tipo not in self.CONFIGURACOES:
            tipo = "informacao"

        self.tipo = tipo
        self.titulo_dialogo = titulo
        self.mensagem = mensagem
        self.texto_confirmar = texto_confirmar
        self.texto_cancelar = texto_cancelar
        self.exibir_cancelar = exibir_cancelar

        self.resultado = False
        self.configuracao = self.CONFIGURACOES[tipo]

        self.altura_dialogo = (
            self._calcular_altura_dialogo(
                mensagem
            )
        )

        self.title(f"ArboHub — {titulo}")
        self.geometry(
            f"{self.LARGURA}x{self.altura_dialogo}"
        )
        self.minsize(
            self.LARGURA,
            self.altura_dialogo
        )
        self.resizable(False, False)
        self.configure(
            fg_color=Colors.BACKGROUND
        )

        try:
            self.transient(master)
        except Exception:
            pass

        self.protocol(
            "WM_DELETE_WINDOW",
            self._cancelar
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_cabecalho()
        self._criar_conteudo()
        self._criar_rodape()

        self.after(
            30,
            self._centralizar
        )
        self.after(
            60,
            self._ativar_modal
        )

    def _calcular_altura_dialogo(
        self,
        mensagem: str
    ) -> int:
        """
        Calcula uma altura suficiente para a mensagem atual.

        Preserva a largura e todo o estilo visual do diálogo, mas
        evita que textos maiores sejam cortados em escalas de
        interface ou resoluções diferentes.
        """

        largura_estimada_linha = 52
        linhas_visuais = 0

        for linha in mensagem.splitlines() or [""]:
            quantidade = max(
                1,
                math.ceil(
                    len(linha)
                    / largura_estimada_linha
                )
            )
            linhas_visuais += quantidade

        altura_estimada = (
            285
            + linhas_visuais * 21
        )

        return max(
            self.ALTURA_MINIMA,
            min(
                self.ALTURA_MAXIMA,
                altura_estimada
            )
        )

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=0
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew"
        )
        cabecalho.grid_columnconfigure(
            1,
            weight=1
        )

        icone = ctk.CTkFrame(
            cabecalho,
            width=44,
            height=44,
            fg_color=Colors.BUTTON,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        icone.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(20, 13),
            pady=18
        )
        icone.grid_propagate(False)

        ctk.CTkLabel(
            icone,
            text=self.configuracao["icone"],
            font=ctk.CTkFont(
                family="Segoe UI",
                size=21,
                weight="bold"
            ),
            text_color=self.configuracao["cor"]
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            cabecalho,
            text=self.configuracao["rotulo"],
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=self.configuracao["cor"],
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="sw",
            padx=(0, 20),
            pady=(17, 1)
        )

        ctk.CTkLabel(
            cabecalho,
            text=self.titulo_dialogo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=19,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=1,
            sticky="nw",
            padx=(0, 20),
            pady=(0, 17)
        )

    def _criar_conteudo(self):
        conteudo = ctk.CTkFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )
        conteudo.grid(
            row=1,
            column=0,
            sticky="nsew"
        )
        conteudo.grid_columnconfigure(0, weight=1)
        conteudo.grid_rowconfigure(0, weight=1)

        caixa = ctk.CTkFrame(
            conteudo,
            fg_color=Colors.SURFACE,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        caixa.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=20,
            pady=20
        )
        caixa.grid_columnconfigure(0, weight=1)
        caixa.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            caixa,
            text=self.mensagem,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="nw",
            justify="left",
            wraplength=455
        ).grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=18,
            pady=18
        )

    def _criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=0
        )
        rodape.grid(
            row=2,
            column=0,
            sticky="ew"
        )
        rodape.grid_columnconfigure(0, weight=1)

        botoes = ctk.CTkFrame(
            rodape,
            fg_color="transparent"
        )
        botoes.grid(
            row=0,
            column=0,
            sticky="e",
            padx=20,
            pady=16
        )

        if self.exibir_cancelar:
            ctk.CTkButton(
                botoes,
                text=self.texto_cancelar,
                command=self._cancelar,
                width=130,
                height=38,
                corner_radius=7,
                fg_color="transparent",
                hover_color=Colors.SURFACE_HOVER,
                border_width=1,
                border_color=Colors.BORDER,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12,
                    weight="bold"
                )
            ).pack(
                side="left",
                padx=(0, 10)
            )

        cor_botao = (
            self.configuracao["cor"]
            if self.tipo in {
                "sucesso",
                "aviso",
                "erro"
            }
            else Colors.PRIMARY
        )

        cores_hover = {
            "sucesso": Colors.SUCCESS_HOVER,
            "aviso": Colors.WARNING_HOVER,
            "erro": Colors.ERROR_HOVER
        }

        ctk.CTkButton(
            botoes,
            text=self.texto_confirmar,
            command=self._confirmar,
            width=155,
            height=38,
            corner_radius=7,
            fg_color=cor_botao,
            hover_color=cores_hover.get(
                self.tipo,
                Colors.PRIMARY_HOVER
            ),
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).pack(side="left")

    def _confirmar(self):
        self.resultado = True
        self._fechar()

    def _cancelar(self):
        self.resultado = False
        self._fechar()

    def _fechar(self):
        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

    def _ativar_modal(self):
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except Exception:
            pass

    def _centralizar(self):
        self.update_idletasks()

        master = self.master

        try:
            master.update_idletasks()

            x = (
                master.winfo_rootx()
                + (
                    master.winfo_width()
                    - self.winfo_width()
                ) // 2
            )
            y = (
                master.winfo_rooty()
                + (
                    master.winfo_height()
                    - self.winfo_height()
                ) // 2
            )

        except Exception:
            x = (
                self.winfo_screenwidth()
                - self.winfo_width()
            ) // 2
            y = (
                self.winfo_screenheight()
                - self.winfo_height()
            ) // 2

        self.geometry(
            f"+{max(x, 20)}+{max(y, 20)}"
        )

    def exibir(self) -> bool:
        self.wait_window()
        return self.resultado


def mostrar_dialogo_arbohub(
    master,
    titulo: str,
    mensagem: str,
    tipo: TipoDialogo = "informacao",
    texto_botao: str = "Entendi"
):
    dialogo = ArboHubDialog(
        master=master,
        titulo=titulo,
        mensagem=mensagem,
        tipo=tipo,
        texto_confirmar=texto_botao,
        exibir_cancelar=False
    )
    dialogo.exibir()


def solicitar_confirmacao_arbohub(
    master,
    titulo: str,
    mensagem: str,
    texto_confirmar: str = "Continuar",
    texto_cancelar: str = "Cancelar",
    tipo: TipoDialogo = "confirmacao"
) -> bool:
    dialogo = ArboHubDialog(
        master=master,
        titulo=titulo,
        mensagem=mensagem,
        tipo=tipo,
        texto_confirmar=texto_confirmar,
        texto_cancelar=texto_cancelar,
        exibir_cancelar=True
    )
    return dialogo.exibir()
