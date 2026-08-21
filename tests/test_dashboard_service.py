from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
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
            dashboard.marcar_gal_concluido(
                referencia,
                data_inicio=date(2026, 7, 27),
                data_fim=date(2026, 8, 10)
            )

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
            self.assertEqual(
                estado_antes["gal"]["data_inicio"],
                date(2026, 7, 27)
            )
            self.assertEqual(
                estado_antes["gal"]["data_fim"],
                date(2026, 8, 10)
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
            self.assertIsNone(
                estado_depois["gal"]["data_inicio"]
            )
            self.assertIsNone(
                estado_depois["gal"]["data_fim"]
            )

    def test_atividades_recentes_limitam_e_agrupam_tres_dias(self):
        with tempfile.TemporaryDirectory() as temporario:
            banco = Path(temporario) / "arbohub_teste.db"
            dashboard = DashboardService(caminho_banco=banco)

            with dashboard.conectar() as conexao:
                for dia in range(20, 16, -1):
                    referencia = date(2026, 8, dia)
                    horario = datetime(2026, 8, dia, 8, 30)
                    conexao.execute(
                        """
                            INSERT INTO rotina_diaria (
                                data_referencia,
                                verificacao_obitos,
                                verificacao_obitos_em
                            )
                            VALUES (?, 1, ?)
                        """,
                        (
                            referencia.isoformat(),
                            horario.isoformat(timespec="seconds")
                        )
                    )
                conexao.commit()

            atividades = dashboard.obter_atividades_recentes(
                limite=6,
                limite_dias=3
            )
            grupos = dashboard.agrupar_atividades_por_dia(
                atividades,
                hoje=date(2026, 8, 20)
            )

            self.assertEqual(len(atividades), 3)
            self.assertEqual(
                [grupo["rotulo"] for grupo in grupos],
                ["Hoje", "Ontem", "18 de agosto"]
            )
            self.assertEqual(
                [grupo["quantidade"] for grupo in grupos],
                [1, 1, 1]
            )


if __name__ == "__main__":
    unittest.main()
