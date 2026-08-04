from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app.gui.components.arbohub_dialog import (
    mostrar_dialogo_arbohub,
    solicitar_confirmacao_arbohub
)
from app.gui.themes.colors import Colors
from app.services.configuracoes_service import (
    ConfiguracoesService
)
from app.services.manutencao_service import (
    ManutencaoService,
    PreviaResetBases
)


class ConfiguracoesPage(ctk.CTkScrollableFrame):
    """
    Preferências gerais do ArboHub.

    As preferências operacionais desta versão não armazenam
    credenciais e não acessam o conteúdo interno dos DBFs.
    """

    PAGINAS = {
        "Início": "inicio",
        "SINAN": "sinan",
        "GAL": "gal"
    }

    PAGINAS_INVERSAS = {
        valor: chave
        for chave, valor in PAGINAS.items()
    }

    INTERVALOS = {
        "30 segundos": 30,
        "60 segundos": 60,
        "2 minutos": 120,
        "5 minutos": 300
    }

    INTERVALOS_INVERSOS = {
        valor: chave
        for chave, valor in INTERVALOS.items()
    }

    INTERVALOS_EXPORTACAO = {
        "10 segundos": 10,
        "15 segundos": 15,
        "30 segundos": 30,
        "60 segundos": 60
    }

    AVISOS_INICIAIS = {
        "1 minuto": 60,
        "2 minutos": 120,
        "3 minutos": 180
    }

    AVISOS_LENTOS = {
        "5 minutos": 300,
        "7 minutos": 420,
        "10 minutos": 600
    }

    AVISOS_REFORCADOS = {
        "10 minutos": 600,
        "12 minutos": 720,
        "15 minutos": 900
    }

    LIMITES_EXPORTACAO = {
        "15 minutos": 900,
        "20 minutos": 1200,
        "30 minutos": 1800,
        "45 minutos": 2700
    }

    CAMINHOS_OPERACIONAIS = (
        (
            "historico_sinan",
            "Histórico do SINAN",
            (
                "Raiz usada para arquivar os ZIPs por ano, "
                "agravo e mês."
            )
        ),
        (
            "teste_ab1",
            "Teste AB1",
            (
                "Destino do banco anual de Dengue usado nos "
                "testes do setor."
            )
        ),
        (
            "teste_ab2",
            "Teste AB2",
            (
                "Destino do banco anual de Chikungunya usado "
                "nos testes do setor."
            )
        ),
        (
            "bancos_atuais",
            "Bancos_Atuais",
            (
                "Destino da dupla oficial dengue_AAAA.dbf e "
                "chiku_AAAA.dbf."
            )
        )
    )

    def __init__(
        self,
        master,
        ao_salvar=None
    ):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.ao_salvar = ao_salvar
        self.configuracoes_service = (
            ConfiguracoesService()
        )
        self.manutencao_service = (
            ManutencaoService()
        )
        self.configuracoes = (
            self.configuracoes_service.carregar()
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self._criar_variaveis()
        self._criar_cabecalho()
        self._criar_secao_geral()
        self._criar_secao_dashboard()
        self._criar_secao_caminhos_operacionais()
        self._criar_secao_exportacao_parcial()
        self._criar_secao_manutencao()
        self._criar_secao_sobre()
        self._criar_rodape()

    def _criar_variaveis(self):
        geral = self.configuracoes[
            "geral"
        ]
        dashboard = self.configuracoes[
            "dashboard"
        ]
        operacional = self.configuracoes[
            "operacional"
        ]
        caminhos = operacional[
            "caminhos"
        ]
        exportacao = operacional[
            "exportacao"
        ]

        self.pagina_inicial_var = ctk.StringVar(
            value=self.PAGINAS_INVERSAS.get(
                geral["pagina_inicial"],
                "Início"
            )
        )
        self.abrir_maximizado_var = ctk.BooleanVar(
            value=geral[
                "abrir_maximizado"
            ]
        )
        self.dashboard_automatico_var = ctk.BooleanVar(
            value=dashboard[
                "atualizacao_automatica"
            ]
        )
        self.intervalo_dashboard_var = ctk.StringVar(
            value=self.INTERVALOS_INVERSOS.get(
                dashboard[
                    "intervalo_segundos"
                ],
                "60 segundos"
            )
        )

        self.caminhos_vars = {
            chave: ctk.StringVar(
                value=str(
                    caminhos[chave]
                )
            )
            for chave, _, _ in self.CAMINHOS_OPERACIONAIS
        }
        self.status_caminhos: dict[
            str,
            ctk.CTkLabel
        ] = {}

        self.intervalo_exportacao_var = ctk.StringVar(
            value=self._rotulo_por_valor(
                self.INTERVALOS_EXPORTACAO,
                exportacao[
                    "intervalo_consulta_segundos"
                ],
                "15 segundos"
            )
        )
        self.aviso_inicial_var = ctk.StringVar(
            value=self._rotulo_por_valor(
                self.AVISOS_INICIAIS,
                exportacao[
                    "aviso_inicial_segundos"
                ],
                "1 minuto"
            )
        )
        self.aviso_lento_var = ctk.StringVar(
            value=self._rotulo_por_valor(
                self.AVISOS_LENTOS,
                exportacao[
                    "aviso_lento_segundos"
                ],
                "5 minutos"
            )
        )
        self.aviso_reforcado_var = ctk.StringVar(
            value=self._rotulo_por_valor(
                self.AVISOS_REFORCADOS,
                exportacao[
                    "aviso_reforcado_segundos"
                ],
                "10 minutos"
            )
        )
        self.tempo_limite_exportacao_var = ctk.StringVar(
            value=self._rotulo_por_valor(
                self.LIMITES_EXPORTACAO,
                exportacao[
                    "tempo_limite_segundos"
                ],
                "20 minutos"
            )
        )


    def _criar_cabecalho(self):
        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(30, 18)
        )
        cabecalho.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            cabecalho,
            text="Configurações",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=30,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew"
        )

        ctk.CTkLabel(
            cabecalho,
            text=(
                "Personalize preferências gerais sem alterar "
                "as rotinas operacionais."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(5, 0)
        )

        ctk.CTkButton(
            cabecalho,
            text="Salvar alterações",
            command=self.salvar_configuracoes,
            width=155,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="e"
        )

    def _criar_secao_geral(self):
        painel = self._criar_painel(
            linha=1,
            titulo="Geral",
            descricao=(
                "Defina como o ArboHub deve abrir nesta conta "
                "do Windows."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_geral"
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Página inicial",
            descricao=(
                "Tela exibida ao abrir o aplicativo."
            ),
            variavel=self.pagina_inicial_var,
            valores=list(
                self.PAGINAS.keys()
            )
        )

        self._criar_opcao_switch(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Abrir maximizado",
            descricao=(
                "Usa toda a área disponível da tela."
            ),
            variavel=self.abrir_maximizado_var
        )

    def _criar_secao_dashboard(self):
        painel = self._criar_painel(
            linha=2,
            titulo="Dashboard",
            descricao=(
                "Controle a atualização dos indicadores da aba Início."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_dashboard"
        )

        self._criar_opcao_switch(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Atualização automática",
            descricao=(
                "Mantém os indicadores atualizados sem ação manual."
            ),
            variavel=self.dashboard_automatico_var
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Intervalo de atualização",
            descricao=(
                "Tempo entre cada atualização automática."
            ),
            variavel=self.intervalo_dashboard_var,
            valores=list(
                self.INTERVALOS.keys()
            )
        )

        aviso = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        aviso.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        aviso.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkLabel(
            aviso,
            text="i",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.INFO
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "O botão Atualizar da aba Início continuará funcionando "
                "mesmo quando a atualização automática estiver desativada."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=720
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=12
        )

    def _criar_secao_caminhos_operacionais(self):
        painel = self._criar_painel(
            linha=3,
            titulo="Pastas operacionais",
            descricao=(
                "Defina os destinos usados pelo fluxo de Bases. "
                "O ArboHub testa leitura e gravação antes de salvar."
            )
        )

        aviso = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        aviso.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 12)
        )
        aviso.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkLabel(
            aviso,
            text="i",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.INFO
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "Nenhum conteúdo de DBF é lido durante o teste. "
                "Um arquivo temporário pequeno é criado e removido "
                "imediatamente para confirmar a permissão de gravação."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=760
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=12
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        grade.grid_columnconfigure(
            0,
            weight=1
        )

        for linha, (
            chave,
            titulo,
            descricao
        ) in enumerate(
            self.CAMINHOS_OPERACIONAIS
        ):
            self._criar_campo_caminho(
                master=grade,
                linha=linha,
                chave=chave,
                titulo=titulo,
                descricao=descricao
            )

    def _criar_campo_caminho(
        self,
        master,
        linha: int,
        chave: str,
        titulo: str,
        descricao: str
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=0,
            sticky="ew",
            pady=(
                (0, 6)
                if linha == 0
                else 6
            )
        )
        card.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(13, 3)
        )

        ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=760
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14
        )

        campo = ctk.CTkEntry(
            card,
            textvariable=self.caminhos_vars[
                chave
            ],
            height=36,
            corner_radius=6,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            )
        )
        campo.grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(10, 8)
        )
        campo.bind(
            "<KeyRelease>",
            lambda _evento, item=chave:
                self._marcar_caminho_nao_testado(
                    item
                ),
            add="+"
        )

        barra_acoes = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        barra_acoes.grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14
        )
        barra_acoes.grid_columnconfigure(
            3,
            weight=1
        )

        for coluna, (
            texto,
            comando
        ) in enumerate(
            (
                (
                    "Selecionar",
                    lambda item=chave:
                        self._selecionar_pasta_operacional(
                            item
                        )
                ),
                (
                    "Testar",
                    lambda item=chave:
                        self._testar_caminho_operacional(
                            item
                        )
                ),
                (
                    "Abrir",
                    lambda item=chave:
                        self._abrir_caminho_operacional(
                            item
                        )
                )
            )
        ):
            ctk.CTkButton(
                barra_acoes,
                text=texto,
                command=comando,
                width=92,
                height=30,
                corner_radius=6,
                fg_color=Colors.BUTTON,
                hover_color=Colors.BUTTON_HOVER,
                border_width=1,
                border_color=Colors.BUTTON_BORDER,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold"
                )
            ).grid(
                row=0,
                column=coluna,
                padx=(
                    (0, 6)
                    if coluna == 0
                    else 6
                )
            )

        status = ctk.CTkLabel(
            card,
            text="○ Não testado nesta sessão",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        status.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14,
            pady=(8, 13)
        )
        self.status_caminhos[
            chave
        ] = status

    def _criar_secao_exportacao_parcial(self):
        painel = self._criar_painel(
            linha=4,
            titulo="Exportação parcial",
            descricao=(
                "Ajuste somente os tempos de acompanhamento do "
                "SINAN. As proteções do fluxo permanecem obrigatórias."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 12)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_exportacao"
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Intervalo de consulta",
            descricao=(
                "Tempo entre as atualizações da tabela do SINAN."
            ),
            variavel=self.intervalo_exportacao_var,
            valores=list(
                self.INTERVALOS_EXPORTACAO.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Primeiro aviso",
            descricao=(
                "Informa que o processamento pode levar alguns minutos."
            ),
            variavel=self.aviso_inicial_var,
            valores=list(
                self.AVISOS_INICIAIS.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=1,
            coluna=0,
            titulo="Aviso de lentidão",
            descricao=(
                "Sinaliza que uma ou mais exportações seguem pendentes."
            ),
            variavel=self.aviso_lento_var,
            valores=list(
                self.AVISOS_LENTOS.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=1,
            coluna=1,
            titulo="Aviso reforçado",
            descricao=(
                "Reforça que o tempo de resposta está acima do habitual."
            ),
            variavel=self.aviso_reforcado_var,
            valores=list(
                self.AVISOS_REFORCADOS.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=2,
            coluna=0,
            titulo="Tempo máximo automático",
            descricao=(
                "Após esse limite, libera a correção manual da pendência."
            ),
            variavel=self.tempo_limite_exportacao_var,
            valores=list(
                self.LIMITES_EXPORTACAO.keys()
            )
        )

        protecoes = self._criar_card_opcao(
            master=grade,
            linha=2,
            coluna=1,
            titulo="Proteções do fluxo",
            descricao=(
                "Regras obrigatórias para evitar perda ou troca "
                "de arquivos."
            )
        )

        ctk.CTkLabel(
            protecoes,
            text=(
                "✓ Processar o agravo disponível imediatamente\n"
                "✓ Continuar acompanhando o agravo pendente\n"
                "✓ Validar o ZIP antes da correção manual"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.SUCCESS,
            anchor="w",
            justify="left"
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

        aviso = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7
        )
        aviso.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        aviso.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkLabel(
            aviso,
            text="!",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.WARNING
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "Os avisos precisam permanecer em ordem crescente "
                "e todos devem ocorrer antes do tempo máximo. "
                "Configurações incompatíveis não serão salvas."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=720
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=12
        )

    def _criar_secao_manutencao(self):
        painel = self._criar_painel(
            linha=5,
            titulo="Testes e manutenção",
            descricao=(
                "Ferramentas locais para repetir testes e acessar "
                "pastas técnicas do ArboHub."
            )
        )

        aviso = ctk.CTkFrame(
            painel,
            fg_color=Colors.SURFACE_HOVER,
            corner_radius=7,
            border_width=1,
            border_color=Colors.BORDER
        )
        aviso.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 12)
        )
        aviso.grid_columnconfigure(
            1,
            weight=1
        )

        ctk.CTkLabel(
            aviso,
            text="!",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=15,
                weight="bold"
            ),
            text_color=Colors.WARNING
        ).grid(
            row=0,
            column=0,
            padx=(12, 6),
            pady=12
        )

        ctk.CTkLabel(
            aviso,
            text=(
                "O reset completo atua somente sobre a rotina de "
                "Bases do dia atual. Um backup é criado antes de "
                "qualquer alteração."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=720
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=12
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color="transparent"
        )
        grade.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_manutencao"
        )

        self._criar_acao_manutencao(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Resetar rotina de Bases de hoje",
            descricao=(
                "Limpa o estado local para testar novamente desde "
                "a criação das solicitações."
            ),
            texto_botao="Revisar e resetar",
            comando=self.iniciar_reset_bases,
            destaque=True
        )

        self._criar_acao_manutencao(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Backups de reset",
            descricao=(
                "Abre os backups automáticos e os manifestos das "
                "operações realizadas."
            ),
            texto_botao="Abrir pasta de backups",
            comando=self.abrir_pasta_backups
        )

        self._criar_acao_manutencao(
            master=grade,
            linha=1,
            coluna=0,
            titulo="Arquivos temporários",
            descricao=(
                "Abre o staging privado usado durante downloads e "
                "validações das exportações."
            ),
            texto_botao="Abrir pasta temporária",
            comando=self.abrir_pasta_temporaria
        )

        self._criar_acao_manutencao(
            master=grade,
            linha=1,
            coluna=1,
            titulo="Dados do ArboHub",
            descricao=(
                "Abre a pasta do banco operacional e dos backups "
                "locais do projeto."
            ),
            texto_botao="Abrir pasta de dados",
            comando=self.abrir_pasta_dados
        )

    def _criar_acao_manutencao(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        texto_botao: str,
        comando,
        destaque: bool = False
    ):
        card = self._criar_card_opcao(
            master=master,
            linha=linha,
            coluna=coluna,
            titulo=titulo,
            descricao=descricao
        )

        ctk.CTkButton(
            card,
            text=texto_botao,
            command=comando,
            height=34,
            corner_radius=6,
            fg_color=(
                Colors.WARNING
                if destaque
                else Colors.BUTTON
            ),
            hover_color=(
                "#B7811C"
                if destaque
                else Colors.BUTTON_HOVER
            ),
            border_width=(
                0
                if destaque
                else 1
            ),
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

    def iniciar_reset_bases(self):
        try:
            previa = (
                self.manutencao_service
                .gerar_previa_reset_bases()
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível gerar a prévia",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        if not previa.possui_estado_local:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Bases já estão limpas",
                mensagem=(
                    "Não foram encontrados lotes, solicitações, "
                    "ZIPs históricos, staging ou checkpoint de "
                    "Bases para o dia atual.\n\n"
                    "A próxima execução já será tratada como uma "
                    "rotina nova."
                ),
                tipo="informacao",
                texto_botao="Entendi"
            )
            return

        dialogo = ConfirmacaoResetBasesDialog(
            master=self.winfo_toplevel(),
            previa=previa,
            manutencao_service=(
                self.manutencao_service
            )
        )
        frase = dialogo.mostrar()

        if frase is None:
            return

        try:
            resultado = (
                self.manutencao_service
                .executar_reset_bases(
                    frase_confirmacao=frase,
                    data_referencia=(
                        previa.data_referencia
                    )
                )
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Reset não concluído",
                mensagem=(
                    "O estado anterior foi restaurado sempre que "
                    "possível.\n\n"
                    f"Detalhe técnico: {erro}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Bases preparadas para novo teste",
            mensagem=(
                "O estado local da rotina de Bases de hoje foi "
                "resetado com segurança.\n\n"
                "Consulta, Relatórios, Teste AB1, Teste AB2 e "
                "Bancos_Atuais foram preservados.\n\n"
                "Backup criado em:\n"
                f"{resultado['pasta_backup']}\n\n"
                "Ao abrir SINAN → Bases, a próxima execução "
                "começará pela criação de novas solicitações."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def abrir_pasta_backups(self):
        self._executar_acao_manutencao(
            self.manutencao_service
            .abrir_pasta_backups,
            "Não foi possível abrir a pasta de backups"
        )

    def abrir_pasta_temporaria(self):
        self._executar_acao_manutencao(
            self.manutencao_service
            .abrir_pasta_temporaria,
            "Não foi possível abrir a pasta temporária"
        )

    def abrir_pasta_dados(self):
        self._executar_acao_manutencao(
            self.manutencao_service
            .abrir_pasta_dados,
            "Não foi possível abrir a pasta de dados"
        )

    def _executar_acao_manutencao(
        self,
        acao,
        titulo_erro: str
    ):
        try:
            acao()
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo=titulo_erro,
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )

    def _rotulo_por_valor(
        self,
        opcoes: dict[str, int],
        valor: int,
        padrao: str
    ) -> str:
        for rotulo, numero in opcoes.items():
            if numero == valor:
                return rotulo

        return padrao

    def _selecionar_pasta_operacional(
        self,
        chave: str
    ):
        atual = Path(
            self.caminhos_vars[
                chave
            ].get()
        ).expanduser()

        if atual.exists() and atual.is_dir():
            inicial = atual
        elif atual.parent.exists():
            inicial = atual.parent
        else:
            inicial = Path.home()

        selecionada = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title=(
                "Selecionar "
                + self.configuracoes_service
                .ROTULOS_CAMINHOS[chave]
            ),
            initialdir=str(inicial),
            mustexist=True
        )

        if not selecionada:
            return

        self.caminhos_vars[
            chave
        ].set(
            selecionada
        )
        self._marcar_caminho_nao_testado(
            chave
        )

    def _marcar_caminho_nao_testado(
        self,
        chave: str
    ):
        status = self.status_caminhos.get(
            chave
        )

        if status is None:
            return

        status.configure(
            text="○ Alterado — teste necessário",
            text_color=Colors.TEXT_MUTED
        )

    def _testar_caminho_operacional(
        self,
        chave: str
    ) -> bool:
        resultado = (
            self.configuracoes_service
            .testar_pasta_operacional(
                chave=chave,
                caminho=self.caminhos_vars[
                    chave
                ].get(),
                testar_escrita=True
            )
        )

        status = self.status_caminhos.get(
            chave
        )

        if resultado["valido"]:
            self.caminhos_vars[
                chave
            ].set(
                str(
                    resultado["caminho"]
                )
            )

            if status is not None:
                status.configure(
                    text="✓ Leitura e gravação confirmadas",
                    text_color=Colors.SUCCESS
                )

            return True

        if status is not None:
            status.configure(
                text="× Caminho inválido ou indisponível",
                text_color=Colors.ERROR
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Não foi possível validar a pasta",
            mensagem=str(
                resultado["mensagem"]
            ),
            tipo="erro",
            texto_botao="Entendi"
        )
        return False

    def _abrir_caminho_operacional(
        self,
        chave: str
    ):
        resultado = (
            self.configuracoes_service
            .testar_pasta_operacional(
                chave=chave,
                caminho=self.caminhos_vars[
                    chave
                ].get(),
                testar_escrita=False
            )
        )

        if not resultado["valido"]:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível abrir a pasta",
                mensagem=str(
                    resultado["mensagem"]
                ),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        if not hasattr(
            os,
            "startfile"
        ):
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Abertura não suportada",
                mensagem=(
                    "Este recurso está disponível na instalação "
                    "do ArboHub para Windows."
                ),
                tipo="informacao",
                texto_botao="Entendi"
            )
            return

        try:
            os.startfile(
                str(
                    resultado["caminho"]
                )
            )
        except OSError as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível abrir a pasta",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )

    def _validar_caminhos_para_salvar(
        self
    ) -> dict[str, str]:
        caminhos = {
            chave: self.caminhos_vars[
                chave
            ].get()
            for chave, _, _ in self.CAMINHOS_OPERACIONAIS
        }

        validados = (
            self.configuracoes_service
            .validar_caminhos_operacionais(
                caminhos=caminhos,
                testar_escrita=True
            )
        )

        for chave, caminho in validados.items():
            self.caminhos_vars[
                chave
            ].set(
                caminho
            )

            status = self.status_caminhos.get(
                chave
            )

            if status is not None:
                status.configure(
                    text="✓ Leitura e gravação confirmadas",
                    text_color=Colors.SUCCESS
                )

        return validados

    def _obter_configuracao_exportacao(
        self
    ) -> dict[str, object]:
        exportacao = {
            "intervalo_consulta_segundos":
                self.INTERVALOS_EXPORTACAO[
                    self.intervalo_exportacao_var.get()
                ],
            "aviso_inicial_segundos":
                self.AVISOS_INICIAIS[
                    self.aviso_inicial_var.get()
                ],
            "aviso_lento_segundos":
                self.AVISOS_LENTOS[
                    self.aviso_lento_var.get()
                ],
            "aviso_reforcado_segundos":
                self.AVISOS_REFORCADOS[
                    self.aviso_reforcado_var.get()
                ],
            "tempo_limite_segundos":
                self.LIMITES_EXPORTACAO[
                    self.tempo_limite_exportacao_var.get()
                ],
            "processar_disponivel_imediatamente": True,
            "continuar_acompanhando_pendente": True,
            "permitir_correcao_manual": True
        }

        if not (
            exportacao["aviso_inicial_segundos"]
            < exportacao["aviso_lento_segundos"]
            < exportacao["aviso_reforcado_segundos"]
            < exportacao["tempo_limite_segundos"]
        ):
            raise ValueError(
                "Os avisos precisam permanecer em ordem crescente "
                "e ocorrer antes do tempo máximo automático."
            )

        return exportacao

    def _criar_secao_sobre(self):
        painel = self._criar_painel(
            linha=6,
            titulo="Sobre",
            descricao=(
                "Informações desta instalação do ArboHub."
            )
        )

        grade = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        grade.grid_columnconfigure(
            1,
            weight=1
        )

        raiz_projeto = Path(
            __file__
        ).resolve().parents[3]

        informacoes = (
            (
                "Aplicativo",
                "ArboHub v0.5"
            ),
            (
                "Finalidade",
                (
                    "Plataforma de apoio à vigilância em "
                    "antropozoonoses"
                )
            ),
            (
                "Configurações locais",
                str(
                    self.configuracoes_service
                    .caminho_arquivo
                )
            ),
            (
                "Banco operacional",
                str(
                    raiz_projeto
                    / "data"
                    / "arbohub.db"
                )
            )
        )

        for linha, (rotulo, valor) in enumerate(
            informacoes
        ):
            ctk.CTkLabel(
                grade,
                text=rotulo,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11,
                    weight="bold"
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).grid(
                row=linha,
                column=0,
                sticky="w",
                padx=(16, 18),
                pady=(
                    (14, 7)
                    if linha == 0
                    else (
                        (7, 14)
                        if linha == len(informacoes) - 1
                        else 7
                    )
                )
            )

            ctk.CTkLabel(
                grade,
                text=valor,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=690
            ).grid(
                row=linha,
                column=1,
                sticky="ew",
                padx=(0, 16),
                pady=(
                    (14, 7)
                    if linha == 0
                    else (
                        (7, 14)
                        if linha == len(informacoes) - 1
                        else 7
                    )
                )
            )

    def _criar_rodape(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        rodape.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 30)
        )
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkButton(
            rodape,
            text="Restaurar padrões",
            command=self.restaurar_padroes,
            width=155,
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
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkButton(
            rodape,
            text="Salvar alterações",
            command=self.salvar_configuracoes,
            width=170,
            height=38,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    def _criar_painel(
        self,
        linha: int,
        titulo: str,
        descricao: str
    ):
        painel = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        painel.grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 16)
        )
        painel.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            painel,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=17,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=(18, 3)
        )

        ctk.CTkLabel(
            painel,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 12)
        )

        return painel

    def _criar_card_opcao(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str
    ):
        card = ctk.CTkFrame(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=coluna,
            sticky="nsew",
            padx=(
                (0, 6)
                if coluna == 0
                else (6, 0)
            ),
            pady=6
        )
        card.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(13, 3)
        )

        ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=345
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14
        )

        return card

    def _criar_opcao_menu(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        variavel,
        valores: list[str]
    ):
        card = self._criar_card_opcao(
            master,
            linha,
            coluna,
            titulo,
            descricao
        )

        ctk.CTkOptionMenu(
            card,
            variable=variavel,
            values=valores,
            height=34,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            button_color=Colors.BUTTON,
            button_hover_color=Colors.BUTTON_HOVER,
            dropdown_fg_color=Colors.SURFACE,
            dropdown_hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

    def _criar_opcao_switch(
        self,
        master,
        linha: int,
        coluna: int,
        titulo: str,
        descricao: str,
        variavel
    ):
        card = self._criar_card_opcao(
            master,
            linha,
            coluna,
            titulo,
            descricao
        )

        ctk.CTkSwitch(
            card,
            text="Ativado",
            variable=variavel,
            onvalue=True,
            offvalue=False,
            progress_color=Colors.PRIMARY,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=14,
            pady=(10, 16)
        )

    def salvar_configuracoes(self):
        try:
            caminhos = (
                self._validar_caminhos_para_salvar()
            )
            exportacao = (
                self._obter_configuracao_exportacao()
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Configurações não salvas",
                mensagem=(
                    "Revise as pastas e os tempos operacionais.\n\n"
                    f"Detalhe: {erro}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        configuracoes = {
            "versao": 3,
            "geral": {
                "pagina_inicial": self.PAGINAS[
                    self.pagina_inicial_var.get()
                ],
                "abrir_maximizado": (
                    self.abrir_maximizado_var.get()
                )
            },
            "dashboard": {
                "atualizacao_automatica": (
                    self.dashboard_automatico_var.get()
                ),
                "intervalo_segundos": self.INTERVALOS[
                    self.intervalo_dashboard_var.get()
                ]
            },
            "operacional": {
                "caminhos": caminhos,
                "exportacao": exportacao
            }
        }

        self.configuracoes = (
            self.configuracoes_service.salvar(
                configuracoes
            )
        )
        self.manutencao_service = (
            ManutencaoService()
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Configurações salvas",
            mensagem=(
                "As preferências foram salvas para esta conta do "
                "Windows.\n\n"
                "Os caminhos e tempos operacionais serão usados na "
                "próxima abertura da página SINAN. A página inicial, "
                "o estado da janela e o dashboard continuam seguindo "
                "as preferências gerais."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )


    def restaurar_padroes(self):
        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Restaurar configurações?",
            mensagem=(
                "As preferências gerais, os caminhos operacionais e "
                "os tempos da exportação voltarão aos valores padrão.\n\n"
                "Nenhum banco, relatório, ZIP ou DBF será alterado."
            ),
            texto_confirmar="Restaurar padrões",
            texto_cancelar="Cancelar",
            tipo="aviso"
        )

        if not confirmou:
            return

        self.configuracoes = (
            self.configuracoes_service
            .restaurar_padroes()
        )
        self.manutencao_service = (
            ManutencaoService()
        )

        geral = self.configuracoes[
            "geral"
        ]
        dashboard = self.configuracoes[
            "dashboard"
        ]
        operacional = self.configuracoes[
            "operacional"
        ]
        caminhos = operacional[
            "caminhos"
        ]
        exportacao = operacional[
            "exportacao"
        ]

        self.pagina_inicial_var.set(
            self.PAGINAS_INVERSAS[
                geral["pagina_inicial"]
            ]
        )
        self.abrir_maximizado_var.set(
            geral["abrir_maximizado"]
        )
        self.dashboard_automatico_var.set(
            dashboard[
                "atualizacao_automatica"
            ]
        )
        self.intervalo_dashboard_var.set(
            self.INTERVALOS_INVERSOS[
                dashboard[
                    "intervalo_segundos"
                ]
            ]
        )

        for chave, _, _ in self.CAMINHOS_OPERACIONAIS:
            self.caminhos_vars[
                chave
            ].set(
                str(
                    caminhos[chave]
                )
            )

            status = self.status_caminhos.get(
                chave
            )

            if status is not None:
                status.configure(
                    text="○ Padrão restaurado — teste antes de usar",
                    text_color=Colors.TEXT_MUTED
                )

        self.intervalo_exportacao_var.set(
            self._rotulo_por_valor(
                self.INTERVALOS_EXPORTACAO,
                exportacao[
                    "intervalo_consulta_segundos"
                ],
                "15 segundos"
            )
        )
        self.aviso_inicial_var.set(
            self._rotulo_por_valor(
                self.AVISOS_INICIAIS,
                exportacao[
                    "aviso_inicial_segundos"
                ],
                "1 minuto"
            )
        )
        self.aviso_lento_var.set(
            self._rotulo_por_valor(
                self.AVISOS_LENTOS,
                exportacao[
                    "aviso_lento_segundos"
                ],
                "5 minutos"
            )
        )
        self.aviso_reforcado_var.set(
            self._rotulo_por_valor(
                self.AVISOS_REFORCADOS,
                exportacao[
                    "aviso_reforcado_segundos"
                ],
                "10 minutos"
            )
        )
        self.tempo_limite_exportacao_var.set(
            self._rotulo_por_valor(
                self.LIMITES_EXPORTACAO,
                exportacao[
                    "tempo_limite_segundos"
                ],
                "20 minutos"
            )
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Padrões restaurados",
            mensagem=(
                "As configurações padrão foram restauradas.\n\n"
                "Teste as quatro pastas operacionais antes de iniciar "
                "uma nova rotina de Bases."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )


class ConfirmacaoResetBasesDialog(ctk.CTkToplevel):
    """
    Confirmação forte para o reset completo de Bases.

    A prévia é exibida em uma área rolável e o botão só é liberado
    quando a frase exigida é digitada exatamente.
    """

    LARGURA = 680
    ALTURA = 610

    def __init__(
        self,
        master,
        previa: PreviaResetBases,
        manutencao_service: ManutencaoService
    ):
        super().__init__(
            master
        )

        self.previa = previa
        self.manutencao_service = (
            manutencao_service
        )
        self.resultado: str | None = None
        self.frase_var = ctk.StringVar()

        self.title(
            "ArboHub — Reset completo de Bases"
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
            False
        )
        self.configure(
            fg_color=Colors.BACKGROUND
        )

        try:
            self.transient(
                master
            )
        except Exception:
            pass

        self.protocol(
            "WM_DELETE_WINDOW",
            self._cancelar
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )
        self.grid_rowconfigure(
            1,
            weight=1
        )

        self._criar_cabecalho()
        self._criar_conteudo()
        self._criar_rodape()

        self.frase_var.trace_add(
            "write",
            self._atualizar_botao
        )

        self.after(
            40,
            self._centralizar
        )
        self.after(
            80,
            self._ativar_modal
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
        icone.grid_propagate(
            False
        )

        ctk.CTkLabel(
            icone,
            text="!",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=21,
                weight="bold"
            ),
            text_color=Colors.WARNING
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            cabecalho,
            text="AÇÃO DE MANUTENÇÃO",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.WARNING,
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
            text="Resetar rotina de Bases de hoje",
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
            sticky="nsew",
            padx=20,
            pady=20
        )
        conteudo.grid_columnconfigure(
            0,
            weight=1
        )
        conteudo.grid_rowconfigure(
            0,
            weight=1
        )

        previa_texto = (
            self.manutencao_service
            .formatar_previa(
                self.previa
            )
        )

        caixa_previa = ctk.CTkTextbox(
            conteudo,
            fg_color=Colors.SURFACE,
            border_width=1,
            border_color=Colors.BORDER,
            corner_radius=8,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            wrap="word"
        )
        caixa_previa.grid(
            row=0,
            column=0,
            sticky="nsew"
        )
        caixa_previa.insert(
            "1.0",
            previa_texto
        )
        caixa_previa.configure(
            state="disabled"
        )

        ctk.CTkLabel(
            conteudo,
            text=(
                "Digite exatamente RESETAR BASES para confirmar:"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(16, 7)
        )

        self.campo_frase = ctk.CTkEntry(
            conteudo,
            textvariable=self.frase_var,
            height=38,
            corner_radius=7,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text="RESETAR BASES",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        )
        self.campo_frase.grid(
            row=2,
            column=0,
            sticky="ew"
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
        rodape.grid_columnconfigure(
            0,
            weight=1
        )

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

        ctk.CTkButton(
            botoes,
            text="Cancelar",
            command=self._cancelar,
            width=110,
            height=36,
            corner_radius=7,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.botao_confirmar = ctk.CTkButton(
            botoes,
            text="Criar backup e resetar",
            command=self._confirmar,
            width=180,
            height=36,
            corner_radius=7,
            fg_color=Colors.WARNING,
            hover_color="#B7811C",
            text_color=Colors.TEXT_PRIMARY,
            state="disabled",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        )
        self.botao_confirmar.pack(
            side="left"
        )

    def _atualizar_botao(
        self,
        *_args
    ):
        valido = (
            self.frase_var.get().strip()
            == self.manutencao_service
            .FRASE_CONFIRMACAO
        )

        self.botao_confirmar.configure(
            state=(
                "normal"
                if valido
                else "disabled"
            )
        )

    def _confirmar(self):
        frase = self.frase_var.get().strip()

        if (
            frase
            != self.manutencao_service
            .FRASE_CONFIRMACAO
        ):
            return

        self.resultado = frase
        self._fechar()

    def _cancelar(self):
        self.resultado = None
        self._fechar()

    def _fechar(self):
        try:
            self.grab_release()
        except Exception:
            pass

        self.destroy()

    def _centralizar(self):
        self.update_idletasks()

        largura_tela = self.winfo_screenwidth()
        altura_tela = self.winfo_screenheight()
        x = max(
            0,
            (largura_tela - self.LARGURA) // 2
        )
        y = max(
            0,
            (altura_tela - self.ALTURA) // 2
        )

        self.geometry(
            f"{self.LARGURA}x{self.ALTURA}+{x}+{y}"
        )

    def _ativar_modal(self):
        try:
            self.grab_set()
            self.focus_force()
            self.campo_frase.focus_set()
        except Exception:
            pass

    def mostrar(self) -> str | None:
        self.wait_window()
        return self.resultado

