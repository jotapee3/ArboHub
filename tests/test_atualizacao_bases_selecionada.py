from __future__ import annotations

import unittest

from app.services.atualizacao_bases_service import AtualizacaoBasesService
from app.services.selecao_destinos_bases import SelecaoDestinosBases


class _CheckpointFalso:
    def __init__(self):
        self.marcacoes = 0

    def marcar_atualizacao_bases(self, data_referencia=None):
        self.marcacoes += 1


class _ConfiguracoesFalsas:
    def carregar(self):
        return {
            "operacional": {
                "exportacao": {
                    "intervalo_consulta_segundos": 15,
                    "tempo_limite_segundos": 1200,
                    "aviso_inicial_segundos": 60,
                    "aviso_lento_segundos": 300,
                    "aviso_reforcado_segundos": 600
                }
            }
        }


class _RotinaFalsa:
    def avaliar_estado_do_dia(self, selecao_destinos):
        return {"requer_navegador": False}

    def executar_rotina_selecionada(self, **opcoes):
        return {
            "concluida": True,
            "agravos": {},
            "selecao_destinos": (
                opcoes["selecao_destinos"].para_dict()
            )
        }


class AtualizacaoBasesSelecionadaTestCase(unittest.TestCase):
    def test_execucao_parcial_nao_fecha_checkpoint_diario(self):
        checkpoint = _CheckpointFalso()
        service = AtualizacaoBasesService(
            checkpoint_service=checkpoint,
            rotina_service=_RotinaFalsa(),
            configuracoes_service=_ConfiguracoesFalsas()
        )
        selecao = SelecaoDestinosBases(
            atualizar_historico=False,
            agravos_bases_dbf=frozenset({"dengue"}),
            atualizar_bancos_atuais=False
        )

        service._executar(
            solicitacoes_autorizadas=False,
            selecao_destinos=selecao
        )

        eventos = service.obter_eventos()
        conclusao = next(
            evento
            for evento in eventos
            if evento["tipo"] == service.EVENTO_CONCLUIDO
        )
        self.assertEqual(checkpoint.marcacoes, 0)
        self.assertFalse(conclusao["checkpoint_completo"])

    def test_execucao_completa_fecha_checkpoint_diario(self):
        checkpoint = _CheckpointFalso()
        service = AtualizacaoBasesService(
            checkpoint_service=checkpoint,
            rotina_service=_RotinaFalsa(),
            configuracoes_service=_ConfiguracoesFalsas()
        )

        service._executar(
            solicitacoes_autorizadas=False,
            selecao_destinos=SelecaoDestinosBases.completa()
        )

        eventos = service.obter_eventos()
        conclusao = next(
            evento
            for evento in eventos
            if evento["tipo"] == service.EVENTO_CONCLUIDO
        )
        self.assertEqual(checkpoint.marcacoes, 1)
        self.assertTrue(conclusao["checkpoint_completo"])


if __name__ == "__main__":
    unittest.main()
