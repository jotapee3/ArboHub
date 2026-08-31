from __future__ import annotations

import calendar
import tkinter as tk
from collections.abc import Callable
from datetime import date

import customtkinter as ctk

from app.gui.themes.colors import Colors
from app.services.qualifica.calendario_epidemiologico import (
    CalendarioEpidemiologico,
)


MESES = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


class CalendarioDialog(ctk.CTkToplevel):
    """Calendário modal simples e coerente com a interface do ArboHub."""

    def __init__(
        self,
        master,
        data_atual: date,
        ao_selecionar: Callable[[date], None],
    ):
        super().__init__(master)

        self.data_selecionada = data_atual
        self.ano_exibido = data_atual.year
        self.mes_exibido = data_atual.month
        self.variavel_mes = tk.StringVar(
            value=MESES[data_atual.month - 1]
        )
        self.variavel_ano = tk.StringVar(
            value=str(data_atual.year)
        )
        self.ao_selecionar = ao_selecionar

        self.title("ArboHub — Selecionar data")
        self.geometry("380x410")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BACKGROUND)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_cabecalho()
        self._criar_calendario()
        self._criar_rodape()
        self._renderizar_dias()

        self.after(30, self._centralizar)
        self.after(60, self._ativar_modal)

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=0,
        )
        cabecalho.grid(row=0, column=0, sticky="ew")
        cabecalho.grid_columnconfigure(1, weight=1)

        self.botao_anterior = ctk.CTkButton(
            cabecalho,
            text="‹",
            command=self._mes_anterior,
            width=38,
            height=36,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=22),
        )
        self.botao_anterior.grid(
            row=0,
            column=0,
            padx=(16, 6),
            pady=16,
        )

        self.combo_mes = ctk.CTkComboBox(
            cabecalho,
            values=list(MESES),
            variable=self.variavel_mes,
            command=self._selecionar_mes,
            state="readonly",
            width=132,
            height=34,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
        )
        self.combo_mes.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 5),
        )

        anos = [
            str(ano)
            for ano in range(date.today().year + 2, 1979, -1)
        ]
        self.combo_ano = ctk.CTkComboBox(
            cabecalho,
            values=anos,
            variable=self.variavel_ano,
            command=self._selecionar_ano,
            state="readonly",
            width=84,
            height=34,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold",
            ),
        )
        self.combo_ano.grid(
            row=0,
            column=2,
            padx=(5, 0),
        )

        self.botao_proximo = ctk.CTkButton(
            cabecalho,
            text="›",
            command=self._proximo_mes,
            width=38,
            height=36,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(size=22),
        )
        self.botao_proximo.grid(
            row=0,
            column=3,
            padx=(6, 16),
            pady=16,
        )

    def _criar_calendario(self):
        self.container_calendario = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.container_calendario.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=18,
            pady=(16, 8),
        )

        for coluna in range(7):
            self.container_calendario.grid_columnconfigure(
                coluna,
                weight=1,
                uniform="dias",
            )

        for coluna, texto in enumerate(
            ("D", "S", "T", "Q", "Q", "S", "S")
        ):
            ctk.CTkLabel(
                self.container_calendario,
                text=texto,
                text_color=Colors.TEXT_MUTED,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold",
                ),
            ).grid(
                row=0,
                column=coluna,
                sticky="nsew",
                pady=(0, 7),
            )

        self.botoes_dias: list[ctk.CTkButton] = []
        for indice in range(42):
            linha = indice // 7 + 1
            coluna = indice % 7
            botao = ctk.CTkButton(
                self.container_calendario,
                text="",
                width=38,
                height=34,
                corner_radius=7,
                fg_color="transparent",
                hover_color=Colors.SURFACE_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12,
                ),
            )
            botao.grid(
                row=linha,
                column=coluna,
                padx=2,
                pady=2,
                sticky="nsew",
            )
            self.botoes_dias.append(botao)

    def _criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        rodape.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(4, 18),
        )
        rodape.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            rodape,
            text="Hoje",
            command=lambda: self._selecionar(date.today()),
            height=38,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5),
        )

        ctk.CTkButton(
            rodape,
            text="Cancelar",
            command=self.destroy,
            height=38,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0),
        )

    def _renderizar_dias(self):
        self.variavel_mes.set(MESES[self.mes_exibido - 1])
        self.variavel_ano.set(str(self.ano_exibido))

        primeiro_dia, quantidade = calendar.monthrange(
            self.ano_exibido,
            self.mes_exibido,
        )
        deslocamento_domingo = (primeiro_dia + 1) % 7

        for indice, botao in enumerate(self.botoes_dias):
            dia = indice - deslocamento_domingo + 1
            if dia < 1 or dia > quantidade:
                botao.configure(
                    text="",
                    state="disabled",
                    fg_color="transparent",
                )
                continue

            data_dia = date(
                self.ano_exibido,
                self.mes_exibido,
                dia,
            )
            selecionado = data_dia == self.data_selecionada
            botao.configure(
                text=str(dia),
                state="normal",
                command=(
                    lambda valor=data_dia: self._selecionar(valor)
                ),
                fg_color=(
                    Colors.PRIMARY
                    if selecionado
                    else "transparent"
                ),
                text_color=(
                    Colors.TEXT_ON_PRIMARY
                    if selecionado
                    else Colors.TEXT_PRIMARY
                ),
            )

    def _mes_anterior(self):
        self.mes_exibido -= 1
        if self.mes_exibido == 0:
            self.mes_exibido = 12
            self.ano_exibido -= 1
        self._renderizar_dias()

    def _proximo_mes(self):
        self.mes_exibido += 1
        if self.mes_exibido == 13:
            self.mes_exibido = 1
            self.ano_exibido += 1
        self._renderizar_dias()

    def _selecionar_mes(self, nome_mes: str):
        self.mes_exibido = MESES.index(nome_mes) + 1
        self._renderizar_dias()

    def _selecionar_ano(self, ano: str):
        self.ano_exibido = int(ano)
        self._renderizar_dias()

    def _selecionar(self, valor: date):
        self.ao_selecionar(valor)
        self.destroy()

    def _centralizar(self):
        self.update_idletasks()
        master = self.master.winfo_toplevel()
        x = master.winfo_rootx() + (
            master.winfo_width() - self.winfo_width()
        ) // 2
        y = master.winfo_rooty() + (
            master.winfo_height() - self.winfo_height()
        ) // 2
        self.geometry(f"+{max(20, x)}+{max(20, y)}")

    def _ativar_modal(self):
        self.lift()
        self.focus_force()
        self.grab_set()


