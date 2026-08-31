from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from app.automation.sinan.excecoes import SessaoSinanExpirada
from app.automation.sinan.exportacao_bases import ExportacaoBasesDbf
from app.automation.sinan.verificacao_obitos import VerificacaoObitos
from app.services.atualizacao_bases_service import AtualizacaoBasesService
from app.services.rotina_bases_service import RotinaBasesService
from app.services.selecao_destinos_bases import SelecaoDestinosBases


class _LocalizadorVazio:
    def count(self):
        return 0


class _CorpoFalso:
    def __init__(self, texto: str):
        self.texto = texto

    def inner_text(self, timeout=None):
        return self.texto


class _ContextoFalso:
    def __init__(self, texto: str):
        self.texto = texto

    def get_by_text(self, texto, exact=False):
        return _LocalizadorVazio()

    def locator(self, seletor: str):
        if seletor != "body":
            raise AssertionError(f"Seletor inesperado: {seletor}")
        return _CorpoFalso(self.texto)


class _PaginaFalsa:
    def __init__(self, url: str):
        self.url = url

    def is_closed(self):
        return False


class _ConfiguracoesFalsas:
    def carregar(self):
        return {
            "operacional": {
                "exportacao": {
                    "intervalo_consulta_segundos": 15,
                    "tempo_limite_segundos": 1200,
                    "aviso_inicial_segundos": 60,
                    "aviso_lento_segundos": 300,
                    "aviso_reforcado_segundos": 600,
                }
            }
        }


class _CheckpointFalso:
    def __init__(self):
        self.marcacoes = 0

    def marcar_atualizacao_bases(self, data_referencia=None):
        self.marcacoes += 1


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


class _RotinaComExpiracao:
    def __init__(self, expiracoes=1):
        self.expiracoes = expiracoes
        self.execucoes = []

    def avaliar_estado_do_dia(self, selecao_destinos):
        return {"requer_navegador": True}

    def executar_rotina_selecionada(self, **opcoes):
        self.execucoes.append(opcoes)
        if len(self.execucoes) <= self.expiracoes:
            raise SessaoSinanExpirada("A sessão do SINAN expirou.")
        return {
            "concluida": True,
            "agravos": {},
            "selecao_destinos": opcoes[
                "selecao_destinos"
            ].para_dict(),
        }


class _RegistroComSolicitacoesExistentes:
    LOTE = {
        "lote_id": "lote-existente",
        "dengue": {"numero_solicitacao": "2816610"},
        "chikungunya": {"numero_solicitacao": "2816611"},
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
    def test_detecta_aviso_real_com_url_e_tabela_ainda_protegidas(self):
        verificacao = object.__new__(VerificacaoObitos)
        verificacao.pagina = _PaginaFalsa(
            "https://sinan.saude.gov.br/sinan/secured/home.jsf"
        )
        contexto = _ContextoFalso(
            "CONSULTAR EXPORTAÇÃO DBF\n"
            "Processamento Agendado\n"
            "Sessão Expirada!"
        )
        verificacao._obter_contextos = lambda: [contexto]

        with self.assertRaises(SessaoSinanExpirada):
            verificacao._garantir_pagina_aberta()

    def test_aviso_ausente_mantem_sessao_protegida(self):
        verificacao = object.__new__(VerificacaoObitos)
        verificacao.pagina = _PaginaFalsa(
            "https://sinan.saude.gov.br/sinan/secured/home.jsf"
        )
        verificacao._obter_contextos = lambda: [
            _ContextoFalso(
                "Sua Sessão Expira Em: 9min 31s\n"
                "Processamento Agendado"
            )
        ]

        verificacao._garantir_pagina_aberta()

    def test_atualizacao_para_antes_de_clicar_quando_sessao_expira(self):
        exportacao = object.__new__(ExportacaoBasesDbf)
        exportacao._garantir_pagina_aberta = Mock(
            side_effect=SessaoSinanExpirada("Sessão expirada")
        )
        exportacao._tela_consulta_exportacoes_esta_aberta = Mock(
            return_value=True
        )
        exportacao._localizar_botao_atualizar_exportacoes = Mock()

        with self.assertRaises(SessaoSinanExpirada):
            exportacao.atualizar_consulta_exportacoes_dbf()

        exportacao._localizar_botao_atualizar_exportacoes.assert_not_called()

    def test_recupera_sessao_e_reutiliza_a_mesma_execucao(self):
        checkpoint = _CheckpointFalso()
        rotina = _RotinaComExpiracao(expiracoes=2)
        service = AtualizacaoBasesService(
            checkpoint_service=checkpoint,
            rotina_service=rotina,
            configuracoes_service=_ConfiguracoesFalsas(),
        )
        selecao = SelecaoDestinosBases.completa()
        _NavegadorFalso.instancias = []

        with patch(
            "app.services.atualizacao_bases_service.NavegadorSinan",
            _NavegadorFalso,
        ), patch(
            "app.services.atualizacao_bases_service.ExportacaoBasesDbf",
            _ExportacaoFalsa,
        ):
            service._executar(
                solicitacoes_autorizadas=False,
                selecao_destinos=selecao,
            )

        eventos = service.obter_eventos()
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
        self.assertTrue(all(
            execucao["selecao_destinos"] is selecao
            and not execucao["solicitacoes_autorizadas"]
            for execucao in rotina.execucoes
        ))
        self.assertEqual(conclusao["recuperacoes_sessao"], 2)
        self.assertEqual(checkpoint.marcacoes, 1)

    def test_retomada_reutiliza_numeros_sem_nova_solicitacao(self):
        registro = _RegistroComSolicitacoesExistentes()
        rotina = RotinaBasesService(
            registro_service=registro,
            arquivos_service=_ArquivosSemFonteHistorica(),
        )

        resultado = rotina.garantir_solicitacoes_selecionadas(
            exportacao=_ExportacaoQueNaoPodeSolicitar(),
            selecao_destinos=SelecaoDestinosBases.completa(),
            data_referencia=date(2026, 8, 31),
            solicitacoes_autorizadas=True,
        )

        self.assertIs(resultado["lote"], registro.LOTE)
        self.assertTrue(resultado["reutilizado"])
        self.assertEqual(resultado["novas_solicitacoes"], [])


if __name__ == "__main__":
    unittest.main()
