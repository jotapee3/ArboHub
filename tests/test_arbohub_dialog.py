from __future__ import annotations

import sys
import types
import unittest


try:
    import customtkinter  # noqa: F401
except ModuleNotFoundError:
    sys.modules["customtkinter"] = types.SimpleNamespace(
        CTkToplevel=object
    )

from app.gui.components.arbohub_dialog import ArboHubDialog


class _CaixaMensagemFake:
    def __init__(self, largura: int):
        self.largura = largura

    def winfo_width(self) -> int:
        return self.largura


class _LabelMensagemFake:
    def __init__(self, escala: float):
        self.escala = escala
        self.wraplength = None

    def _reverse_widget_scaling(self, valor: float) -> float:
        return valor / self.escala

    def configure(self, *, wraplength: int):
        self.wraplength = wraplength


class ArboHubDialogTestCase(unittest.TestCase):
    def test_quebra_de_linha_respeita_escala_da_interface(self):
        dialogo = types.SimpleNamespace(
            caixa_mensagem=_CaixaMensagemFake(494),
            label_mensagem=_LabelMensagemFake(1.25),
            MARGEM_INTERNA_MENSAGEM=44,
        )

        ArboHubDialog._ajustar_quebra_mensagem(dialogo)

        self.assertEqual(
            dialogo.label_mensagem.wraplength,
            360,
        )

    def test_quebra_de_linha_ignora_caixa_ainda_nao_mapeada(self):
        dialogo = types.SimpleNamespace(
            caixa_mensagem=_CaixaMensagemFake(1),
            label_mensagem=_LabelMensagemFake(1.25),
            MARGEM_INTERNA_MENSAGEM=44,
        )

        ArboHubDialog._ajustar_quebra_mensagem(dialogo)

        self.assertIsNone(
            dialogo.label_mensagem.wraplength
        )


if __name__ == "__main__":
    unittest.main()
