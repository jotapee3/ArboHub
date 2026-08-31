from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw

from app.core.versao import ROTULO_VERSAO_ARBOHUB
from app.gui.components.icones_navegacao import (
    criar_icone_navegacao,
)
from app.gui.themes.colors import Colors


def _criar_icone_chevron(direcao: str) -> ctk.CTkImage:
    """Cria uma seta simétrica, sem depender do alinhamento da fonte."""

    def desenhar(cor: str) -> Image.Image:
        escala = 4
        imagem = Image.new(
            "RGBA",
            (24 * escala, 24 * escala),
            (0, 0, 0, 0),
        )
        desenho = ImageDraw.Draw(imagem)
        if direcao == "esquerda":
            pontos = ((15, 6), (9, 12), (15, 18))
        else:
            pontos = ((9, 6), (15, 12), (9, 18))
        desenho.line(
            [(x * escala, y * escala) for x, y in pontos],
            fill=cor,
            width=round(1.9 * escala),
            joint="curve",
        )
        return imagem.resize(
            (24, 24),
            Image.Resampling.LANCZOS,
        )

    return ctk.CTkImage(
        light_image=desenhar(
            Colors.PALETAS["claro"]["TEXT_SECONDARY"]
        ),
        dark_image=desenhar(
            Colors.PALETAS["escuro"]["TEXT_SECONDARY"]
        ),
        size=(18, 18),
    )


