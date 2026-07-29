from __future__ import annotations

from typing import Any

import customtkinter as ctk

from app.gui.themes.colors import Colors


class ConfirmacaoConferenciaDialog(ctk.CTkToplevel):
    """
    Janela nativa para a conferência humana de um agravo.

    Por ser um CTkToplevel, a janela:
    - pode ser movida para fora do navegador;
    - pode ficar em outro monitor;
    - permanece independente da página do SINAN;
    - não bloqueia a interação com o navegador.

    A janela retorna somente o que o usuário informar.
    Nenhum dado dos resultados do SINAN é lido.
    """

    LARGURA = 470
    ALTURA = 520

    def __init__(
        self,
        master,
        agravo: str,
        acao_seguinte: str,
        manter_no_topo: bool = True
    ):
        super().__init__(master)

        self.agravo = agravo
        self.acao_seguinte = acao_seguinte
        self.manter_no_topo = manter_no_topo

        self.resultado: dict[str, Any] | None = None

        self.title(
            f"ArboHub — Conferência de {agravo}"
        )
        self.geometry(
            f"{self.LARGURA}x{self.ALTURA}"
        )
        self.minsize(
            self.LARGURA,
            self.ALTURA
        )
        self.resizable(
            False,
            True
        )

        self.configure(
            fg_color=Colors.BACKGROUND
        )

        # Não usamos grab_set: o usuário precisa continuar
        # interagindo com o navegador do SINAN.
        if self.manter_no_topo:
            try:
                self.attributes(
                    "-topmost",
                    True
                )
            except Exception:
                pass

        self.protocol(
            "WM_DELETE_WINDOW",
            self._ao_tentar_fechar
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )
        self.grid_rowconfigure(
            1,
            weight=1
        )

        self.opcao_var = ctk.StringVar(
            value="manteve_igual"
        )

        self.criar_cabecalho()
        self.criar_conteudo()
        self.criar_rodape()

        self.after(
            50,
            self._posicionar_na_tela
        )
        self.after(
            80,
            self._trazer_para_frente
        )

    # ------------------------------------------------------------------
    # Construção visual
    # ------------------------------------------------------------------

    def criar_cabecalho(self):
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
            width=40,
            height=40,
            fg_color=Colors.BUTTON,
            corner_radius=8
        )
        icone.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(18, 12),
            pady=16
        )
        icone.grid_propagate(False)

        ctk.CTkLabel(
            icone,
            text="✓",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            cabecalho,
            text="CONFERÊNCIA HUMANA",
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
            padx=(0, 18),
            pady=(15, 1)
        )

        ctk.CTkLabel(
            cabecalho,
            text=f"Verificação de {self.agravo}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=18,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=1,
            sticky="nw",
            padx=(0, 18),
            pady=(0, 15)
        )

    def criar_conteudo(self):
        conteudo = ctk.CTkScrollableFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )
        conteudo.grid(
            row=1,
            column=0,
            sticky="nsew"
        )
        conteudo.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            conteudo,
            text=(
                "Confira os resultados apresentados no SINAN. "
                "Houve alguma alteração em relação à "
                "verificação anterior?"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=410
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(20, 14)
        )

        opcoes = ctk.CTkFrame(
            conteudo,
            fg_color="transparent"
        )
        opcoes.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20
        )
        opcoes.grid_columnconfigure(
            0,
            weight=1
        )

        self.radio_igual = self._criar_opcao(
            master=opcoes,
            texto="Não houve alteração",
            valor="manteve_igual",
            linha=0
        )

        self.radio_mudou = self._criar_opcao(
            master=opcoes,
            texto="Houve alteração",
            valor="mudou",
            linha=1
        )

        ctk.CTkLabel(
            conteudo,
            text="O que mudou?",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 6)
        )

        self.campo_observacao = ctk.CTkTextbox(
            conteudo,
            height=110,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER,
            fg_color=Colors.SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            wrap="word"
        )
        self.campo_observacao.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20
        )

        self.label_ajuda = ctk.CTkLabel(
            conteudo,
            text=(
                "Selecione “Houve alteração” para habilitar "
                "o campo de observação."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=410
        )
        self.label_ajuda.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=20,
            pady=(6, 0)
        )

        self.label_erro = ctk.CTkLabel(
            conteudo,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=410
        )
        self.label_erro.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(8, 18)
        )

        self._atualizar_estado_observacao()

    def criar_rodape(self):
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
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

        texto_botao = (
            f"Confirmar e {self.acao_seguinte}"
        )

        self.botao_confirmar = ctk.CTkButton(
            rodape,
            text=texto_botao,
            command=self._confirmar,
            height=40,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_confirmar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=18,
            pady=(14, 8)
        )

        ctk.CTkLabel(
            rodape,
            text=(
                "Esta janela pode ser arrastada para fora "
                "do navegador ou para outro monitor."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="center"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12)
        )

    def _criar_opcao(
        self,
        master,
        texto: str,
        valor: str,
        linha: int
    ) -> ctk.CTkRadioButton:
        container = ctk.CTkFrame(
            master,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        container.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(
                (0, 8)
                if linha == 0
                else 0
            )
        )
        container.grid_columnconfigure(
            0,
            weight=1
        )

        radio = ctk.CTkRadioButton(
            container,
            text=texto,
            variable=self.opcao_var,
            value=valor,
            command=self._atualizar_estado_observacao,
            radiobutton_width=18,
            radiobutton_height=18,
            border_width_unchecked=2,
            border_width_checked=5,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            border_color=Colors.TEXT_MUTED,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        radio.grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=13
        )

        return radio

    # ------------------------------------------------------------------
    # Comportamento
    # ------------------------------------------------------------------

    def _atualizar_estado_observacao(self):
        mudou = (
            self.opcao_var.get() == "mudou"
        )

        if mudou:
            self.campo_observacao.configure(
                state="normal",
                border_color=Colors.PRIMARY
            )
            self.label_ajuda.configure(
                text=(
                    "Descreva resumidamente a alteração "
                    "observada para continuar."
                )
            )
            self.after(
                50,
                self.campo_observacao.focus_set
            )
        else:
            self.campo_observacao.configure(
                state="normal"
            )
            self.campo_observacao.delete(
                "1.0",
                "end"
            )
            self.campo_observacao.configure(
                state="disabled",
                border_color=Colors.BORDER
            )
            self.label_ajuda.configure(
                text=(
                    "Sem alteração: basta confirmar "
                    "para prosseguir."
                )
            )
            self.label_erro.configure(
                text=""
            )

    def _confirmar(self):
        mudou = (
            self.opcao_var.get() == "mudou"
        )

        observacao = ""

        if mudou:
            observacao = (
                self.campo_observacao.get(
                    "1.0",
                    "end"
                ).strip()
            )

            if not observacao:
                self.label_erro.configure(
                    text=(
                        "Descreva o que mudou antes "
                        "de continuar."
                    ),
                    text_color=Colors.TEXT_SECONDARY
                )
                self.campo_observacao.focus_set()
                return

        self.resultado = {
            "confirmado": True,
            "houve_alteracao": mudou,
            "resultado_comparacao": (
                "mudou"
                if mudou
                else "manteve_igual"
            ),
            "observacao": observacao
        }

        self.destroy()

    def _ao_tentar_fechar(self):
        self.label_erro.configure(
            text=(
                "Use o botão de confirmação para concluir "
                "esta etapa da rotina."
            ),
            text_color=Colors.TEXT_SECONDARY
        )
        self._trazer_para_frente()

    def _trazer_para_frente(self):
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _posicionar_na_tela(self):
        """
        Posiciona a janela no lado direito da tela.

        Ela continua totalmente arrastável e pode ser levada
        para qualquer monitor.
        """

        self.update_idletasks()

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()

        largura = self.winfo_width()
        altura = self.winfo_height()

        x = max(
            20,
            largura_tela - largura - 40
        )
        y = max(
            20,
            int((altura_tela - altura) / 2)
        )

        self.geometry(
            f"+{x}+{y}"
        )

    def exibir(self) -> dict[str, Any]:
        """
        Aguarda a confirmação sem bloquear o navegador.
        """

        self.wait_window()

        if self.resultado is None:
            raise RuntimeError(
                "A confirmação foi encerrada sem resultado."
            )

        return self.resultado


def solicitar_confirmacao_conferencia_nativa(
    agravo: str,
    acao_seguinte: str,
    master=None,
    manter_no_topo: bool = True
) -> dict[str, Any]:
    """
    Abre a janela de conferência.

    Quando chamada fora do ArboHub, cria uma raiz oculta apenas
    para hospedar o CTkToplevel. Na integração definitiva,
    a janela principal do aplicativo poderá ser passada em master.
    """

    raiz_temporaria = None

    if master is None:
        ctk.set_appearance_mode("dark")

        raiz_temporaria = ctk.CTk()
        raiz_temporaria.withdraw()
        master = raiz_temporaria

    try:
        dialogo = ConfirmacaoConferenciaDialog(
            master=master,
            agravo=agravo,
            acao_seguinte=acao_seguinte,
            manter_no_topo=manter_no_topo
        )

        return dialogo.exibir()

    finally:
        if raiz_temporaria is not None:
            raiz_temporaria.destroy()