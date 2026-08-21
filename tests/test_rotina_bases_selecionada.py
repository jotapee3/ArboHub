from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.services.rotina_bases_service import RotinaBasesService
from app.services.selecao_destinos_bases import SelecaoDestinosBases


class _RegistroFalso:
    def obter_lote_completo_do_dia(self, data_referencia):
        return None

    def obter_lote_parcial_do_dia(self, data_referencia):
        return None


class _ArquivosFalso:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.instalacoes_bases: list[str] = []
        self.instalacoes_bancos: list[str] = []
        self.validacoes: list[str] = []
        self.arquivamentos: list[str] = []

        for agravo in ("dengue", "chikungunya"):
            caminho = self.caminho_historico(
                agravo=agravo,
                data_referencia=date(2026, 8, 21)
            )
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(b"zip-sintetico")

    def validar_destinos_operacionais(self, **opcoes):
        return opcoes

    def caminho_historico(self, agravo, data_referencia):
        return self.raiz / "historico" / f"{agravo}.zip"

    def validar_extracao_agravo_zip(
        self,
        caminho_zip,
        agravo,
        data_referencia
    ):
        self.validacoes.append(agravo)
        return {
            "nome_interno": f"{agravo}.dbf",
            "registros_lidos": False
        }

    def zip_contem_dbf_do_agravo(self, caminho_zip, agravo):
        return Path(caminho_zip).is_file()

    def instalar_dbf_agravo_pasta_teste(
        self,
        agravo,
        data_referencia,
        caminho_zip
    ):
        self.instalacoes_bases.append(agravo)
        return {"destino": self.raiz / f"base-{agravo}.dbf"}

    def instalar_dbf_agravo_bancos_atuais(
        self,
        agravo,
        data_referencia,
        caminho_zip
    ):
        self.instalacoes_bancos.append(agravo)
        return {"destino": self.raiz / f"banco-{agravo}.dbf"}

    def arquivar_agravo(self, **opcoes):
        self.arquivamentos.append(str(opcoes["agravo"]))
        return {"caminho": Path(opcoes["caminho_zip"])}


class RotinaBasesSelecionadaTestCase(unittest.TestCase):
    DATA_REFERENCIA = date(2026, 8, 21)

    def test_selecao_completa_preserva_os_tres_destinos(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivos = _ArquivosFalso(Path(temporario))
            service = RotinaBasesService(
                registro_service=_RegistroFalso(),
                arquivos_service=arquivos
            )

            resultado = service.executar_rotina_selecionada(
                selecao_destinos=SelecaoDestinosBases.completa(),
                data_referencia=self.DATA_REFERENCIA
            )

            self.assertEqual(
                set(resultado["historico"]),
                {"dengue", "chikungunya"}
            )
            self.assertEqual(
                set(arquivos.instalacoes_bases),
                {"dengue", "chikungunya"}
            )
            self.assertEqual(
                set(arquivos.instalacoes_bancos),
                {"dengue", "chikungunya"}
            )

    def test_somente_dengue_dbf_nao_altera_outros_destinos(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivos = _ArquivosFalso(Path(temporario))
            service = RotinaBasesService(
                registro_service=_RegistroFalso(),
                arquivos_service=arquivos
            )
            eventos = []
            selecao = SelecaoDestinosBases(
                atualizar_historico=False,
                agravos_bases_dbf=frozenset({"dengue"}),
                atualizar_bancos_atuais=False
            )

            resultado = service.executar_rotina_selecionada(
                selecao_destinos=selecao,
                data_referencia=self.DATA_REFERENCIA,
                ao_evento=eventos.append
            )

            self.assertTrue(resultado["concluida"])
            self.assertEqual(set(resultado["agravos"]), {"dengue"})
            self.assertEqual(arquivos.instalacoes_bases, ["dengue"])
            self.assertEqual(arquivos.instalacoes_bancos, [])
            self.assertEqual(arquivos.arquivamentos, [])
            self.assertEqual(resultado["historico"], {})
            self.assertTrue(any(
                evento.etapa == service.ETAPA_HISTORICO
                and evento.estado == service.ESTADO_IGNORADA
                for evento in eventos
            ))

    def test_historico_mantem_a_dupla_sem_instalar_bases(self):
        with tempfile.TemporaryDirectory() as temporario:
            arquivos = _ArquivosFalso(Path(temporario))
            service = RotinaBasesService(
                registro_service=_RegistroFalso(),
                arquivos_service=arquivos
            )
            selecao = SelecaoDestinosBases(
                atualizar_historico=True,
                agravos_bases_dbf=frozenset(),
                atualizar_bancos_atuais=False
            )

            resultado = service.executar_rotina_selecionada(
                selecao_destinos=selecao,
                data_referencia=self.DATA_REFERENCIA
            )

            self.assertEqual(
                set(resultado["agravos"]),
                {"dengue", "chikungunya"}
            )
            self.assertEqual(arquivos.instalacoes_bases, [])
            self.assertEqual(arquivos.instalacoes_bancos, [])
            self.assertEqual(arquivos.arquivamentos, [])
            self.assertEqual(
                set(resultado["historico"]),
                {"dengue", "chikungunya"}
            )


if __name__ == "__main__":
    unittest.main()
