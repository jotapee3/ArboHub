from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.gui.components.arbohub_dialog import (
    mostrar_dialogo_arbohub,
    solicitar_confirmacao_arbohub
)
from app.gui.themes.colors import Colors
from app.services.atualizacao_gal_service import (
    AtualizacaoGalService
)
from app.services.notificacoes_service import NotificacoesService


class GalPage(ctk.CTkFrame):
    """Tela da rotina semanal assistida do GAL."""

    ETAPAS = (
        (AtualizacaoGalService.ETAPA_ACESSO, "Acesso ao GAL"),
        (
            AtualizacaoGalService.ETAPA_RELATORIO,
            "Relatório epidemiológico"
        ),
        (AtualizacaoGalService.ETAPA_DOWNLOAD, "Download"),
        (
            AtualizacaoGalService.ETAPA_HISTORICO,
            "Histórico mensal"
        ),
        (
            AtualizacaoGalService.ETAPA_TESTE_SORO,
            "Banco TesteSORO"
        ),
        (AtualizacaoGalService.ETAPA_FINALIZACAO, "Finalização")
    )

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )

        self.atualizacao_service = AtualizacaoGalService()
        self.notificacoes_service = NotificacoesService()
        self._pagina_destruida = False
        self._polling_id = None
        self._concluida_hoje = False
        self._estados_etapas: dict[str, str] = {}
        self._mensagens_etapas: dict[str, str] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._criar_cabecalho()
        self._criar_conteudo()
        self._atualizar_estado_geral()
        self._atualizar_linha_tempo()
        self._atualizar_controles()

        self.bind("<Destroy>", self._ao_destruir)
        self._agendar_eventos()

    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=36,
            pady=(28, 12)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cabecalho,
            text="GAL",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Atualização semanal assistida do banco laboratorial "
                "de arbovírus."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _criar_conteudo(self):
        self.conteudo = ctk.CTkScrollableFrame(
            self,
            fg_color=Colors.BACKGROUND,
            corner_radius=0
        )
        self.conteudo.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(28, 20),
            pady=(0, 24)
        )
        self.conteudo.grid_columnconfigure(0, weight=1)

        self._criar_painel_estado()
        self._criar_painel_acoes()
        self._criar_painel_progresso()
        self._criar_painel_destinos()

    def _novo_painel(self, linha: int) -> ctk.CTkFrame:
        painel = ctk.CTkFrame(
            self.conteudo,
            fg_color=Colors.SURFACE,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=8,
            pady=(0, 14)
        )
        painel.grid_columnconfigure(0, weight=1)
        return painel

    def _criar_painel_estado(self):
        painel = self._novo_painel(0)
        painel.grid_columnconfigure(1, weight=1)

        icone = ctk.CTkFrame(
            painel,
            width=52,
            height=52,
            fg_color=Colors.BUTTON,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER
        )
        icone.grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(20, 15),
            pady=20
        )
        icone.grid_propagate(False)

        self.label_icone_estado = ctk.CTkLabel(
            icone,
            text="G",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=23,
                weight="bold"
            ),
            text_color=Colors.PRIMARY
        )
        self.label_icone_estado.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        self.label_estado = ctk.CTkLabel(
            painel,
            text="Verificando a situação do GAL...",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.label_estado.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 20),
            pady=(18, 2)
        )

        self.label_detalhe_estado = ctk.CTkLabel(
            painel,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=780
        )
        self.label_detalhe_estado.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 20),
            pady=2
        )

        self.label_periodo = ctk.CTkLabel(
            painel,
            text="",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_periodo.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 20),
            pady=(2, 18)
        )

    def _criar_painel_acoes(self):
        painel = self._novo_painel(1)
        painel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            painel,
            text="Atualizar banco semanal",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        ctk.CTkLabel(
            painel,
            text=(
                "O ArboHub abre o portal e preenche o relatório. "
                "Por segurança, login e CAPTCHA continuam manuais."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=850
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(0, 15)
        )

        botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        botoes.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        botoes.grid_columnconfigure((0, 1), weight=1)

        self.botao_iniciar = ctk.CTkButton(
            botoes,
            text="▶ Iniciar atualização",
            command=self._iniciar_atualizacao,
            height=40,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.botao_iniciar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 6)
        )

        self.botao_importar = ctk.CTkButton(
            botoes,
            text="Usar arquivo já baixado",
            command=self._selecionar_arquivo_manual,
            height=40,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.botao_importar.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=6
        )

        self.botao_cancelar = ctk.CTkButton(
            botoes,
            text="Cancelar",
            command=self._cancelar_atualizacao,
            width=110,
            height=40,
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
        )
        self.botao_cancelar.grid(
            row=0,
            column=2,
            sticky="e",
            padx=(6, 0)
        )

    def _criar_painel_progresso(self):
        painel = self._novo_painel(2)

        ctk.CTkLabel(
            painel,
            text="Progresso da atualização",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 4)
        )

        self.label_status_execucao = ctk.CTkLabel(
            painel,
            text="Aguardando o início da rotina.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=850
        )
        self.label_status_execucao.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )

        self.container_etapas = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        self.container_etapas.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        self.container_etapas.grid_columnconfigure(1, weight=1)

        self.componentes_etapas: dict[str, dict[str, object]] = {}

        for indice, (chave, titulo) in enumerate(self.ETAPAS):
            label_icone = ctk.CTkLabel(
                self.container_etapas,
                text="○",
                width=28,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=16,
                    weight="bold"
                ),
                text_color=Colors.TEXT_MUTED
            )
            label_icone.grid(
                row=indice,
                column=0,
                padx=(14, 8),
                pady=(10 if indice == 0 else 5,
                      10 if indice == len(self.ETAPAS) - 1 else 5)
            )

            label_titulo = ctk.CTkLabel(
                self.container_etapas,
                text=titulo,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=12,
                    weight="bold"
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w"
            )
            label_titulo.grid(
                row=indice,
                column=1,
                sticky="ew",
                padx=(0, 8),
                pady=(10 if indice == 0 else 5,
                      10 if indice == len(self.ETAPAS) - 1 else 5)
            )

            label_detalhe = ctk.CTkLabel(
                self.container_etapas,
                text="Aguardando",
                width=310,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=Colors.TEXT_MUTED,
                anchor="e"
            )
            label_detalhe.grid(
                row=indice,
                column=2,
                sticky="e",
                padx=(8, 14),
                pady=(10 if indice == 0 else 5,
                      10 if indice == len(self.ETAPAS) - 1 else 5)
            )

            self.componentes_etapas[chave] = {
                "icone": label_icone,
                "titulo": label_titulo,
                "detalhe": label_detalhe
            }

    def _criar_painel_destinos(self):
        painel = self._novo_painel(3)

        ctk.CTkLabel(
            painel,
            text="Destinos da atualização",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 12)
        )

        arquivos = self.atualizacao_service.arquivos_service
        destinos = (
            (
                "Histórico mensal",
                str(arquivos.pasta_historico_mes())
            ),
            (
                "Banco de teste",
                str(
                    arquivos.pasta_teste_soro
                    / "gal_sorotipo-TESTE"
                )
                + ".<extensão do relatório>"
            )
        )

        for indice, (rotulo, caminho) in enumerate(destinos, start=1):
            linha = ctk.CTkFrame(
                painel,
                fg_color=Colors.BACKGROUND,
                corner_radius=7,
                border_width=1,
                border_color=Colors.BORDER
            )
            linha.grid(
                row=indice,
                column=0,
                sticky="ew",
                padx=20,
                pady=(0, 10 if indice == 1 else 20)
            )
            linha.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                linha,
                text=rotulo.upper(),
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold"
                ),
                text_color=Colors.PRIMARY,
                anchor="w"
            ).grid(
                row=0,
                column=0,
                sticky="ew",
                padx=14,
                pady=(11, 2)
            )

            ctk.CTkLabel(
                linha,
                text=caminho,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=820
            ).grid(
                row=1,
                column=0,
                sticky="ew",
                padx=14,
                pady=(2, 11)
            )

    def _iniciar_atualizacao(self):
        if self.atualizacao_service.esta_em_execucao():
            return

        if self.atualizacao_service.esta_concluida_hoje():
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="GAL já atualizado",
                mensagem=(
                    "A atualização do GAL já foi concluída hoje. "
                    "O ArboHub bloqueou uma nova execução para "
                    "evitar duplicidade no histórico."
                ),
                tipo="informacao"
            )
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Iniciar atualização do GAL",
            mensagem=(
                "O navegador será aberto no portal oficial do GAL.\n\n"
                "Faça o login e preencha o CAPTCHA manualmente. "
                "Depois disso, não feche o navegador: o ArboHub "
                "continuará a rotina automaticamente."
            ),
            texto_confirmar="Abrir GAL",
            texto_cancelar="Agora não"
        )

        if not confirmou:
            return

        self._reiniciar_progresso()

        if self.atualizacao_service.iniciar():
            self.label_status_execucao.configure(
                text="Preparando a atualização semanal do GAL...",
                text_color=Colors.PRIMARY
            )
            self._atualizar_controles()

    def _selecionar_arquivo_manual(self):
        if self.atualizacao_service.esta_em_execucao():
            return

        if self.atualizacao_service.esta_concluida_hoje():
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="GAL já atualizado",
                mensagem=(
                    "A atualização do GAL já foi concluída hoje. "
                    "Nenhum arquivo foi substituído novamente."
                ),
                tipo="informacao"
            )
            return

        caminho = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Selecionar relatório baixado do GAL",
            filetypes=(
                ("Relatórios do GAL", "*.zip *.csv *.xlsx *.xls *.txt *.dbf"),
                ("Todos os arquivos", "*.*")
            )
        )

        if not caminho:
            return

        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Usar arquivo baixado",
            mensagem=(
                f"Arquivo selecionado:\n{Path(caminho).name}\n\n"
                "O ArboHub preservará o original no histórico mensal "
                "e atualizará o arquivo gal_sorotipo-TESTE."
            ),
            texto_confirmar="Processar arquivo",
            texto_cancelar="Cancelar"
        )

        if not confirmou:
            return

        self._reiniciar_progresso()

        if self.atualizacao_service.iniciar_importacao_manual(caminho):
            self.label_status_execucao.configure(
                text="Validando o arquivo selecionado...",
                text_color=Colors.PRIMARY
            )
            self._atualizar_controles()

    def _cancelar_atualizacao(self):
        if self.atualizacao_service.esta_em_execucao():
            self.atualizacao_service.cancelar()
            self.botao_cancelar.configure(state="disabled")

    def _agendar_eventos(self):
        if self._pagina_destruida:
            return

        self._polling_id = self.after(
            120,
            self._processar_eventos
        )

    def _processar_eventos(self):
        self._polling_id = None

        if self._pagina_destruida:
            return

        for evento in self.atualizacao_service.obter_eventos():
            self._tratar_evento(evento)

        self._atualizar_controles()
        self._agendar_eventos()

    def _tratar_evento(self, evento: dict):
        tipo = evento.get("tipo")
        mensagem = str(evento.get("mensagem", ""))

        if tipo == AtualizacaoGalService.EVENTO_ETAPA:
            etapa = str(evento.get("etapa", ""))
            self._estados_etapas[etapa] = str(
                evento.get("estado", "em_andamento")
            )
            self._mensagens_etapas[etapa] = mensagem
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            self._atualizar_linha_tempo()
            return

        if tipo == AtualizacaoGalService.EVENTO_STATUS:
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.PRIMARY
            )
            return

        if tipo == AtualizacaoGalService.EVENTO_CONCLUIDO:
            resultado = evento.get("resultado", {})
            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.SUCCESS
            )
            self._atualizar_estado_geral()
            self._atualizar_controles()
            self.notificacoes_service.tocar_conclusao()

            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="GAL atualizado",
                mensagem=(
                    "A atualização semanal foi concluída.\n\n"
                    f"Histórico:\n{resultado.get('arquivo_historico', '')}\n\n"
                    f"Banco de teste:\n{resultado.get('arquivo_teste', '')}"
                ),
                tipo="sucesso",
                texto_botao="Concluir"
            )
            return

        if tipo == AtualizacaoGalService.EVENTO_CANCELADO:
            etapa = str(evento.get("etapa", ""))

            if etapa:
                self._estados_etapas[etapa] = "cancelada"
                self._mensagens_etapas[etapa] = mensagem
                self._atualizar_linha_tempo()

            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.WARNING
            )
            return

        if tipo == AtualizacaoGalService.EVENTO_ERRO:
            etapa = str(evento.get("etapa", ""))

            if etapa:
                self._estados_etapas[etapa] = "erro"
                self._mensagens_etapas[etapa] = mensagem
                self._atualizar_linha_tempo()

            self.label_status_execucao.configure(
                text=mensagem,
                text_color=Colors.ERROR
            )
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Atualização do GAL não concluída",
                mensagem=(
                    f"{mensagem}\n\n"
                    "O banco não foi marcado como concluído. Se o "
                    "relatório já foi baixado, use o botão "
                    "'Usar arquivo já baixado'."
                ),
                tipo="erro"
            )

    def _reiniciar_progresso(self):
        self._estados_etapas.clear()
        self._mensagens_etapas.clear()
        self._atualizar_linha_tempo()

    def _atualizar_linha_tempo(self):
        for chave, _titulo in self.ETAPAS:
            estado = self._estados_etapas.get(chave, "aguardando")
            mensagem = self._mensagens_etapas.get(chave, "Aguardando")
            componentes = self.componentes_etapas[chave]

            if estado == "concluida":
                icone = "✓"
                cor = Colors.SUCCESS
            elif estado == "erro":
                icone = "×"
                cor = Colors.ERROR
            elif estado == "cancelada":
                icone = "!"
                cor = Colors.WARNING
            elif estado == "ignorada":
                icone = "—"
                cor = Colors.TEXT_MUTED
            elif estado in {"iniciada", "em_andamento"}:
                icone = "●"
                cor = Colors.PRIMARY
            else:
                icone = "○"
                cor = Colors.TEXT_MUTED

            componentes["icone"].configure(
                text=icone,
                text_color=cor
            )
            componentes["titulo"].configure(
                text_color=(
                    Colors.TEXT_PRIMARY
                    if estado != "aguardando"
                    else Colors.TEXT_SECONDARY
                )
            )
            componentes["detalhe"].configure(
                text=mensagem,
                text_color=cor
            )

    def _atualizar_estado_geral(self):
        hoje = date.today()
        estado = (
            self.atualizacao_service.dashboard_service
            .obter_estado_dia(hoje)
        )["gal"]
        self._concluida_hoje = bool(estado["concluido"])
        data_inicio, data_fim = (
            self.atualizacao_service.arquivos_service
            .intervalo_semanal(hoje)
        )

        self.label_periodo.configure(
            text=(
                "PERÍODO POR DATA DE LIBERAÇÃO: "
                f"{data_inicio.strftime('%d/%m/%Y')} a "
                f"{data_fim.strftime('%d/%m/%Y')}"
            )
        )

        if estado["concluido"]:
            self.label_estado.configure(
                text="Atualização concluída hoje",
                text_color=Colors.SUCCESS
            )
            self.label_detalhe_estado.configure(
                text=(
                    "O histórico mensal e o banco TesteSORO já "
                    "foram atualizados."
                )
            )
            self.label_icone_estado.configure(
                text="✓",
                text_color=Colors.SUCCESS
            )
        elif estado["programado"]:
            self.label_estado.configure(
                text="Atualização semanal pendente",
                text_color=Colors.WARNING
            )
            self.label_detalhe_estado.configure(
                text=(
                    "Hoje é o dia programado para baixar o relatório "
                    "do GAL."
                )
            )
            self.label_icone_estado.configure(
                text="G",
                text_color=Colors.WARNING
            )
        else:
            self.label_estado.configure(
                text="Atualização disponível",
                text_color=Colors.PRIMARY
            )
            self.label_detalhe_estado.configure(
                text=(
                    "A rotina obrigatória do GAL ocorre às "
                    "segundas-feiras, mas pode ser executada agora."
                )
            )
            self.label_icone_estado.configure(
                text="G",
                text_color=Colors.PRIMARY
            )

    def _atualizar_controles(self):
        executando = self.atualizacao_service.esta_em_execucao()
        concluida = self._concluida_hoje

        self.botao_iniciar.configure(
            state=("disabled" if executando or concluida else "normal"),
            text=(
                "● Atualização em andamento"
                if executando
                else (
                    "✓ Atualização concluída"
                    if concluida
                    else "▶ Iniciar atualização"
                )
            )
        )
        self.botao_importar.configure(
            state=("disabled" if executando or concluida else "normal")
        )
        self.botao_cancelar.configure(
            state=("normal" if executando else "disabled")
        )

    def _ao_destruir(self, event):
        if event.widget is not self:
            return

        self._pagina_destruida = True

        if self._polling_id is not None:
            try:
                self.after_cancel(self._polling_id)
            except Exception:
                pass
            self._polling_id = None

        if self.atualizacao_service.esta_em_execucao():
            self.atualizacao_service.cancelar()
