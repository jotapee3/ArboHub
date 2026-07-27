from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk

from app.gui.themes.colors import Colors
from app.services.checkpoint_service import CheckpointService


class SinanPage(ctk.CTkScrollableFrame):

    def __init__(self, master):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            orientation="vertical",
            scrollbar_fg_color=Colors.BACKGROUND,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.pasta_destino = None
        self.progresso_atual = 0

        self.checkpoint_service = CheckpointService()

        self.grid_columnconfigure(0, weight=1)

        self.criar_cabecalho()
        self.criar_painel_rotina()
        self.criar_painel_status()
        self.criar_painel_progresso()
        self.criar_painel_operacoes()

        self.atualizar_painel_rotina()

    def criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(34, 24)
        )

        titulo = ctk.CTkLabel(
            cabecalho,
            text="SINAN",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.pack(fill="x")

        descricao = ctk.CTkLabel(
            cabecalho,
            text="Gerenciamento e download das bases de dados do SINAN.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        descricao.pack(
            fill="x",
            pady=(5, 0)
        )

    def criar_painel_rotina(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40
        )

        painel.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            painel,
            text="Controle da rotina diária",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(20, 5)
        )

        descricao = ctk.CTkLabel(
            painel,
            text="Acompanhe a conclusão das etapas obrigatórias do SINAN.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        descricao.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 16)
        )

        self.label_checkpoint_obitos = ctk.CTkLabel(
            painel,
            text="○ Verificação de óbitos pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_checkpoint_obitos.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 8)
        )

        self.label_checkpoint_bases = ctk.CTkLabel(
            painel,
            text="○ Atualização das bases pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_checkpoint_bases.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 8)
        )

        self.label_rotina_completa = ctk.CTkLabel(
            painel,
            text="Rotina completa: pendente",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_rotina_completa.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22,
            pady=(2, 16)
        )

        divisor = ctk.CTkFrame(
            painel,
            height=1,
            fg_color=Colors.DIVIDER
        )
        divisor.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22
        )

        container_botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        container_botoes.grid(
            row=6,
            column=0,
            sticky="w",
            padx=22,
            pady=(16, 22)
        )

        self.botao_concluir_obitos = ctk.CTkButton(
            container_botoes,
            text="✓ Concluir verificação",
            command=self.concluir_verificacao_obitos,
            width=165,
            height=36,
            corner_radius=6,
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
        self.botao_concluir_obitos.pack(side="left")

        self.botao_concluir_bases = ctk.CTkButton(
            container_botoes,
            text="✓ Concluir atualização",
            command=self.concluir_atualizacao_bases,
            width=165,
            height=36,
            corner_radius=6,
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
        self.botao_concluir_bases.pack(
            side="left",
            padx=(10, 0)
        )

        self.botao_resetar = ctk.CTkButton(
            container_botoes,
            text="↻ Resetar",
            command=self.resetar_checkpoints,
            width=90,
            height=36,
            corner_radius=6,
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
        self.botao_resetar.pack(
            side="left",
            padx=(10, 0)
        )

    def criar_painel_status(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(20, 0)
        )

        painel.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            painel,
            text="Status da base",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(20, 4)
        )

        self.label_status_base = ctk.CTkLabel(
            painel,
            text="Nenhuma base disponível",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_status_base.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22
        )

        divisor = ctk.CTkFrame(
            painel,
            height=1,
            fg_color=Colors.DIVIDER
        )
        divisor.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=18
        )

        titulo_pasta = ctk.CTkLabel(
            painel,
            text="Pasta de destino",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo_pasta.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22
        )

        self.label_pasta = ctk.CTkLabel(
            painel,
            text="📁 Nenhuma pasta selecionada",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=620
        )
        self.label_pasta.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22,
            pady=(5, 16)
        )

        container_botoes = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        container_botoes.grid(
            row=5,
            column=0,
            sticky="w",
            padx=22,
            pady=(0, 22)
        )

        self.botao_selecionar_pasta = ctk.CTkButton(
            container_botoes,
            text="📁 Selecionar pasta",
            command=self.selecionar_pasta,
            width=160,
            height=38,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_selecionar_pasta.pack(side="left")

        self.botao_remover_pasta = ctk.CTkButton(
            container_botoes,
            text="✕ Remover seleção",
            command=self.remover_pasta,
            width=160,
            height=38,
            corner_radius=6,
            state="disabled",
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_remover_pasta.pack(
            side="left",
            padx=(10, 0)
        )

        self.botao_baixar = ctk.CTkButton(
            container_botoes,
            text="↓ Baixar bases",
            command=self.iniciar_download,
            width=145,
            height=38,
            corner_radius=6,
            state="disabled",
            fg_color=Colors.PRIMARY,
            hover_color=Colors.BUTTON_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            )
        )
        self.botao_baixar.pack(
            side="left",
            padx=(10, 0)
        )

    def criar_painel_progresso(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=40,
            pady=(20, 0)
        )

        painel.grid_columnconfigure(0, weight=1)

        cabecalho = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=22,
            pady=(18, 10)
        )

        cabecalho.grid_columnconfigure(0, weight=1)

        titulo = ctk.CTkLabel(
            cabecalho,
            text="Progresso",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.grid(
            row=0,
            column=0,
            sticky="w"
        )

        self.label_porcentagem = ctk.CTkLabel(
            cabecalho,
            text="0%",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="e"
        )
        self.label_porcentagem.grid(
            row=0,
            column=1,
            sticky="e"
        )

        self.barra_progresso = ctk.CTkProgressBar(
            painel,
            height=10,
            corner_radius=5,
            fg_color=Colors.BACKGROUND,
            progress_color=Colors.PRIMARY
        )
        self.barra_progresso.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=22
        )
        self.barra_progresso.set(0)

        self.label_progresso = ctk.CTkLabel(
            painel,
            text="Aguardando início do download.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_progresso.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(10, 18)
        )

    def criar_painel_operacoes(self):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=40,
            pady=(20, 30)
        )

        titulo = ctk.CTkLabel(
            painel,
            text="Últimas operações",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=16,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        titulo.pack(
            fill="x",
            padx=22,
            pady=(18, 6)
        )

        self.label_operacao = ctk.CTkLabel(
            painel,
            text="Nenhuma operação realizada.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        )
        self.label_operacao.pack(
            fill="x",
            padx=22,
            pady=(0, 18)
        )

    def selecionar_pasta(self):
        pasta_selecionada = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Selecione a pasta de destino"
        )

        if not pasta_selecionada:
            return

        self.pasta_destino = pasta_selecionada

        self.label_pasta.configure(
            text=f"📁 {self.pasta_destino}",
            text_color=Colors.TEXT_SECONDARY
        )

        self.botao_remover_pasta.configure(
            state="normal"
        )

        self.botao_baixar.configure(
            state="normal",
            text="↓ Baixar bases"
        )

        self.label_progresso.configure(
            text="Pasta selecionada. A atualização pode ser iniciada."
        )

        self.registrar_operacao(
            "Pasta de destino selecionada."
        )

    def remover_pasta(self):
        if self.pasta_destino is None:
            return

        self.pasta_destino = None
        self.progresso_atual = 0

        self.label_pasta.configure(
            text="📁 Nenhuma pasta selecionada",
            text_color=Colors.TEXT_MUTED
        )

        self.botao_remover_pasta.configure(
            state="disabled"
        )

        self.botao_baixar.configure(
            state="disabled",
            text="↓ Baixar bases"
        )

        self.barra_progresso.set(0)

        self.label_porcentagem.configure(
            text="0%"
        )

        self.label_progresso.configure(
            text="Seleção removida. Escolha uma pasta de destino."
        )

        self.registrar_operacao(
            "Seleção da pasta de destino removida."
        )

    def iniciar_download(self):
        if self.pasta_destino is None:
            return

        self.progresso_atual = 0

        self.botao_selecionar_pasta.configure(
            state="disabled"
        )

        self.botao_remover_pasta.configure(
            state="disabled"
        )

        self.botao_baixar.configure(
            state="disabled",
            text="↓ Baixando..."
        )

        self.label_status_base.configure(
            text="Download em andamento",
            text_color=Colors.PRIMARY
        )

        self.label_progresso.configure(
            text="Preparando o download da base do SINAN..."
        )

        self.registrar_operacao(
            "Download das bases iniciado."
        )

        self.barra_progresso.set(0)
        self.label_porcentagem.configure(text="0%")

        self.simular_progresso()

    def simular_progresso(self):
        self.progresso_atual += 5

        valor_barra = self.progresso_atual / 100

        self.barra_progresso.set(valor_barra)

        self.label_porcentagem.configure(
            text=f"{self.progresso_atual}%"
        )

        if self.progresso_atual < 100:
            self.after(
                100,
                self.simular_progresso
            )
            return

        self.finalizar_download()

    def finalizar_download(self):
        self.label_status_base.configure(
            text="Base disponível",
            text_color=Colors.SUCCESS
        )

        self.label_progresso.configure(
            text="Download concluído com sucesso."
        )

        self.botao_selecionar_pasta.configure(
            state="normal"
        )

        self.botao_remover_pasta.configure(
            state="normal"
        )

        self.botao_baixar.configure(
            state="normal",
            text="↻ Baixar novamente"
        )

        # Quando a atualização termina com sucesso,
        # o checkpoint é marcado automaticamente.
        self.checkpoint_service.marcar_atualizacao_bases()

        self.atualizar_painel_rotina()

        self.registrar_operacao(
            "Bases do SINAN atualizadas com sucesso."
        )

    def concluir_verificacao_obitos(self):
        self.checkpoint_service.marcar_verificacao_obitos()

        self.atualizar_painel_rotina()

        self.registrar_operacao(
            "Verificação de óbitos marcada como concluída."
        )

    def concluir_atualizacao_bases(self):
        self.checkpoint_service.marcar_atualizacao_bases()

        self.atualizar_painel_rotina()

        self.registrar_operacao(
            "Atualização das bases marcada como concluída."
        )

    def resetar_checkpoints(self):
        self.checkpoint_service.resetar_rotina()

        self.atualizar_painel_rotina()

        self.label_status_base.configure(
            text="Nenhuma base disponível",
            text_color=Colors.TEXT_SECONDARY
        )

        self.barra_progresso.set(0)

        self.label_porcentagem.configure(
            text="0%"
        )

        self.label_progresso.configure(
            text="Aguardando início do download."
        )

        self.registrar_operacao(
            "Checkpoints do dia foram resetados."
        )

    def atualizar_painel_rotina(self):
        rotina = self.checkpoint_service.obter_rotina()

        if rotina["verificacao_obitos"]:
            horario = self.formatar_horario(
                rotina["verificacao_obitos_em"]
            )

            self.label_checkpoint_obitos.configure(
                text=(
                    "✓ Verificação de óbitos concluída"
                    f"{horario}"
                ),
                text_color=Colors.SUCCESS
            )

            self.botao_concluir_obitos.configure(
                text="✓ Verificação concluída",
                state="disabled"
            )
        else:
            self.label_checkpoint_obitos.configure(
                text="○ Verificação de óbitos pendente",
                text_color=Colors.TEXT_SECONDARY
            )

            self.botao_concluir_obitos.configure(
                text="✓ Concluir verificação",
                state="normal"
            )

        if rotina["atualizacao_bases"]:
            horario = self.formatar_horario(
                rotina["atualizacao_bases_em"]
            )

            self.label_checkpoint_bases.configure(
                text=(
                    "✓ Atualização das bases concluída"
                    f"{horario}"
                ),
                text_color=Colors.SUCCESS
            )

            self.botao_concluir_bases.configure(
                text="✓ Atualização concluída",
                state="disabled"
            )
        else:
            self.label_checkpoint_bases.configure(
                text="○ Atualização das bases pendente",
                text_color=Colors.TEXT_SECONDARY
            )

            self.botao_concluir_bases.configure(
                text="✓ Concluir atualização",
                state="normal"
            )

        if rotina["rotina_concluida"]:
            self.label_rotina_completa.configure(
                text="✓ Rotina completa: concluída",
                text_color=Colors.SUCCESS
            )
        else:
            self.label_rotina_completa.configure(
                text="○ Rotina completa: pendente",
                text_color=Colors.TEXT_MUTED
            )

    def formatar_horario(self, horario_iso):
        if not horario_iso:
            return ""

        horario = datetime.fromisoformat(
            horario_iso
        ).strftime("%H:%M")

        return f" às {horario}"

    def registrar_operacao(self, mensagem):
        horario = datetime.now().strftime("%H:%M:%S")

        self.label_operacao.configure(
            text=f"{horario} — {mensagem}"
        )