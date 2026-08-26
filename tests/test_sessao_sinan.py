from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from app.automation.sinan.excecoes import (
    SessaoSinanExpirada
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
)
from app.services.atualizacao_bases_service import (
    AtualizacaoBasesService
)
from app.services.rotina_bases_service import (
    RotinaBasesService
)
from app.services.selecao_destinos_bases import (
    SelecaoDestinosBases
)


class _PaginaFalsa:
    def __init__(self, url: str):
        self.url = url

    def is_closed(self):
        return False


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


class _NavegadorFalso:
    instancias = []

    def __init__(self, **opcoes):
        self.opcoes = opcoes
        self.pagina = object()
        self.login_automatico_concluido = True
        self.fechado = False
        self.__class__.instancias.append(self)

    def abrir(self):
        return self.pagina

    def fechar(self):
        self.fechado = True


class _ExportacaoFalsa:
    def __init__(self, pagina):
        self.pagina = pagina


class _RotinaComExpiracoes:
    def __init__(self, expiracoes: int):
        self.expiracoes = expiracoes
        self.execucoes = []

    def avaliar_estado_do_dia(self, selecao_destinos):
        return {"requer_navegador": True}

    def executar_rotina_selecionada(self, **opcoes):
        self.execucoes.append(opcoes)

        if len(self.execucoes) <= self.expiracoes:
            raise SessaoSinanExpirada(
                "A sessão do SINAN expirou."
            )

        return {
            "concluida": True,
            "agravos": {},
            "selecao_destinos": (
                opcoes["selecao_destinos"].para_dict()
            )
        }


class _RotinaQueCancelaAoExpirar(_RotinaComExpiracoes):
    def __init__(self):
        super().__init__(expiracoes=1)
        self.cancelar = None

    def executar_rotina_selecionada(self, **opcoes):
        self.execucoes.append(opcoes)
        self.cancelar()
        raise SessaoSinanExpirada(
            "A sessão do SINAN expirou."
        )


class _RegistroComSolicitacoesExistentes:
    LOTE = {
        "lote_id": "lote-existente",
        "dengue": {
            "numero_solicitacao": "2816610"
        },
        "chikungunya": {
            "numero_solicitacao": "2816611"
        }
    }

    def obter_lote_completo_do_dia(self, data_referencia):
        return self.LOTE

    def obter_lote_parcial_do_dia(self, data_referencia):
        return None


class _ArquivosSemFonteHistorica:
    def validar_destinos_operacionais(self, **opcoes):
        return opcoes

    def caminho_historico(self, agravo, data_referencia):
        return Path(f"arquivo-ainda-ausente-{agravo}.zip")

    def zip_contem_dbf_do_agravo(self, caminho_zip, agravo):
        return False


class _ExportacaoQueNaoPodeSolicitar:
    def __getattr__(self, nome):
        raise AssertionError(
            f"Não deveria criar uma solicitação por {nome}."
        )


