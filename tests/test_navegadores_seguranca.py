from __future__ import annotations

import unittest

from app.core.seguranca_urls import (
    url_https_corresponde_dominio,
)


class NavegadoresSegurancaTestCase(unittest.TestCase):
    def test_sinan_aceita_somente_https_e_dominio_oficial(self):
        for url, esperado in (
            (
                "https://sinan.saude.gov.br/sinan/login/login.jsf",
                True,
            ),
            ("http://sinan.saude.gov.br/", False),
            ("https://sinan.saude.gov.br.exemplo.org/", False),
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    url_https_corresponde_dominio(
                        url,
                        "sinan.saude.gov.br",
                    ),
                    esperado,
                )

    def test_gal_aceita_somente_https_e_dominio_oficial(self):
        for url, esperado in (
            (
                "https://gal.riograndedosul.sus.gov.br/login/",
                True,
            ),
            ("http://gal.riograndedosul.sus.gov.br/login/", False),
            (
                "https://gal.riograndedosul.sus.gov.br.exemplo.org/",
                False,
            ),
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    url_https_corresponde_dominio(
                        url,
                        "gal.riograndedosul.sus.gov.br",
                    ),
                    esperado,
                )


if __name__ == "__main__":
    unittest.main()
