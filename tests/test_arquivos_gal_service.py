from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from app.services.arquivos_gal_service import ArquivosGalService


class ArquivosGalServiceTestCase(unittest.TestCase):
    def test_intervalo_semanal_avanca_na_segunda_feira(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            service = ArquivosGalService(
                pasta_historico=raiz / "historico",
                pasta_banco_atual=raiz / "banco_atual",
                pasta_teste_soro=raiz / "teste_soro"
            )

            self.assertEqual(
                service.intervalo_semanal(date(2026, 8, 12)),
                (date(2026, 8, 3), date(2026, 8, 10))
            )
            self.assertEqual(
                service.intervalo_semanal(date(2026, 8, 17)),
                (date(2026, 8, 10), date(2026, 8, 17))
            )

    def test_compara_assinatura_sem_interpretar_csv(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            service = ArquivosGalService()
            arquivo = raiz / "relatorio.csv"
            referencia = b"referencia-binaria-sem-dados-clinicos"
            diferente = b"arquivo-binario-diferente"
            assinatura_original = service.CSV_VAZIO_SHA256

            try:
                service.CSV_VAZIO_SHA256 = hashlib.sha256(
                    referencia
                ).hexdigest()
                arquivo.write_bytes(referencia)

                self.assertTrue(
                    service.corresponde_ao_csv_vazio(arquivo)
                )

                arquivo.write_bytes(diferente)

                self.assertFalse(
                    service.corresponde_ao_csv_vazio(arquivo)
                )
            finally:
                service.CSV_VAZIO_SHA256 = assinatura_original

    def test_processamento_cria_e_substitui_zip_semanal(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta_historico = raiz / "historico"
            pasta_banco_atual = raiz / "banco_atual"
            pasta_teste_soro = raiz / "teste_soro"
            pasta_teste_soro.mkdir(parents=True)

            service = ArquivosGalService(
                pasta_historico=pasta_historico,
                pasta_banco_atual=pasta_banco_atual,
                pasta_teste_soro=pasta_teste_soro
            )
            referencia = date(2026, 8, 12)
            pasta_mes = service.pasta_historico_mes(
                date(2026, 8, 10)
            )
            pasta_mes.mkdir(parents=True)
            historico_solto = pasta_mes / "gal_2026-08-10.csv"
            historico_solto.write_bytes(b"legado\n")

            relatorio = raiz / "relatorio.csv"
            conteudo_inicial = b"coluna\nprimeira-versao\n"
            relatorio.write_bytes(conteudo_inicial)

            resultado = service.processar_download(
                relatorio,
                data_referencia=referencia
            )

            arquivo_zip = Path(resultado["arquivo_historico"])
            self.assertEqual(
                arquivo_zip.name,
                "gal_2026-08-10.zip"
            )
            self.assertFalse(historico_solto.exists())
            self.assertEqual(
                Path(resultado["arquivo_banco_atual"]).read_bytes(),
                conteudo_inicial
            )
            self.assertEqual(
                Path(resultado["arquivo_teste"]).read_bytes(),
                conteudo_inicial
            )
            self._assert_zip_semanal(
                arquivo_zip,
                "gal_2026-08-10.csv",
                conteudo_inicial
            )

            conteudo_novo = b"coluna\nsegunda-versao\n"
            relatorio.write_bytes(conteudo_novo)
            resultado_novo = service.processar_download(
                relatorio,
                data_referencia=referencia,
                data_inicio=date(2026, 7, 27)
            )

            self.assertEqual(
                resultado_novo["data_inicio"],
                date(2026, 7, 27)
            )

            self._assert_zip_semanal(
                arquivo_zip,
                "gal_2026-08-10.csv",
                conteudo_novo
            )

    def _assert_zip_semanal(
        self,
        caminho: Path,
        membro_esperado: str,
        conteudo_esperado: bytes
    ):
        with zipfile.ZipFile(caminho) as arquivo_zip:
            self.assertEqual(
                arquivo_zip.namelist(),
                [membro_esperado]
            )
            self.assertEqual(
                arquivo_zip.read(membro_esperado),
                conteudo_esperado
            )
            self.assertIsNone(arquivo_zip.testzip())


if __name__ == "__main__":
    unittest.main()