class Sidebar(ctk.CTkFrame):
    """Navegação lateral que se expande ou recolhe por clique."""

    LARGURA_RECOLHIDA = 72
    LARGURA_EXPANDIDA = 230
    TAMANHO_ICONE_LOGO = 46

    def __init__(
        self,
        master,
        comando_inicio,
        comando_sinan,
        comando_gal,
        comando_qualifica,
        comando_historico,
        comando_configuracoes,
    ):
        super().__init__(
            master,
            width=self.LARGURA_RECOLHIDA,
            corner_radius=0,
            fg_color=Colors.SIDEBAR,
            border_width=0,
        )

        self.pack_propagate(False)
        self.grid_propagate(False)

        self.comandos = {
            "inicio": comando_inicio,
            "sinan": comando_sinan,
            "gal": comando_gal,
            "qualifica": comando_qualifica,
            "historico": comando_historico,
            "configuracoes": comando_configuracoes,
        }
        self.rotulos = {
            "inicio": "Início",
            "sinan": "SINAN",
            "gal": "GAL",
            "qualifica": "Qualifica",
            "historico": "Histórico",
            "configuracoes": "Configurações",
        }

        self.botao_ativo = None
        self.chave_ativa: str | None = None
        self.imagem_logo = None
        self._expandida = False
        self._botoes: dict[str, ctk.CTkButton] = {}
        self._icones_normais: dict[str, ctk.CTkImage] = {}
        self._icones_ativos: dict[str, ctk.CTkImage] = {}

        self._criar_icones()
        self._criar_cabecalho()
        self._criar_controle_expansao()
        self._criar_menu()
        self._criar_rodape()
        self._aplicar_estado_visual(expandida=False)

    def _criar_icones(self):
        for chave in self.rotulos:
            self._icones_normais[chave] = criar_icone_navegacao(
                chave,
                tamanho=20,
                ativo=False,
            )
            self._icones_ativos[chave] = criar_icone_navegacao(
                chave,
                tamanho=20,
                ativo=True,
            )
        self._icone_expandir = _criar_icone_chevron("direita")
        self._icone_recolher = _criar_icone_chevron("esquerda")

    def _criar_cabecalho(self):
        self.cabecalho = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.cabecalho.pack(
            fill="x",
            padx=10,
            pady=(20, 12),
        )

        self.marca = ctk.CTkFrame(
            self.cabecalho,
            fg_color="transparent",
            height=52,
        )
        self.marca.pack(fill="x")
        self.marca.pack_propagate(False)

        pasta_assets = (
            Path(__file__).resolve().parent.parent
            / "assets"
        )
        imagem_clara = self._preparar_logo(
            pasta_assets / "arbohub_icon_light.png"
        )
        imagem_escura = self._preparar_logo(
            pasta_assets / "arbohub_icon_dark.png"
        )
        self.imagem_logo = ctk.CTkImage(
            light_image=imagem_clara,
            dark_image=imagem_escura,
            size=(self.TAMANHO_ICONE_LOGO,) * 2,
        )

        self.label_logo = ctk.CTkLabel(
            self.marca,
            text="",
            image=self.imagem_logo,
            width=52,
            height=52,
            fg_color="transparent",
        )
        self.label_logo.pack(side="left")

        self.label_nome = ctk.CTkLabel(
            self.marca,
            text="ArboHub",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=25,
                weight="bold",
            ),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )

        self.label_subtitulo = ctk.CTkLabel(
            self.cabecalho,
            text="Software para vigilância em saúde",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=11,
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )

        self.divisor_cabecalho = ctk.CTkFrame(
            self.cabecalho,
            height=1,
            fg_color=Colors.DIVIDER,
        )

    @staticmethod
    def _preparar_logo(caminho: Path) -> Image.Image:
        imagem_original = Image.open(caminho).convert("RGBA")
        caixa_conteudo = imagem_original.getchannel("A").getbbox()
        if caixa_conteudo is not None:
            imagem_original = imagem_original.crop(caixa_conteudo)

        largura, altura = imagem_original.size
        tamanho_quadrado = max(largura, altura)
        imagem_quadrada = Image.new(
            mode="RGBA",
            size=(tamanho_quadrado, tamanho_quadrado),
            color=(0, 0, 0, 0),
        )
        imagem_quadrada.paste(
            imagem_original,
            (
                (tamanho_quadrado - largura) // 2,
                (tamanho_quadrado - altura) // 2,
            ),
            imagem_original,
        )
        return imagem_quadrada

    def _criar_menu(self):
        self.menu = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.menu.pack(fill="x", padx=10, pady=(8, 0))

        for chave in ("inicio", "sinan", "gal", "qualifica"):
            self._botoes[chave] = self._criar_botao_menu(
                self.menu,
                chave,
                altura=44,
            )

        self.botao_inicio = self._botoes["inicio"]
        self.botao_sinan = self._botoes["sinan"]
        self.botao_gal = self._botoes["gal"]
        self.botao_qualifica = self._botoes["qualifica"]

    def _criar_controle_expansao(self):
        self.botao_alternar = ctk.CTkButton(
            self,
            text="",
            image=self._icone_expandir,
            command=self.alternar_expansao,
            width=52,
            height=40,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            border_width=0,
            anchor="center",
        )
        self.botao_alternar.pack(
            anchor="center",
            padx=10,
            pady=(0, 6),
        )

    def _criar_botao_menu(
        self,
        master,
        chave: str,
        *,
        altura: int,
    ) -> ctk.CTkButton:
        botao = ctk.CTkButton(
            master,
            text=self.rotulos[chave],
            image=self._icones_normais[chave],
            compound="left",
            command=self.comandos[chave],
            height=altura,
            corner_radius=7,
            fg_color="transparent",
            hover_color=Colors.SURFACE_HOVER,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=13,
                weight="bold",
            ),
            anchor="w",
        )
        botao.pack(fill="x", pady=3)
        return botao

    def _criar_rodape(self):
        self.rodape = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.rodape.pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=16,
        )

        self.divisor_rodape = ctk.CTkFrame(
            self.rodape,
            height=1,
            fg_color=Colors.DIVIDER,
        )
        self.divisor_rodape.pack(
            fill="x",
            padx=4,
            pady=(0, 8),
        )

        for chave in ("historico", "configuracoes"):
            self._botoes[chave] = self._criar_botao_menu(
                self.rodape,
                chave,
                altura=38,
            )

        self.botao_historico = self._botoes["historico"]
        self.botao_configuracoes = self._botoes["configuracoes"]

        self.label_status = ctk.CTkLabel(
            self.rodape,
            text="● Sistema disponível",
            font=ctk.CTkFont(
                family="Segoe UI",
                size=10,
            ),
            text_color=Colors.SUCCESS,
            anchor="w",
            height=28,
        )
        self.label_status.pack(fill="x", padx=7, pady=(6, 0))

        self.label_versao = ctk.CTkLabel(
            self.rodape,
            text=ROTULO_VERSAO_ARBOHUB,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=9,
            ),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )

    def selecionar_botao(self, chave: str):
        if self.chave_ativa is not None:
            anterior = self._botoes[self.chave_ativa]
            anterior.configure(
                fg_color="transparent",
                text_color=Colors.TEXT_SECONDARY,
                image=self._icones_normais[self.chave_ativa],
            )

        atual = self._botoes[chave]
        atual.configure(
            fg_color=Colors.SURFACE_SELECTED,
            text_color=Colors.PRIMARY,
            image=self._icones_ativos[chave],
        )
        self.botao_ativo = atual
        self.chave_ativa = chave

    def selecionar_inicio(self):
        self.selecionar_botao("inicio")

    def selecionar_sinan(self):
        self.selecionar_botao("sinan")

    def selecionar_gal(self):
        self.selecionar_botao("gal")

    def selecionar_qualifica(self):
        self.selecionar_botao("qualifica")

    def selecionar_historico(self):
        self.selecionar_botao("historico")

    def selecionar_configuracoes(self):
        self.selecionar_botao("configuracoes")

    # ------------------------------------------------------------------
    # Expansão e recolhimento por clique
    # ------------------------------------------------------------------

    def alternar_expansao(self):
        if self._expandida:
            self.recolher()
        else:
            self.expandir()

    def expandir(self):
        if self._expandida:
            return
        self._expandida = True
        self.configure(width=self.LARGURA_EXPANDIDA)
        self.after_idle(
            self._concluir_expansao
        )

    def recolher(self):
        if not self._expandida:
            return
        self._expandida = False
        self._aplicar_estado_visual(expandida=False)
        self.after_idle(
            self._concluir_recolhimento
        )

    def _concluir_expansao(self):
        if self._expandida:
            self._aplicar_estado_visual(expandida=True)

    def _concluir_recolhimento(self):
        if not self._expandida:
            self.configure(width=self.LARGURA_RECOLHIDA)

    def _aplicar_estado_visual(self, *, expandida: bool):
        if expandida:
            if not self.label_nome.winfo_manager():
                self.label_nome.pack(
                    side="left",
                    padx=(9, 0),
                )
            if not self.label_subtitulo.winfo_manager():
                self.label_subtitulo.pack(
                    fill="x",
                    pady=(6, 0),
                )
            if not self.divisor_cabecalho.winfo_manager():
                self.divisor_cabecalho.pack(
                    fill="x",
                    padx=4,
                    pady=(14, 0),
                )
            if not self.label_versao.winfo_manager():
                self.label_versao.pack(
                    fill="x",
                    padx=7,
                    pady=(2, 0),
                )
            self.label_status.configure(
                text="● Sistema disponível",
                anchor="w",
            )
        else:
            self.label_nome.pack_forget()
            self.label_subtitulo.pack_forget()
            self.divisor_cabecalho.pack_forget()
            self.label_versao.pack_forget()
            self.label_status.configure(
                text="●",
                anchor="center",
            )

        for chave, botao in self._botoes.items():
            botao.configure(
                text=self.rotulos[chave] if expandida else "",
                anchor="w" if expandida else "center",
                width=(
                    self.LARGURA_EXPANDIDA - 20
                    if expandida
                    else 52
                ),
            )

        self.botao_alternar.configure(
            image=(
                self._icone_recolher
                if expandida
                else self._icone_expandir
            ),
        )
        self.botao_alternar.pack_configure(
            anchor="e" if expandida else "center",
            padx=(0, 10) if expandida else 10,
        )
