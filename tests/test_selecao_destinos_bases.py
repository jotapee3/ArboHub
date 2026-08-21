import unittest

from app.services.selecao_destinos_bases import (
    SelecaoDestinosBases
)


class SelecaoDestinosBasesTestCase(unittest.TestCase):
    def test_selecao_completa_exige_os_dois_agravos(self):
        selecao = SelecaoDestinosBases.completa()

        self.assertTrue(selecao.esta_completa)
        self.assertEqual(
            selecao.agravos_necessarios,
            SelecaoDestinosBases.AGRAVOS_VALIDOS
        )

    def test_somente_dengue_dbf_nao_exige_chikungunya(self):
        selecao = SelecaoDestinosBases(
            atualizar_historico=False,
            agravos_bases_dbf=frozenset({"dengue"}),
            atualizar_bancos_atuais=False
        )

        self.assertEqual(
            selecao.agravos_necessarios,
            frozenset({"dengue"})
        )
        self.assertEqual(selecao.resumo(), "Dengue DBF")

    def test_historico_exige_a_dupla_sem_ativar_bases_dbf(self):
        selecao = SelecaoDestinosBases(
            atualizar_historico=True,
            agravos_bases_dbf=frozenset(),
            atualizar_bancos_atuais=False
        )

        self.assertEqual(
            selecao.agravos_necessarios,
            SelecaoDestinosBases.AGRAVOS_VALIDOS
        )
        self.assertEqual(selecao.resumo(), "Histórico")

    def test_rejeita_execucao_sem_destino(self):
        with self.assertRaisesRegex(
            ValueError,
            "Selecione pelo menos um destino"
        ):
            SelecaoDestinosBases(
                atualizar_historico=False,
                agravos_bases_dbf=frozenset(),
                atualizar_bancos_atuais=False
            )

    def test_rejeita_agravo_desconhecido(self):
        with self.assertRaisesRegex(ValueError, "Agravo inválido"):
            SelecaoDestinosBases(
                agravos_bases_dbf=frozenset({"zika"})
            )


if __name__ == "__main__":
    unittest.main()