class SessaoSinanTestCase(unittest.TestCase):
    def test_detecta_aviso_visivel_mesmo_em_url_protegida(self):
        verificacao = object.__new__(VerificacaoObitos)
        verificacao.pagina = _PaginaFalsa(
            "https://sinan.saude.gov.br/sinan/secured/home.jsf"
        )
        verificacao._sessao_expirada_esta_visivel = Mock(
            return_value=True
        )

        with self.assertRaises(SessaoSinanExpirada):
            verificacao._garantir_pagina_aberta()

    def test_url_de_login_tambem_indica_sessao_expirada(self):
        verificacao = object.__new__(VerificacaoObitos)
        verificacao.pagina = _PaginaFalsa(
            "https://sinan.saude.gov.br/sinan/login/login.jsf"
        )
        verificacao._sessao_expirada_esta_visivel = Mock(
            return_value=False
        )

        with self.assertRaises(SessaoSinanExpirada):
            verificacao._garantir_pagina_aberta()

    def test_aviso_ausente_mantem_sessao_protegida(self):
        verificacao = object.__new__(VerificacaoObitos)
        verificacao.pagina = _PaginaFalsa(
            "https://sinan.saude.gov.br/sinan/secured/home.jsf"
        )
        verificacao._sessao_expirada_esta_visivel = Mock(
            return_value=False
        )

        verificacao._garantir_pagina_aberta()

    def test_recupera_expiracoes_repetidas_e_reutiliza_execucao(self):
        checkpoint = _CheckpointFalso()
        rotina = _RotinaComExpiracoes(expiracoes=2)
        service = AtualizacaoBasesService(
            checkpoint_service=checkpoint,
            rotina_service=rotina,
            configuracoes_service=_ConfiguracoesFalsas()
        )
        selecao = SelecaoDestinosBases.completa()
        _NavegadorFalso.instancias = []

        with patch(
            "app.services.atualizacao_bases_service.NavegadorSinan",
            _NavegadorFalso
        ), patch(
            "app.services.atualizacao_bases_service.ExportacaoBasesDbf",
            _ExportacaoFalsa
        ):
            service._executar(
                solicitacoes_autorizadas=False,
                selecao_destinos=selecao
            )

        eventos = service.obter_eventos()
        recuperando = [
            evento
            for evento in eventos
            if evento["tipo"] == service.EVENTO_STATUS
            and evento.get("estado") == "recuperando"
        ]
        recuperadas = [
            evento
            for evento in eventos
            if evento["tipo"] == service.EVENTO_STATUS
            and evento.get("estado") == "recuperada"
        ]
        conclusao = next(
            evento
            for evento in eventos
            if evento["tipo"] == service.EVENTO_CONCLUIDO
        )

        self.assertEqual(len(rotina.execucoes), 3)
        self.assertEqual(len(_NavegadorFalso.instancias), 3)
        self.assertTrue(all(
            navegador.fechado
            for navegador in _NavegadorFalso.instancias
        ))
        self.assertEqual(len(recuperando), 2)
        self.assertEqual(len(recuperadas), 2)
        self.assertEqual(conclusao["recuperacoes_sessao"], 2)
        self.assertIn(
            "recuperada automaticamente 2 vezes",
            conclusao["mensagem"]
        )
        self.assertEqual(checkpoint.marcacoes, 1)
        self.assertTrue(all(
            execucao["selecao_destinos"] is selecao
            and not execucao["solicitacoes_autorizadas"]
            for execucao in rotina.execucoes
        ))

    def test_retomada_reutiliza_numeros_sem_nova_solicitacao(self):
        registro = _RegistroComSolicitacoesExistentes()
        rotina = RotinaBasesService(
            registro_service=registro,
            arquivos_service=_ArquivosSemFonteHistorica()
        )

        resultado = rotina.garantir_solicitacoes_selecionadas(
            exportacao=_ExportacaoQueNaoPodeSolicitar(),
            selecao_destinos=SelecaoDestinosBases.completa(),
            data_referencia=date(2026, 8, 26),
            solicitacoes_autorizadas=True
        )

        self.assertIs(resultado["lote"], registro.LOTE)
        self.assertTrue(resultado["reutilizado"])
        self.assertEqual(resultado["novas_solicitacoes"], [])

    def test_cancelamento_impede_nova_autenticacao(self):
        rotina = _RotinaQueCancelaAoExpirar()
        service = AtualizacaoBasesService(
            checkpoint_service=_CheckpointFalso(),
            rotina_service=rotina,
            configuracoes_service=_ConfiguracoesFalsas()
        )
        rotina.cancelar = service.cancelar
        _NavegadorFalso.instancias = []

        with patch(
            "app.services.atualizacao_bases_service.NavegadorSinan",
            _NavegadorFalso
        ), patch(
            "app.services.atualizacao_bases_service.ExportacaoBasesDbf",
            _ExportacaoFalsa
        ):
            service._executar(
                solicitacoes_autorizadas=False,
                selecao_destinos=SelecaoDestinosBases.completa()
            )

        eventos = service.obter_eventos()

        self.assertEqual(len(_NavegadorFalso.instancias), 1)
        self.assertTrue(_NavegadorFalso.instancias[0].fechado)
        self.assertTrue(any(
            evento["tipo"] == service.EVENTO_CANCELADO
            for evento in eventos
        ))
        self.assertFalse(any(
            evento.get("estado") == "recuperada"
            for evento in eventos
        ))


if __name__ == "__main__":
    unittest.main()
