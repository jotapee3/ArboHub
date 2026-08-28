from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk
from PIL import Image, ImageDraw

from app.gui.themes.colors import Colors


TAMANHO_BASE = 24
ESCALA_DESENHO = 4


def criar_icone_navegacao(
    nome: str,
    *,
    tamanho: int = 20,
    ativo: bool = False,
) -> ctk.CTkImage:
    """Cria um ícone monocromático que acompanha os temas do ArboHub."""

    chave_cor = "PRIMARY" if ativo else "TEXT_SECONDARY"
    cor_clara = Colors.PALETAS["claro"][chave_cor]
    cor_escura = Colors.PALETAS["escuro"][chave_cor]

    return ctk.CTkImage(
        light_image=_criar_imagem(nome, cor_clara),
        dark_image=_criar_imagem(nome, cor_escura),
        size=(tamanho, tamanho),
    )


def _criar_imagem(nome: str, cor: str) -> Image.Image:
    tamanho = TAMANHO_BASE * ESCALA_DESENHO
    imagem = Image.new(
        "RGBA",
        (tamanho, tamanho),
        (0, 0, 0, 0),
    )
    desenho = ImageDraw.Draw(imagem)

    desenhistas: dict[
        str,
        Callable[[ImageDraw.ImageDraw, str], None],
    ] = {
        "inicio": _desenhar_inicio,
        "sinan": _desenhar_banco,
        "gal": _desenhar_laboratorio,
        "qualifica": _desenhar_grafico,
        "historico": _desenhar_historico,
        "configuracoes": _desenhar_configuracoes,
        "calendario": _desenhar_calendario,
    }
    desenhista = desenhistas.get(
        nome,
        _desenhar_padrao,
    )
    desenhista(desenho, cor)

    return imagem.resize(
        (TAMANHO_BASE, TAMANHO_BASE),
        Image.Resampling.LANCZOS,
    )


def _ponto(x: float, y: float) -> tuple[int, int]:
    return (
        round(x * ESCALA_DESENHO),
        round(y * ESCALA_DESENHO),
    )


def _linha(
    desenho: ImageDraw.ImageDraw,
    pontos: tuple[tuple[float, float], ...],
    cor: str,
    *,
    largura: float = 1.8,
):
    desenho.line(
        [_ponto(x, y) for x, y in pontos],
        fill=cor,
        width=round(largura * ESCALA_DESENHO),
        joint="curve",
    )


def _caixa(
    esquerda: float,
    topo: float,
    direita: float,
    base: float,
) -> tuple[int, int, int, int]:
    return (
        *_ponto(esquerda, topo),
        *_ponto(direita, base),
    )


def _desenhar_inicio(desenho: ImageDraw.ImageDraw, cor: str):
    _linha(
        desenho,
        ((3.5, 11), (12, 4), (20.5, 11)),
        cor,
    )
    _linha(
        desenho,
        ((5.5, 10), (5.5, 20), (18.5, 20), (18.5, 10)),
        cor,
    )
    _linha(
        desenho,
        ((10, 20), (10, 14), (14, 14), (14, 20)),
        cor,
    )


def _desenhar_banco(desenho: ImageDraw.ImageDraw, cor: str):
    largura = round(1.7 * ESCALA_DESENHO)
    desenho.ellipse(
        _caixa(4, 3.5, 20, 9),
        outline=cor,
        width=largura,
    )
    _linha(desenho, ((4, 6.2), (4, 17.8)), cor, largura=1.7)
    _linha(desenho, ((20, 6.2), (20, 17.8)), cor, largura=1.7)
    desenho.arc(
        _caixa(4, 8.5, 20, 14),
        start=0,
        end=180,
        fill=cor,
        width=largura,
    )
    desenho.arc(
        _caixa(4, 14.5, 20, 20),
        start=0,
        end=180,
        fill=cor,
        width=largura,
    )


def _desenhar_laboratorio(desenho: ImageDraw.ImageDraw, cor: str):
    _linha(desenho, ((9, 3.5), (15, 3.5)), cor)
    _linha(desenho, ((10, 3.5), (10, 9), (4.8, 18.2)), cor)
    _linha(desenho, ((14, 3.5), (14, 9), (19.2, 18.2)), cor)
    _linha(
        desenho,
        ((4.8, 18.2), (5.4, 20.3), (18.6, 20.3), (19.2, 18.2)),
        cor,
    )
    _linha(desenho, ((7.2, 15), (16.8, 15)), cor)


def _desenhar_grafico(desenho: ImageDraw.ImageDraw, cor: str):
    _linha(desenho, ((4, 4), (4, 20), (20, 20)), cor)
    _linha(
        desenho,
        ((6.5, 16), (10.2, 12), (13.2, 14), (18.5, 7)),
        cor,
        largura=2,
    )
    desenho.ellipse(
        _caixa(17.2, 5.7, 19.8, 8.3),
        fill=cor,
    )


def _desenhar_historico(desenho: ImageDraw.ImageDraw, cor: str):
    largura = round(1.8 * ESCALA_DESENHO)
    desenho.arc(
        _caixa(4, 4, 20, 20),
        start=35,
        end=325,
        fill=cor,
        width=largura,
    )
    _linha(desenho, ((4, 9), (4, 4.5), (8.5, 4.5)), cor)
    _linha(desenho, ((12, 7.5), (12, 12.2), (15.5, 14.2)), cor)


def _desenhar_configuracoes(
    desenho: ImageDraw.ImageDraw,
    cor: str,
):
    largura = round(1.7 * ESCALA_DESENHO)
    desenho.ellipse(
        _caixa(7.5, 7.5, 16.5, 16.5),
        outline=cor,
        width=largura,
    )
    desenho.ellipse(
        _caixa(10.4, 10.4, 13.6, 13.6),
        fill=cor,
    )
    for inicio, fim in (
        ((12, 3), (12, 6)),
        ((12, 18), (12, 21)),
        ((3, 12), (6, 12)),
        ((18, 12), (21, 12)),
        ((5.6, 5.6), (7.7, 7.7)),
        ((16.3, 16.3), (18.4, 18.4)),
        ((18.4, 5.6), (16.3, 7.7)),
        ((7.7, 16.3), (5.6, 18.4)),
    ):
        _linha(desenho, (inicio, fim), cor, largura=1.7)


def _desenhar_calendario(desenho: ImageDraw.ImageDraw, cor: str):
    largura = round(1.7 * ESCALA_DESENHO)
    desenho.rounded_rectangle(
        _caixa(3.5, 5.5, 20.5, 20.5),
        radius=round(2 * ESCALA_DESENHO),
        outline=cor,
        width=largura,
    )
    _linha(desenho, ((3.5, 10), (20.5, 10)), cor, largura=1.7)
    _linha(desenho, ((8, 3.5), (8, 7.5)), cor, largura=1.7)
    _linha(desenho, ((16, 3.5), (16, 7.5)), cor, largura=1.7)
    desenho.ellipse(_caixa(7, 13, 9, 15), fill=cor)
    desenho.ellipse(_caixa(11, 13, 13, 15), fill=cor)
    desenho.ellipse(_caixa(15, 13, 17, 15), fill=cor)


def _desenhar_padrao(desenho: ImageDraw.ImageDraw, cor: str):
    desenho.rounded_rectangle(
        _caixa(4, 4, 20, 20),
        radius=round(3 * ESCALA_DESENHO),
        outline=cor,
        width=round(1.8 * ESCALA_DESENHO),
    )
