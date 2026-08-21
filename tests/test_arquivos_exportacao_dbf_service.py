from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)
from app.services.configuracoes_service import ConfiguracoesService


class ArquivosExportacaoDbfServiceTestCase(unittest.TestCase):
    DATA_REFERENCIA = date(2026, 8, 21)

    def test_valida_somente_a_base_dbf_selecionada(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta_dengue = raiz / "Dengue DBF"
            pasta_dengue.mkdir()
            service = self._criar_service(
                raiz=raiz,
                pasta_dengue=pasta_dengue,
                pasta_chiku=raiz / "Chiku DBF ausente"
            )

            validados = service.validar_destinos_operacionais(
                incluir_historico=False,
                incluir_pastas_teste=True,
                incluir_bancos_atuais=False,
                agravos_pastas_teste={"dengue"}
            )

            self.assertEqual(
                validados,
                {"teste_ab1": pasta_dengue}
            )

    def test_instala_dengue_de_zip_fonte_sem_alterar_chiku(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            pasta_dengue = raiz / "Dengue DBF"
            pasta_chiku = raiz / "Chiku DBF"
            pasta_dengue.mkdir()
            pasta_chiku.mkdir()
            service = self._criar_service(
                raiz=raiz,
                pasta_dengue=pasta_dengue,
                pasta_chiku=pasta_chiku
            )
            caminho_zip = raiz / "download_dengue.zip"

            with zipfile.ZipFile(caminho_zip, "w") as arquivo_zip:
                arquivo_zip.writestr(
                    "DENGON26.dbf",
                    b"conteudo-binario-de-teste"
                )

            self.assertTrue(
                service.zip_contem_dbf_do_agravo(
                    caminho_zip=caminho_zip,
                    agravo="dengue"
                )
            )
            self.assertFalse(
                service.zip_contem_dbf_do_agravo(
                    caminho_zip=caminho_zip,
                    agravo="chikungunya"
                )
            )

            resultado = service.instalar_dbf_agravo_pasta_teste(
                agravo="dengue",
                data_referencia=self.DATA_REFERENCIA,
                caminho_zip=caminho_zip
            )

            destino_dengue = pasta_dengue / "dengue_2026.dbf"
            destino_chiku = pasta_chiku / "chiku_2026.dbf"
            self.assertTrue(resultado["instalado"])
            self.assertEqual(
                destino_dengue.read_bytes(),
                b"conteudo-binario-de-teste"
            )
            self.assertFalse(destino_chiku.exists())
            self.assertTrue(caminho_zip.exists())
            self.assertFalse(resultado["registros_lidos"])

    def _criar_service(
        self,
        raiz: Path,
        pasta_dengue: Path,
        pasta_chiku: Path
    ) -> ArquivosExportacaoDbfService:
        pasta_bancos = raiz / "Bancos atuais"
        pasta_bancos.mkdir(exist_ok=True)

        return ArquivosExportacaoDbfService(
            raiz_staging=raiz / "staging",
            raiz_historico=raiz / "historico",
            pasta_ab1=pasta_dengue,
            pasta_ab2=pasta_chiku,
            pasta_bancos_atuais=pasta_bancos,
            nome_arquivo_ab1="dengue_{ano}.dbf",
            nome_arquivo_ab2="chiku_{ano}.dbf",
            configuracoes_service=ConfiguracoesService(
                caminho_arquivo=raiz / "configuracoes.json"
            )
        )


if __name__ == "__main__":
    unittest.main()
