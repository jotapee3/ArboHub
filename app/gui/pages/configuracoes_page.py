from __future__ import annotations

import os
from datetime import date
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
from app.services.credenciais_service import (
    CredenciaisService
)
from app.services.manutencao_service import (
    ManutencaoService,
    PreviaResetBases
)
from app.services.notificacoes_service import (
    NotificacoesService
)
from app.services.suporte_service import (
    EMAIL_SUPORTE,
    RESPONSAVEL_SUPORTE,
    ROTULO_VERSAO_ARBOHUB,
    SuporteService
)
from app.services.usuario_windows_service import (
    UsuarioWindowsService
)


class ConfiguracoesPage(ctk.CTkScrollableFrame):
    """
    Preferências gerais do ArboHub.

    As preferências comuns ficam no JSON local. A credencial do
    SINAN, quando usada, é mantida exclusivamente pelo Gerenciador
    de Credenciais do Windows. O conteúdo interno dos DBFs não é
    acessado por esta página.
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

    TEMAS_INTERFACE = {
        "Escuro": "escuro",
        "Claro": "claro",
        "Seguir o Windows": "sistema"
    }

    TEMAS_INTERFACE_INVERSOS = {
        valor: chave
        for chave, valor in TEMAS_INTERFACE.items()
    }

    ESCALAS_INTERFACE = {
        "90% — compacta": 90,
        "100% — recomendada": 100,
        "110% — ampliada": 110,
        "125% — acessibilidade": 125
    }

    ESCALAS_INTERFACE_INVERSAS = {
        valor: chave
        for chave, valor in ESCALAS_INTERFACE.items()
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
            "Dengue (AB1)",
            (
                "Destino do banco anual de Dengue usado nos "
                "testes do setor."
            )
        ),
        (
            "teste_ab2",
            "Chikungunya (AB2)",
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

    NOMES_ARQUIVOS_TESTE_POR_CAMINHO = {
        "teste_ab1": (
            "dengue",
            "Nome final do DBF de Dengue"
        ),
        "teste_ab2": (
            "chikungunya",
            "Nome final do DBF de Chikungunya"
        )
    }

    CATEGORIAS = (
        (
            "aparencia",
            "🎨",
            "Aparência",
            "Tema, escala e comportamento ao iniciar."
        ),
        (
            "dados",
            "🗂️",
            "Dados e arquivos",
            "Pastas usadas pelos fluxos operacionais."
        ),
        (
            "automacao",
            "⚡",
            "Automação",
            "Dashboard e tempos das rotinas automáticas."
        ),
        (
            "acessos",
            "🔐",
            "Acessos",
            "Login automático e credencial do SINAN."
        ),
        (
            "notificacoes",
            "🔔",
            "Notificações",
            "Sons locais e contatos de supervisão."
        ),
        (
            "manutencao",
            "🛠️",
            "Manutenção",
            "Testes, reset e informações técnicas."
        )
    )

    def __init__(
        self,
        master,
        ao_salvar=None,
        ao_reiniciar=None
    ):
        super().__init__(
            master,
            fg_color=Colors.BACKGROUND,
            corner_radius=0,
            scrollbar_button_color=Colors.BORDER,
            scrollbar_button_hover_color=Colors.TEXT_MUTED
        )

        self.ao_salvar = ao_salvar
        self.ao_reiniciar = ao_reiniciar
        self.configuracoes_service = (
            ConfiguracoesService()
        )
        self.credenciais_service = (
            CredenciaisService()
        )
        self.manutencao_service = (
            ManutencaoService()
        )
        self.notificacoes_service = (
            NotificacoesService()
        )
        self.suporte_service = (
            SuporteService()
        )
        self.usuario_windows_service = (
            UsuarioWindowsService()
        )
        self.identidade_windows = (
            self.usuario_windows_service.obter_identidade()
        )
        self.configuracoes = (
            self.configuracoes_service.carregar()
        )

        self.grid_columnconfigure(
            0,
            weight=1
        )

        self._criar_variaveis()
        self._categoria_atual = "inicio"
        self._mostrar_inicio_configuracoes()

    def _criar_variaveis(self):
        geral = self.configuracoes[
            "geral"
        ]
        aparencia = self.configuracoes[
            "aparencia"
        ]
        dashboard = self.configuracoes[
            "dashboard"
        ]
        sinan = self.configuracoes[
            "sinan"
        ]
        notificacoes = self.configuracoes[
            "notificacoes"
        ]
        supervisao = notificacoes[
            "supervisao"
        ]
        operacional = self.configuracoes[
            "operacional"
        ]
        caminhos = operacional[
            "caminhos"
        ]
        nomes_arquivos_teste = operacional[
            "nomes_arquivos_teste"
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
        self.tema_interface_var = ctk.StringVar(
            value=self.TEMAS_INTERFACE_INVERSOS.get(
                str(
                    aparencia.get(
                        "tema",
                        "escuro"
                    )
                ),
                "Escuro"
            )
        )
        self.escala_interface_var = ctk.StringVar(
            value=self.ESCALAS_INTERFACE_INVERSAS.get(
                int(
                    aparencia.get(
                        "escala_percentual",
                        100
                    )
                ),
                "100% — recomendada"
            )
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

        self.login_automatico_var = ctk.BooleanVar(
            value=bool(
                sinan.get(
                    "login_automatico",
                    False
                )
            )
        )
        self.usuario_sinan_var = ctk.StringVar(
            value=""
        )
        self.senha_sinan_var = ctk.StringVar(
            value=""
        )
        self.label_status_credencial = None
        self.entry_senha_sinan = None

        try:
            usuario_armazenado = (
                self.credenciais_service
                .obter_usuario()
            )
        except Exception:
            usuario_armazenado = None

        if usuario_armazenado:
            self.usuario_sinan_var.set(
                usuario_armazenado
            )

        self.som_conclusao_var = ctk.BooleanVar(
            value=bool(
                notificacoes.get(
                    "som_conclusao",
                    True
                )
            )
        )
        self.som_atencao_var = ctk.BooleanVar(
            value=bool(
                notificacoes.get(
                    "som_atencao",
                    True
                )
            )
        )
        self.som_exportacao_disponivel_var = (
            ctk.BooleanVar(
                value=bool(
                    notificacoes.get(
                        "som_exportacao_disponivel",
                        False
                    )
                )
            )
        )
        self.supervisora_nome_var = ctk.StringVar(
            value=str(
                supervisao.get(
                    "nome",
                    ""
                )
            )
        )
        self.supervisora_telefone_var = ctk.StringVar(
            value=str(
                supervisao.get(
                    "telefone",
                    ""
                )
            )
        )
        self.supervisora_email_var = ctk.StringVar(
            value=str(
                supervisao.get(
                    "email",
                    ""
                )
            )
        )
        self.label_status_som = None

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
        self.nomes_arquivos_teste_vars = {
            chave: ctk.StringVar(
                value=str(
                    nomes_arquivos_teste[chave]
                )
            )
            for chave in (
                "dengue",
                "chikungunya"
            )
        }
        self.labels_previas_nomes_arquivos: dict[
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

    def _limpar_conteudo_configuracoes(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Referências para widgets que existem apenas dentro de
        # determinadas categorias não podem sobreviver à navegação.
        self.label_status_credencial = None
        self.entry_senha_sinan = None
        self.label_status_som = None
        self.status_caminhos.clear()

    def _rolar_para_topo(self):
        try:
            self._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _mostrar_inicio_configuracoes(self):
        self._limpar_conteudo_configuracoes()
        self._categoria_atual = "inicio"

        self._criar_cabecalho_inicio()
        self._criar_cartao_usuario_windows()
        self._criar_grade_categorias()
        self._criar_rodape_inicio()
        self.after_idle(self._rolar_para_topo)

    def _mostrar_categoria(self, categoria: str):
        categorias_validas = {
            item[0]
            for item in self.CATEGORIAS
        }

        if categoria not in categorias_validas:
            return

        self._limpar_conteudo_configuracoes()
        self._categoria_atual = categoria
        self._criar_cabecalho_categoria(categoria)

        secoes = {
            "aparencia": (
                self._criar_secao_geral,
                self._criar_secao_escala_interface
            ),
            "dados": (
                self._criar_secao_caminhos_operacionais,
            ),
            "automacao": (
                self._criar_secao_dashboard,
                self._criar_secao_exportacao_parcial
            ),
            "acessos": (
                self._criar_secao_login_sinan,
            ),
            "notificacoes": (
                self._criar_secao_notificacoes_supervisao,
            ),
            "manutencao": (
                self._criar_secao_manutencao,
                self._criar_secao_ajuda_suporte,
                self._criar_secao_sobre
            )
        }

        for criar_secao in secoes[categoria]:
            criar_secao()

        self._criar_rodape()
        self.after_idle(self._rolar_para_topo)

    def _obter_dados_categoria(
        self,
        categoria: str
    ) -> tuple[str, str, str]:
        for chave, icone, titulo, descricao in self.CATEGORIAS:
            if chave == categoria:
                return icone, titulo, descricao

        return "⚙️", "Configurações", "Preferências do ArboHub."

    def _criar_cabecalho_inicio(self):
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
                "Gerencie as preferências e o funcionamento do "
                "ArboHub."
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
            text_color=Colors.TEXT_ON_PRIMARY,
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

    def _criar_cartao_usuario_windows(self):
        identidade = self.identidade_windows

        card = ctk.CTkFrame(
            self,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 9)
        )
        card.grid_columnconfigure(1, weight=1)

        avatar = ctk.CTkFrame(
            card,
            width=50,
            height=50,
            corner_radius=25,
            fg_color=Colors.SURFACE_HOVER
        )
        avatar.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(16, 12),
            pady=14
        )
        avatar.grid_propagate(False)
        avatar.grid_rowconfigure(0, weight=1)
        avatar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            avatar,
            text="👤",
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=23
            ),
            text_color=Colors.TEXT_SECONDARY
        ).grid(
            row=0,
            column=0
        )

        ctk.CTkLabel(
            card,
            text=identidade.nome_exibicao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="sw"
        ).grid(
            row=0,
            column=1,
            sticky="sew",
            padx=(0, 12),
            pady=(14, 1)
        )

        ctk.CTkLabel(
            card,
            text=identidade.conta,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="nw"
        ).grid(
            row=1,
            column=1,
            sticky="new",
            padx=(0, 12),
            pady=(1, 14)
        )

        ctk.CTkLabel(
            card,
            text="Conta do Windows",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
                weight="bold"
            ),
            text_color=Colors.INFO,
            anchor="e"
        ).grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="e",
            padx=(12, 18)
        )

    def _criar_grade_categorias(self):
        grade = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        grade.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=40,
            pady=(2, 22)
        )
        grade.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
            uniform="categorias_configuracoes"
        )

        for indice, dados in enumerate(self.CATEGORIAS):
            chave, icone, titulo, descricao = dados
            linha = indice // 3
            coluna = indice % 3

            self._criar_card_categoria(
                master=grade,
                linha=linha,
                coluna=coluna,
                chave=chave,
                icone=icone,
                titulo=titulo,
                descricao=descricao
            )

    def _criar_card_categoria(
        self,
        master,
        linha: int,
        coluna: int,
        chave: str,
        icone: str,
        titulo: str,
        descricao: str
    ):
        card = ctk.CTkFrame(
            master,
            height=128,
            fg_color=Colors.SURFACE,
            corner_radius=9,
            border_width=1,
            border_color=Colors.BORDER
        )
        card.grid(
            row=linha,
            column=coluna,
            sticky="nsew",
            padx=(
                (0, 7)
                if coluna == 0
                else (
                    (7, 0)
                    if coluna == 2
                    else 7
                )
            ),
            pady=7
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)

        label_icone = ctk.CTkLabel(
            card,
            text=icone,
            width=40,
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=22
            ),
            text_color=Colors.INFO
        )
        label_icone.grid(
            row=0,
            column=0,
            rowspan=2,
            padx=(16, 10),
            pady=18
        )

        label_titulo = ctk.CTkLabel(
            card,
            text=titulo,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=14,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        label_titulo.grid(
            row=0,
            column=1,
            sticky="sew",
            pady=(23, 2)
        )

        label_descricao = ctk.CTkLabel(
            card,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="nw",
            justify="left",
            wraplength=220
        )
        label_descricao.grid(
            row=1,
            column=1,
            sticky="new",
            pady=(2, 20)
        )

        label_seta = ctk.CTkLabel(
            card,
            text="›",
            width=20,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=20
            ),
            text_color=Colors.TEXT_MUTED
        )
        label_seta.grid(
            row=0,
            column=2,
            rowspan=2,
            padx=(8, 14)
        )

        componentes = (
            card,
            label_icone,
            label_titulo,
            label_descricao,
            label_seta
        )

        for componente in componentes:
            componente.bind(
                "<Button-1>",
                lambda _evento, item=chave:
                    self._mostrar_categoria(item)
            )
            componente.bind(
                "<Enter>",
                lambda _evento, alvo=card:
                    alvo.configure(
                        fg_color=Colors.SURFACE_HOVER
                    )
            )
            componente.bind(
                "<Leave>",
                lambda _evento, alvo=card:
                    alvo.configure(
                        fg_color=Colors.SURFACE
                    )
            )

    def _criar_rodape_inicio(self):
        rodape = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        rodape.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=40,
            pady=(0, 30)
        )
        rodape.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            rodape,
            text=(
                f"{ROTULO_VERSAO_ARBOHUB}  •  "
                "Configurações locais desta "
                "conta do Windows"
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w"
        )

        ctk.CTkButton(
            rodape,
            text="Restaurar padrões",
            command=self.restaurar_padroes,
            width=145,
            height=34,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

    def _criar_cabecalho_categoria(self, categoria: str):
        icone, titulo, descricao = (
            self._obter_dados_categoria(categoria)
        )

        cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        cabecalho.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=40,
            pady=(24, 18)
        )
        cabecalho.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            cabecalho,
            text="←  Configurações",
            command=self._mostrar_inicio_configuracoes,
            width=132,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=0,
            text_color=Colors.INFO,
            anchor="w",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 12)
        )

        ctk.CTkLabel(
            cabecalho,
            text=f"{icone}  {titulo}",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=26,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=1,
            column=0,
            sticky="ew"
        )

        ctk.CTkLabel(
            cabecalho,
            text=descricao,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(
            row=2,
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
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold"
            )
        ).grid(
            row=1,
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

    def _criar_secao_escala_interface(self):
        painel = self._criar_painel(
            linha=3,
            titulo="Aparência",
            descricao=(
                "Escolha o tema e ajuste o tamanho dos textos e "
                "controles sem perder a identidade visual do ArboHub."
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
            pady=(4, 8)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_aparencia"
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Tema da interface",
            descricao=(
                "Use o tema escuro, o claro ou acompanhe a "
                "preferência de aplicativos do Windows."
            ),
            variavel=self.tema_interface_var,
            valores=list(
                self.TEMAS_INTERFACE.keys()
            )
        )

        self._criar_opcao_menu(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Escala da interface",
            descricao=(
                "Aumenta ou reduz textos, botões, campos e "
                "espaçamentos dos componentes."
            ),
            variavel=self.escala_interface_var,
            valores=list(
                self.ESCALAS_INTERFACE.keys()
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
            text="↻",
            width=32,
            font=ctk.CTkFont(
                family="Segoe UI Symbol",
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
                "Tema e escala são aplicados integralmente na próxima "
                "abertura. No modo “Seguir o Windows”, o ArboHub "
                "consulta o tema do sistema sempre que for iniciado."
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


    def _criar_secao_login_sinan(self):
        painel = self._criar_painel(
            linha=4,
            titulo="Acesso ao SINAN",
            descricao=(
                "Configure o login automático sem guardar a senha "
                "nos arquivos do ArboHub."
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
            text="🔐",
            width=34,
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=16
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
                "A credencial é armazenada pelo Gerenciador de "
                "Credenciais do Windows e fica vinculada a esta "
                "conta do Windows. A senha não entra no JSON, no "
                "banco SQLite, no GitHub ou nos logs."
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
            pady=(0, 6)
        )
        grade.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="config_login_sinan"
        )

        card_login = self._criar_card_opcao(
            master=grade,
            linha=0,
            coluna=0,
            titulo="Login automático",
            descricao=(
                "Tenta autenticar no domínio oficial do SINAN. "
                "Se não funcionar, o navegador permanece aberto "
                "para login manual."
            )
        )

        switch_login = ctk.CTkSwitch(
            card_login,
            text="Ativado",
            variable=self.login_automatico_var,
            onvalue=True,
            offvalue=False,
            switch_width=40,
            switch_height=20,
            corner_radius=10,
            border_width=1,
            progress_color=Colors.PRIMARY,
            button_color=Colors.CONTROL_KNOB,
            button_hover_color=Colors.CONTROL_KNOB,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        )
        self._preparar_visual_switch(
            switch_login,
            self.login_automatico_var,
            exibir_estado=True
        )
        switch_login.grid(
            row=2,
            column=0,
            sticky="w",
            padx=14,
            pady=(10, 16)
        )

        card_status = self._criar_card_opcao(
            master=grade,
            linha=0,
            coluna=1,
            titulo="Credencial protegida",
            descricao=(
                "O ArboHub consulta apenas a entrada ArboHub/SINAN "
                "do cofre do usuário atual."
            )
        )

        self.label_status_credencial = ctk.CTkLabel(
            card_status,
            text="Verificando o Windows...",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=330
        )
        self.label_status_credencial.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 16)
        )

        credenciais = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        credenciais.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20)
        )
        credenciais.grid_columnconfigure(
            (0, 1),
            weight=1,
            uniform="campos_credencial_sinan"
        )

        ctk.CTkLabel(
            credenciais,
            text="Usuário",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(14, 7),
            pady=(14, 5)
        )

        ctk.CTkLabel(
            credenciais,
            text="Senha",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(7, 14),
            pady=(14, 5)
        )

        ctk.CTkEntry(
            credenciais,
            textvariable=self.usuario_sinan_var,
            height=36,
            corner_radius=6,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text="Usuário do SINAN",
            placeholder_text_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            )
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(14, 7)
        )

        self.entry_senha_sinan = ctk.CTkEntry(
            credenciais,
            textvariable=self.senha_sinan_var,
            show="●",
            height=36,
            corner_radius=6,
            fg_color=Colors.INPUT,
            border_color=Colors.INPUT_BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text=(
                "Digite apenas para salvar ou substituir"
            ),
            placeholder_text_color=Colors.TEXT_MUTED,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            )
        )
        self.entry_senha_sinan.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(7, 14)
        )

        botoes = ctk.CTkFrame(
            credenciais,
            fg_color="transparent"
        )
        botoes.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(12, 14)
        )
        botoes.grid_columnconfigure(
            3,
            weight=1
        )

        ctk.CTkButton(
            botoes,
            text="Salvar credencial",
            command=self.salvar_credencial_sinan,
            width=145,
            height=34,
            corner_radius=6,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=0,
            padx=(0, 8)
        )

        ctk.CTkButton(
            botoes,
            text="Verificar armazenamento",
            command=self.verificar_credencial_sinan,
            width=175,
            height=34,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=1,
            padx=(0, 8)
        )

        ctk.CTkButton(
            botoes,
            text="Remover credencial",
            command=self.remover_credencial_sinan,
            width=155,
            height=34,
            corner_radius=6,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.ERROR,
            text_color=Colors.ERROR,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=2
        )

        ctk.CTkLabel(
            botoes,
            text=(
                "A senha nunca é exibida novamente depois de salva."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="e"
        ).grid(
            row=0,
            column=3,
            sticky="e",
            padx=(12, 0)
        )

        self._atualizar_status_credencial()

    def _criar_secao_caminhos_operacionais(self):
        painel = self._criar_painel(
            linha=5,
            titulo="Pastas operacionais",
            descricao=(
                "Defina os destinos usados pelo fluxo de Bases. "
                "Nas pastas de teste, você também pode definir o "
                "nome final dos DBFs. O ArboHub valida tudo antes "
                "de salvar."
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
            sticky="ew",
            padx=(14, 8),
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

        ctk.CTkButton(
            card,
            text="📂",
            command=(
                lambda item=chave:
                    self._selecionar_pasta_operacional(
                        item
                    )
            ),
            width=40,
            height=36,
            corner_radius=6,
            fg_color=Colors.BUTTON,
            hover_color=Colors.BUTTON_HOVER,
            border_width=1,
            border_color=Colors.BUTTON_BORDER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=14
            )
        ).grid(
            row=2,
            column=1,
            padx=(0, 14),
            pady=(10, 8)
        )

        linha_acoes = 3
        configuracao_nome = (
            self.NOMES_ARQUIVOS_TESTE_POR_CAMINHO.get(
                chave
            )
        )

        if configuracao_nome is not None:
            chave_nome, rotulo_nome = configuracao_nome

            ctk.CTkLabel(
                card,
                text=rotulo_nome,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold"
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w"
            ).grid(
                row=3,
                column=0,
                columnspan=3,
                sticky="ew",
                padx=14,
                pady=(4, 3)
            )

            campo_nome = ctk.CTkEntry(
                card,
                textvariable=(
                    self.nomes_arquivos_teste_vars[
                        chave_nome
                    ]
                ),
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
            campo_nome.grid(
                row=4,
                column=0,
                sticky="ew",
                padx=(14, 8),
                pady=(0, 4)
            )
            campo_nome.bind(
                "<KeyRelease>",
                lambda _evento, item=chave_nome:
                    self._atualizar_previa_nome_arquivo(
                        item
                    ),
                add="+"
            )

            ctk.CTkButton(
                card,
                text="✏️",
                command=(
                    lambda entrada=campo_nome:
                        self._focar_campo_nome_arquivo(
                            entrada
                        )
                ),
                width=40,
                height=36,
                corner_radius=6,
                fg_color=Colors.BUTTON,
                hover_color=Colors.BUTTON_HOVER,
                border_width=1,
                border_color=Colors.BUTTON_BORDER,
                text_color=Colors.TEXT_SECONDARY,
                font=ctk.CTkFont(
                    family="Segoe UI Emoji",
                    size=14
                )
            ).grid(
                row=4,
                column=1,
                padx=(0, 14),
                pady=(0, 4)
            )

            previa = ctk.CTkLabel(
                card,
                text="",
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10
                ),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            )
            previa.grid(
                row=5,
                column=0,
                columnspan=3,
                sticky="ew",
                padx=14,
                pady=(0, 4)
            )
            self.labels_previas_nomes_arquivos[
                chave_nome
            ] = previa
            self._atualizar_previa_nome_arquivo(
                chave_nome
            )
            linha_acoes = 6

        barra_acoes = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        barra_acoes.grid(
            row=linha_acoes,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=14
        )
        barra_acoes.grid_columnconfigure(
            2,
            weight=1
        )

        for coluna, (
            texto,
            comando
        ) in enumerate(
            (
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
                    else (6, 0)
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
            row=linha_acoes + 1,
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
            linha=6,
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

    def _criar_secao_notificacoes_supervisao(self):
        painel = self._criar_painel(
            linha=7,
            titulo="Notificações e supervisão",
            descricao=(
                "Defina sons locais do Windows e contatos "
                "institucionais usados nos avisos de pendência."
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
            text="🔔",
            width=34,
            font=ctk.CTkFont(
                family="Segoe UI Emoji",
                size=16
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
                "Os sons são reproduzidos pelo próprio Windows. "
                "O ArboHub não envia e-mail, WhatsApp ou qualquer "
                "mensagem automaticamente. Os dados de supervisão "
                "ficam somente nas configurações locais."
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
            (0, 1),
            weight=1,
            uniform="notificacoes_supervisao"
        )

        sons = ctk.CTkFrame(
            grade,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        sons.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 6)
        )
        sons.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            sons,
            text="Sons do Windows",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(14, 3)
        )

        ctk.CTkLabel(
            sons,
            text=(
                "Avisos discretos que nunca substituem as "
                "mensagens visuais."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=330
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(0, 8)
        )

        opcoes_som = (
            (
                "Conclusão da rotina",
                self.som_conclusao_var,
                NotificacoesService.TIPO_CONCLUSAO
            ),
            (
                "Rotina exige atenção",
                self.som_atencao_var,
                NotificacoesService.TIPO_ATENCAO
            ),
            (
                "Exportação disponível",
                self.som_exportacao_disponivel_var,
                (
                    NotificacoesService
                    .TIPO_EXPORTACAO_DISPONIVEL
                )
            )
        )

        for indice, (
            texto,
            variavel,
            tipo
        ) in enumerate(
            opcoes_som,
            start=2
        ):
            switch_som = ctk.CTkSwitch(
                sons,
                text=texto,
                variable=variavel,
                onvalue=True,
                offvalue=False,
                switch_width=40,
                switch_height=20,
                corner_radius=10,
                border_width=1,
                progress_color=Colors.PRIMARY,
                button_color=Colors.CONTROL_KNOB,
                button_hover_color=Colors.CONTROL_KNOB,
                text_color=Colors.TEXT_PRIMARY,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11,
                    weight="bold"
                )
            )
            self._preparar_visual_switch(
                switch_som,
                variavel
            )
            switch_som.grid(
                row=indice,
                column=0,
                sticky="w",
                padx=(14, 8),
                pady=6
            )

            ctk.CTkButton(
                sons,
                text="Testar",
                command=(
                    lambda item=tipo:
                        self.testar_som_notificacao(
                            item
                        )
                ),
                width=72,
                height=28,
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
                row=indice,
                column=1,
                sticky="e",
                padx=(0, 14),
                pady=6
            )

        self.label_status_som = ctk.CTkLabel(
            sons,
            text="○ Use “Testar” para conferir o volume do Windows.",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.label_status_som.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=14,
            pady=(8, 14)
        )

        supervisao = ctk.CTkFrame(
            grade,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        supervisao.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 0)
        )
        supervisao.grid_columnconfigure(
            0,
            weight=1
        )

        ctk.CTkLabel(
            supervisao,
            text="Supervisão",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=14,
            pady=(14, 3)
        )

        ctk.CTkLabel(
            supervisao,
            text=(
                "Dados institucionais opcionais usados somente "
                "para copiar contatos e o resumo da pendência."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=330
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 8)
        )

        campos = (
            (
                "Nome da supervisora",
                self.supervisora_nome_var,
                "Nome institucional"
            ),
            (
                "Telefone institucional",
                self.supervisora_telefone_var,
                "(51) 0000-0000"
            ),
            (
                "E-mail institucional",
                self.supervisora_email_var,
                "nome@instituicao.gov.br"
            )
        )

        linha = 2

        for (
            titulo,
            variavel,
            placeholder
        ) in campos:
            ctk.CTkLabel(
                supervisao,
                text=titulo,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=10,
                    weight="bold"
                ),
                text_color=Colors.TEXT_SECONDARY,
                anchor="w"
            ).grid(
                row=linha,
                column=0,
                sticky="ew",
                padx=14,
                pady=(6, 4)
            )

            ctk.CTkEntry(
                supervisao,
                textvariable=variavel,
                height=34,
                corner_radius=6,
                fg_color=Colors.INPUT,
                border_color=Colors.INPUT_BORDER,
                text_color=Colors.TEXT_PRIMARY,
                placeholder_text=placeholder,
                placeholder_text_color=Colors.TEXT_MUTED,
                font=ctk.CTkFont(
                    family="Segoe UI",
                    size=11
                )
            ).grid(
                row=linha + 1,
                column=0,
                sticky="ew",
                padx=14
            )

            linha += 2

        ctk.CTkLabel(
            supervisao,
            text=(
                "Nenhum contato é enviado automaticamente."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=linha,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 14)
        )

    def testar_som_notificacao(
        self,
        tipo: str
    ):
        reproduzido = (
            self.notificacoes_service
            .testar_som(
                tipo
            )
        )

        if self.label_status_som is None:
            return

        if reproduzido:
            self.label_status_som.configure(
                text="✓ Som solicitado ao Windows.",
                text_color=Colors.SUCCESS
            )
        else:
            self.label_status_som.configure(
                text=(
                    "× O som não pôde ser reproduzido neste sistema."
                ),
                text_color=Colors.ERROR
            )

    def _criar_secao_manutencao(self):
        painel = self._criar_painel(
            linha=8,
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
                Colors.WARNING_HOVER
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
                "Consulta, Relatórios, os destinos configurados "
                "para Dengue e Chikungunya e Bancos_Atuais foram "
                "preservados.\n\n"
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

    def salvar_credencial_sinan(self):
        usuario = self.usuario_sinan_var.get().strip()
        senha = self.senha_sinan_var.get()

        try:
            self.credenciais_service.salvar(
                usuario=usuario,
                senha=senha
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Credencial não salva",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        self.senha_sinan_var.set("")
        self.login_automatico_var.set(True)
        self._atualizar_status_credencial()

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Credencial protegida pelo Windows",
            mensagem=(
                "A credencial do SINAN foi salva no Gerenciador de "
                "Credenciais desta conta do Windows.\n\n"
                "O login automático foi marcado como ativo nesta "
                "tela. Clique em Salvar alterações para aplicar essa "
                "preferência às próximas rotinas."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def verificar_credencial_sinan(self):
        credencial = None

        try:
            credencial = self.credenciais_service.obter()
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível verificar",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        if credencial is None:
            self._atualizar_status_credencial()
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Nenhuma credencial encontrada",
                mensagem=(
                    "O Windows não encontrou a entrada segura "
                    "ArboHub/SINAN para esta conta."
                ),
                tipo="informacao",
                texto_botao="Entendi"
            )
            return

        usuario = credencial.usuario
        credencial = None
        self.usuario_sinan_var.set(usuario)
        self._atualizar_status_credencial()

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Armazenamento verificado",
            mensagem=(
                "O Windows conseguiu recuperar a credencial segura "
                f"do usuário {usuario}.\n\n"
                "A senha não foi exibida. A autenticação real será "
                "confirmada somente ao abrir uma rotina do SINAN."
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def remover_credencial_sinan(self):
        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Remover credencial do SINAN?",
            mensagem=(
                "A entrada ArboHub/SINAN será removida do "
                "Gerenciador de Credenciais desta conta do Windows.\n\n"
                "O login manual continuará disponível e nenhum dado "
                "operacional será alterado."
            ),
            texto_confirmar="Remover credencial",
            texto_cancelar="Cancelar",
            tipo="aviso"
        )

        if not confirmou:
            return

        try:
            removida = self.credenciais_service.remover()
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Credencial não removida",
                mensagem=str(erro),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        self.usuario_sinan_var.set("")
        self.senha_sinan_var.set("")
        self.login_automatico_var.set(False)

        configuracoes_salvas = (
            self.configuracoes_service.carregar()
        )
        configuracoes_salvas.setdefault(
            "sinan",
            {}
        )["login_automatico"] = False
        self.configuracoes = (
            self.configuracoes_service.salvar(
                configuracoes_salvas
            )
        )

        if callable(self.ao_salvar):
            self.ao_salvar(
                self.configuracoes
            )

        self._atualizar_status_credencial()

        mostrar_dialogo_arbohub(
            master=self.winfo_toplevel(),
            titulo="Credencial removida",
            mensagem=(
                "A credencial segura foi removida e o login "
                "automático foi desativado."
                if removida
                else (
                    "Nenhuma credencial estava armazenada. O login "
                    "automático foi desativado."
                )
            ),
            tipo="sucesso",
            texto_botao="Entendi"
        )

    def _validar_configuracao_login(self) -> None:
        if not self.login_automatico_var.get():
            return

        try:
            existe = self.credenciais_service.existe()
        except Exception as erro:
            raise RuntimeError(
                "Não foi possível acessar o Gerenciador de "
                f"Credenciais do Windows. Detalhe: {erro}"
            ) from erro

        if not existe:
            raise ValueError(
                "Salve uma credencial do SINAN antes de ativar o "
                "login automático."
            )

    def _atualizar_status_credencial(self):
        if self.label_status_credencial is None:
            return

        try:
            usuario = (
                self.credenciais_service
                .obter_usuario()
            )
        except Exception as erro:
            self.label_status_credencial.configure(
                text=(
                    "✕ Windows indisponível: "
                    + str(erro)
                ),
                text_color=Colors.ERROR
            )
            return

        if usuario:
            self.label_status_credencial.configure(
                text=(
                    "✓ Credencial armazenada para "
                    + usuario
                ),
                text_color=Colors.SUCCESS
            )
        else:
            self.label_status_credencial.configure(
                text="○ Nenhuma credencial armazenada",
                text_color=Colors.TEXT_MUTED
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

    def _atualizar_previa_nome_arquivo(
        self,
        chave: str
    ) -> None:
        label = self.labels_previas_nomes_arquivos.get(
            chave
        )

        if (
            label is None
            or not label.winfo_exists()
        ):
            return

        try:
            modelo = (
                self.configuracoes_service
                .validar_nome_arquivo_teste(
                    chave=chave,
                    modelo=(
                        self.nomes_arquivos_teste_vars[
                            chave
                        ].get()
                    )
                )
            )
            exemplo = modelo.replace(
                "{ano}",
                str(date.today().year)
            )
        except ValueError as erro:
            label.configure(
                text=f"⚠ {erro}",
                text_color=Colors.ERROR
            )
            return

        label.configure(
            text=(
                f"Exemplo atual: {exemplo}  •  "
                "use {ano} para manter o ano automático"
            ),
            text_color=Colors.TEXT_MUTED
        )

    @staticmethod
    def _focar_campo_nome_arquivo(
        campo: ctk.CTkEntry
    ) -> None:
        campo.focus_set()
        campo.selection_range(
            0,
            "end"
        )
        campo.icursor(
            "end"
        )

    def _validar_nomes_arquivos_teste_para_salvar(
        self
    ) -> dict[str, str]:
        nomes = {
            chave: variavel.get()
            for chave, variavel in (
                self.nomes_arquivos_teste_vars.items()
            )
        }
        validados = (
            self.configuracoes_service
            .validar_nomes_arquivos_teste(
                nomes
            )
        )

        for chave, nome in validados.items():
            self.nomes_arquivos_teste_vars[
                chave
            ].set(
                nome
            )
            self._atualizar_previa_nome_arquivo(
                chave
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

    def _criar_secao_ajuda_suporte(self):
        painel = self._criar_painel(
            linha=9,
            titulo="Ajuda e suporte",
            descricao=(
                "Informe problemas, solicite mudanças ou sugira "
                "novas implementações para o ArboHub."
            )
        )

        contato = ctk.CTkFrame(
            painel,
            fg_color=Colors.BACKGROUND,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER
        )
        contato.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=20,
            pady=(4, 20)
        )
        contato.grid_columnconfigure(1, weight=1)

        icone = ctk.CTkFrame(
            contato,
            width=48,
            height=48,
            corner_radius=9,
            fg_color=Colors.SURFACE_HOVER,
            border_width=1,
            border_color=Colors.BORDER
        )
        icone.grid(
            row=0,
            column=0,
            rowspan=3,
            padx=(16, 12),
            pady=(16, 8)
        )
        icone.grid_propagate(False)

        ctk.CTkLabel(
            icone,
            text="✉",
            font=ctk.CTkFont(
                family="Segoe UI Symbol",
                size=22
            ),
            text_color=Colors.INFO
        ).place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ctk.CTkLabel(
            contato,
            text=RESPONSAVEL_SUPORTE,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold"
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            sticky="sew",
            padx=(0, 14),
            pady=(16, 1)
        )

        ctk.CTkLabel(
            contato,
            text="Responsável pelo ArboHub",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 14),
            pady=1
        )

        ctk.CTkLabel(
            contato,
            text=EMAIL_SUPORTE,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11
            ),
            text_color=Colors.INFO,
            anchor="w"
        ).grid(
            row=2,
            column=1,
            sticky="new",
            padx=(0, 14),
            pady=(1, 8)
        )

        ctk.CTkButton(
            contato,
            text="Entrar em contato",
            command=self.abrir_solicitacao_suporte,
            width=160,
            height=36,
            corner_radius=7,
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        ).grid(
            row=0,
            column=2,
            rowspan=3,
            sticky="e",
            padx=(10, 16),
            pady=(16, 8)
        )

        ctk.CTkLabel(
            contato,
            text=(
                "A mensagem será aberta no aplicativo de e-mail "
                "do Windows com a versão do ArboHub e o usuário "
                "desta instalação preenchidos automaticamente."
            ),
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10
            ),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=720
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=16,
            pady=(8, 14)
        )

    def abrir_solicitacao_suporte(self):
        try:
            self.suporte_service.abrir_solicitacao(
                nome_usuario=(
                    self.identidade_windows.nome_exibicao
                ),
                conta_usuario=(
                    self.identidade_windows.conta
                )
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Não foi possível abrir o e-mail",
                mensagem=(
                    "Abra uma nova mensagem manualmente para:\n"
                    f"{EMAIL_SUPORTE}\n\n"
                    f"Detalhe: {erro}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )

    def _criar_secao_sobre(self):
        painel = self._criar_painel(
            linha=10,
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
                ROTULO_VERSAO_ARBOHUB
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
            row=11,
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
            text_color=Colors.TEXT_ON_PRIMARY,
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

        switch = ctk.CTkSwitch(
            card,
            text="Ativado",
            variable=variavel,
            onvalue=True,
            offvalue=False,
            switch_width=40,
            switch_height=20,
            corner_radius=10,
            border_width=1,
            progress_color=Colors.PRIMARY,
            button_color=Colors.CONTROL_KNOB,
            button_hover_color=Colors.CONTROL_KNOB,
            text_color=Colors.TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
                weight="bold"
            )
        )
        self._preparar_visual_switch(
            switch,
            variavel,
            exibir_estado=True
        )
        switch.grid(
            row=2,
            column=0,
            sticky="w",
            padx=14,
            pady=(10, 16)
        )

    def _preparar_visual_switch(
        self,
        switch,
        variavel,
        exibir_estado: bool = False
    ):
        """Aplica ao switch o comportamento visual usado pelo Windows."""
        self._atualizar_visual_switch(
            switch,
            variavel,
            exibir_estado
        )
        switch.configure(
            command=(
                lambda controle=switch, estado=variavel,
                mostrar_estado=exibir_estado:
                    self._atualizar_visual_switch(
                        controle,
                        estado,
                        mostrar_estado
                    )
            )
        )

    def _atualizar_visual_switch(
        self,
        switch,
        variavel,
        exibir_estado: bool = False
    ):
        ativo = bool(variavel.get())

        if exibir_estado:
            switch.configure(
                text=(
                    "Ativado"
                    if ativo
                    else "Desativado"
                )
            )

        if ativo:
            switch.configure(
                fg_color=Colors.PRIMARY,
                progress_color=Colors.PRIMARY,
                border_color=Colors.PRIMARY,
                button_color=Colors.CONTROL_KNOB,
                button_hover_color=Colors.CONTROL_KNOB,
                text_color=Colors.TEXT_PRIMARY
            )
            return

        if Colors.TEMA_ATUAL == "claro":
            switch.configure(
                fg_color=Colors.BUTTON,
                progress_color=Colors.PRIMARY,
                border_color=Colors.TEXT_DISABLED,
                button_color=Colors.TEXT_SECONDARY,
                button_hover_color=Colors.TEXT_SECONDARY,
                text_color=Colors.TEXT_PRIMARY
            )
            return

        switch.configure(
            fg_color=Colors.BUTTON,
            progress_color=Colors.PRIMARY,
            border_color=Colors.BORDER,
            button_color=Colors.CONTROL_KNOB,
            button_hover_color=Colors.CONTROL_KNOB,
            text_color=Colors.TEXT_PRIMARY
        )

    def salvar_configuracoes(self):
        escala_percentual = self.ESCALAS_INTERFACE[
            self.escala_interface_var.get()
        ]
        tema_interface = self.TEMAS_INTERFACE[
            self.tema_interface_var.get()
        ]

        try:
            self._validar_configuracao_login()
            caminhos = (
                self._validar_caminhos_para_salvar()
            )
            nomes_arquivos_teste = (
                self
                ._validar_nomes_arquivos_teste_para_salvar()
            )
            exportacao = (
                self._obter_configuracao_exportacao()
            )
            supervisao = (
                self.configuracoes_service
                .validar_supervisao(
                    {
                        "nome":
                            self.supervisora_nome_var.get(),
                        "telefone":
                            self.supervisora_telefone_var.get(),
                        "email":
                            self.supervisora_email_var.get()
                    }
                )
            )
        except Exception as erro:
            mostrar_dialogo_arbohub(
                master=self.winfo_toplevel(),
                titulo="Configurações não salvas",
                mensagem=(
                    "Revise o acesso ao SINAN, as notificações, "
                    "a supervisão, as pastas, os nomes dos arquivos "
                    "e os tempos operacionais.\n\n"
                    f"Detalhe: {erro}"
                ),
                tipo="erro",
                texto_botao="Entendi"
            )
            return

        configuracoes = {
            "versao": (
                self.configuracoes_service
                .VERSAO_CONFIGURACOES
            ),
            "geral": {
                "pagina_inicial": self.PAGINAS[
                    self.pagina_inicial_var.get()
                ],
                "abrir_maximizado": (
                    self.abrir_maximizado_var.get()
                )
            },
            "aparencia": {
                "tema": tema_interface,
                "escala_percentual": escala_percentual
            },
            "dashboard": {
                "atualizacao_automatica": (
                    self.dashboard_automatico_var.get()
                ),
                "intervalo_segundos": self.INTERVALOS[
                    self.intervalo_dashboard_var.get()
                ]
            },
            "sinan": {
                "login_automatico": (
                    self.login_automatico_var.get()
                )
            },
            "notificacoes": {
                "som_conclusao": (
                    self.som_conclusao_var.get()
                ),
                "som_atencao": (
                    self.som_atencao_var.get()
                ),
                "som_exportacao_disponivel": (
                    self.som_exportacao_disponivel_var.get()
                ),
                "supervisao": supervisao
            },
            "operacional": {
                "caminhos": caminhos,
                "nomes_arquivos_teste": nomes_arquivos_teste,
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

        reiniciar_agora = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Configurações salvas",
            mensagem=(
                "Configurações salvas com sucesso.\n\n"
                "Deseja reiniciar o ArboHub agora para aplicar "
                "as alterações?\n\n"
                "Se houver uma rotina em andamento, escolha Depois."
            ),
            tipo="sucesso",
            texto_confirmar="Reiniciar agora",
            texto_cancelar="Depois"
        )

        if (
            reiniciar_agora
            and callable(self.ao_reiniciar)
        ):
            self.ao_reiniciar()



    def restaurar_padroes(self):
        confirmou = solicitar_confirmacao_arbohub(
            master=self.winfo_toplevel(),
            titulo="Restaurar configurações?",
            mensagem=(
                "As preferências gerais, o tema, a escala da interface, "
                "o login automático, os sons, os contatos de supervisão, "
                "os caminhos, os nomes dos DBFs de teste e os tempos "
                "da exportação voltarão aos "
                "valores padrão.\n\n"
                "A credencial protegida pelo Windows será preservada, "
                "mas o login automático ficará desativado. Nenhum "
                "banco, relatório, ZIP ou DBF será alterado."
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
        aparencia = self.configuracoes[
            "aparencia"
        ]
        dashboard = self.configuracoes[
            "dashboard"
        ]
        sinan = self.configuracoes[
            "sinan"
        ]
        notificacoes = self.configuracoes[
            "notificacoes"
        ]
        supervisao = notificacoes[
            "supervisao"
        ]
        operacional = self.configuracoes[
            "operacional"
        ]
        caminhos = operacional[
            "caminhos"
        ]
        nomes_arquivos_teste = operacional[
            "nomes_arquivos_teste"
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
        self.tema_interface_var.set(
            self.TEMAS_INTERFACE_INVERSOS.get(
                str(
                    aparencia.get(
                        "tema",
                        "escuro"
                    )
                ),
                "Escuro"
            )
        )
        self.escala_interface_var.set(
            self.ESCALAS_INTERFACE_INVERSAS.get(
                int(
                    aparencia.get(
                        "escala_percentual",
                        100
                    )
                ),
                "100% — recomendada"
            )
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
        self.login_automatico_var.set(
            bool(
                sinan.get(
                    "login_automatico",
                    False
                )
            )
        )
        self.senha_sinan_var.set("")
        self._atualizar_status_credencial()

        self.som_conclusao_var.set(
            bool(
                notificacoes.get(
                    "som_conclusao",
                    True
                )
            )
        )
        self.som_atencao_var.set(
            bool(
                notificacoes.get(
                    "som_atencao",
                    True
                )
            )
        )
        self.som_exportacao_disponivel_var.set(
            bool(
                notificacoes.get(
                    "som_exportacao_disponivel",
                    False
                )
            )
        )
        self.supervisora_nome_var.set(
            str(
                supervisao.get(
                    "nome",
                    ""
                )
            )
        )
        self.supervisora_telefone_var.set(
            str(
                supervisao.get(
                    "telefone",
                    ""
                )
            )
        )
        self.supervisora_email_var.set(
            str(
                supervisao.get(
                    "email",
                    ""
                )
            )
        )

        if self.label_status_som is not None:
            self.label_status_som.configure(
                text=(
                    "○ Padrões restaurados — use “Testar” "
                    "para conferir."
                ),
                text_color=Colors.TEXT_MUTED
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

        for chave, nome in nomes_arquivos_teste.items():
            self.nomes_arquivos_teste_vars[
                chave
            ].set(
                str(nome)
            )
            self._atualizar_previa_nome_arquivo(
                chave
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
                "As configurações padrão foram restauradas. O tema "
                "voltou para Escuro, a escala voltou para 100% e o "
                "login automático foi desativado, "
                "os contatos de supervisão foram limpos e os sons "
                "voltaram ao padrão. A credencial segura continua "
                "preservada no Windows.\n\n"
                "Feche e abra o ArboHub para aplicar o tema Escuro "
                "e a escala de 100%. "
                "Os nomes dos DBFs de teste também voltaram ao "
                "padrão. Teste as quatro pastas operacionais antes "
                "de iniciar uma nova rotina de Bases."
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
            hover_color=Colors.WARNING_HOVER,
            text_color=Colors.TEXT_ON_PRIMARY,
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
