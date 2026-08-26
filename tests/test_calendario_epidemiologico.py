from __future__ import annotations

import unittest
from datetime import date

from app.services.qualifica.calendario_epidemiologico import (
    CalendarioEpidemiologico,
)


class CalendarioEpidemiologicoTestCase(unittest.TestCase):
    def test_inicio_pode_ocorrer_no_ano_anterior(self):
        self.assertEqual(
            CalendarioEpidemiologico.inicio_do_ano(2025),
            date(2024, 12, 29),
        )
        self.assertEqual(
            CalendarioEpidemiologico.inicio_do_ano(2026),
            date(2026, 1, 4),
        )

    def test_ano_pode_ter_cinquenta_e_duas_ou_tres_semanas(self):
        self.assertEqual(
            CalendarioEpidemiologico.quantidade_de_semanas(2025),
            53,
        )
        self.assertEqual(
            CalendarioEpidemiologico.quantidade_de_semanas(2026),
            52,
        )

    def test_semana_comeca_domingo_e_termina_sabado(self):
        semana = CalendarioEpidemiologico.obter_semana(2025, 53)

        self.assertEqual(semana.data_inicial, date(2025, 12, 28))
        self.assertEqual(semana.data_final, date(2026, 1, 3))

    def test_rejeita_semana_inexistente(self):
        with self.assertRaisesRegex(ValueError, "possui 52 semanas"):
            CalendarioEpidemiologico.obter_semana(2026, 53)


if __name__ == "__main__":
    unittest.main()
