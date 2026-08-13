from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from app.core.versao import ROTULO_VERSAO_ARBOHUB
from app.services.suporte_service import SuporteService


class SuporteServiceTestCase(unittest.TestCase):
    def test_email_usa_canal_institucional_sem_conta_windows(self):
        link = SuporteService().montar_link_email(
            destinatario="SUPERVISAO@EXEMPLO.GOV.BR",
            nome_destinatario="Supervisão",
        )
        endereco = urlparse(link)
        consulta = parse_qs(endereco.query)
        corpo = consulta["body"][0]

        self.assertEqual(
            endereco.path,
            "supervisao@exemplo.gov.br",
        )
        self.assertIn(ROTULO_VERSAO_ARBOHUB, corpo)
        self.assertNotIn("Usuário do Windows", corpo)
        self.assertNotIn("Conta do Windows", corpo)

    def test_email_invalido_e_rejeitado(self):
        with self.assertRaises(ValueError):
            SuporteService().montar_link_email(
                destinatario="email-invalido",
            )


if __name__ == "__main__":
    unittest.main()
