from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.services.atualizacao_gal_service import AtualizacaoGalService


class _ArquivosGalFake:
    def __init__(self, vazios: set[Path]):
        self.vazios = vazios

    def corresponde_ao_csv_vazio(self, arquivo: Path) -> bool:
        return arquivo in self.vazios


class _ExportacaoGalFake:
    def __init__(self, arquivos: list[Path]):
        self.arquivos = iter(arquivos)
        self.periodos: list[tuple[date, date]] = []

    def baixar(
        self,
        pasta_temporaria: str | Path,
        data_inicio: date,
        data_fim: date,
        cancelado,
        ao_status
    ) -> Path:
        self.periodos.append((data_inicio, data_fim))
        return next(self.arquivos)


class _DashboardFake:
    pass


class AtualizacaoGalServiceTestCase(unittest.TestCase):
    def test_retrocede_segundas_ate_arquivo_diferente(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            vazio_1 = raiz / "vazio-1.csv"
            vazio_2 = raiz / "vazio-2.csv"
            diferente = raiz / "diferente.csv"
            arquivos_service = _ArquivosGalFake(
                {vazio_1, vazio_2}
            )
            exportacao = _ExportacaoGalFake(
                [vazio_1, vazio_2, diferente]
            )
            service = AtualizacaoGalService(
                arquivos_service=arquivos_service,
                dashboard_service=_DashboardFake()
            )

            arquivo, data_inicio = (
                service._baixar_ate_diferir_do_csv_vazio(
                    exportacao=exportacao,
                    pasta_temporaria=raiz,
                    data_inicio=date(2026, 8, 10),
                    data_fim=date(2026, 8, 17)
                )
            )

            self.assertEqual(arquivo, diferente)
            self.assertEqual(data_inicio, date(2026, 7, 27))
            self.assertEqual(
                exportacao.periodos,
                [
                    (date(2026, 8, 10), date(2026, 8, 17)),
                    (date(2026, 8, 3), date(2026, 8, 17)),
                    (date(2026, 7, 27), date(2026, 8, 17))
                ]
            )


if __name__ == "__main__":
    unittest.main()
