from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.services.checkpoint_service import CheckpointService
from app.services.dashboard_service import DashboardService


class DashboardServiceTestCase(unittest.TestCase):
    def test_reset_gal_preserva_estado_concluido_do_sinan(self):
        with tempfile.TemporaryDirectory() as temporario:
            banco = Path(temporario) / "arbohub_teste.db"
            referencia = date(2026, 8, 10)

            checkpoints = CheckpointService(
                caminho_banco=banco
            )
            dashboard = DashboardService(
                caminho_banco=banco
            )

            checkpoints.marcar_verificacao_obitos(referencia)
            checkpoints.marcar_atualizacao_bases(referencia)
            dashboard.marcar_gal_concluido(referencia)

            estado_antes = dashboard.obter_estado_dia(
                referencia
            )
            self.assertTrue(
                estado_antes["sinan"]["concluido"]
            )
            self.assertTrue(
                estado_antes["gal"]["concluido"]
            )
            self.assertIsNotNone(
                estado_antes["gal"]["atualizacao_em"]
            )

            dashboard.resetar_gal(referencia)

            estado_depois = dashboard.obter_estado_dia(
                referencia
            )
            self.assertTrue(
                estado_depois["sinan"]["concluido"]
            )
            self.assertTrue(
                estado_depois["sinan"][
                    "verificacao_obitos"
                ]
            )
            self.assertTrue(
                estado_depois["sinan"][
                    "atualizacao_bases"
                ]
            )
            self.assertFalse(
                estado_depois["gal"]["concluido"]
            )
            self.assertIsNone(
                estado_depois["gal"]["atualizacao_em"]
            )


if __name__ == "__main__":
    unittest.main()