class SemanaEpidemiologicaDialog(ctk.CTkToplevel):
    """Seleciona uma SE e devolve seu intervalo de domingo a sábado."""

    def __init__(
        self,
        master,
        data_referencia: date,
        ao_selecionar: Callable[[date, date], None],
    ):
        super().__init__(master)

        self.ao_selecionar = ao_selecionar
        self.title("ArboHub — Semana epidemiológica")
        self.geometry("400x300")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BACKGROUND)
        self.transient(master.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.grid_columnconfigure(0, weight=1)

        conteudo = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER,
        )
        conteudo.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=20,
            pady=20,
        )
        conteudo.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            conteudo,
            text="Escolher semana epidemiológica",
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold",
            ),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=(18, 5),
        )

        ctk.CTkLabel(
            conteudo,
            text="O ArboHub preencherá o domingo e o sábado da SE.",
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=(0, 18),
        )

        anos = [
            str(ano)
            for ano in range(date.today().year + 1, 1999, -1)
        ]
        self.variavel_ano = tk.StringVar(
            value=str(data_referencia.year)
        )
        inicio_ano = CalendarioEpidemiologico.inicio_do_ano(
            data_referencia.year
        )
        numero_semana = max(
            1,
            ((data_referencia - inicio_ano).days // 7) + 1,
        )
        quantidade_semanas = (
            CalendarioEpidemiologico.quantidade_de_semanas(
                data_referencia.year
            )
        )
        numero_semana = min(
            numero_semana,
            quantidade_semanas,
        )
        self.variavel_semana = tk.StringVar(
            value=str(numero_semana)
        )

        self.combo_ano = self._criar_combo(
            conteudo,
            "Ano",
            anos,
            self.variavel_ano,
            coluna=0,
        )
        self.combo_ano.configure(
            command=lambda _valor: self._atualizar_semanas()
        )
        self.combo_semana = self._criar_combo(
            conteudo,
            "Semana",
            ["1"],
            self.variavel_semana,
            coluna=1,
        )
        self._atualizar_semanas()

        botoes = ctk.CTkFrame(
            conteudo,
            fg_color="transparent",
        )
        botoes.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=18,
        )
        botoes.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            botoes,
            text="Cancelar",
            command=self.destroy,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(
            botoes,
            text="Usar esta semana",
            command=self._confirmar,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.after(30, self._centralizar)
        self.after(60, self._ativar_modal)

    @staticmethod
    def _criar_combo(
        master,
        titulo: str,
        valores: list[str],
        variavel: tk.StringVar,
        *,
        coluna: int,
    ) -> ctk.CTkComboBox:
        ctk.CTkLabel(
            master,
            text=titulo,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).grid(
            row=2,
            column=coluna,
            sticky="ew",
            padx=(18, 6) if coluna == 0 else (6, 18),
        )
        combo = ctk.CTkComboBox(
            master,
            values=valores,
            variable=variavel,
            state="readonly",
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_text_color=Colors.TEXT_PRIMARY,
            text_color=Colors.TEXT_PRIMARY,
        )
        combo.grid(
            row=3,
            column=coluna,
            sticky="ew",
            padx=(18, 6) if coluna == 0 else (6, 18),
            pady=(5, 0),
        )
        return combo

    def _atualizar_semanas(self):
        ano = int(self.variavel_ano.get())
        quantidade = CalendarioEpidemiologico.quantidade_de_semanas(
            ano
        )
        valores = [str(numero) for numero in range(1, quantidade + 1)]
        self.combo_semana.configure(values=valores)
        if self.variavel_semana.get() not in valores:
            self.variavel_semana.set(valores[-1])

    def _confirmar(self):
        semana = CalendarioEpidemiologico.obter_semana(
            int(self.variavel_ano.get()),
            int(self.variavel_semana.get()),
        )
        self.ao_selecionar(
            semana.data_inicial,
            semana.data_final,
        )
        self.destroy()

    def _centralizar(self):
        self.update_idletasks()
        master = self.master.winfo_toplevel()
        x = master.winfo_rootx() + (
            master.winfo_width() - self.winfo_width()
        ) // 2
        y = master.winfo_rooty() + (
            master.winfo_height() - self.winfo_height()
        ) // 2
        self.geometry(f"+{max(20, x)}+{max(20, y)}")

    def _ativar_modal(self):
        self.lift()
        self.focus_force()
        self.grab_set()
