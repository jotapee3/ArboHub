from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


class ConfiguracoesService:
    """
    Gerencia preferências locais do ArboHub.

    As configurações são gravadas fora do repositório, na pasta
    local do usuário do Windows. Nenhuma credencial ou dado de
    paciente é armazenado por este serviço.
    """

    PAGINAS_VALIDAS = {
        "inicio",
        "sinan",
        "gal"
    }

    INTERVALOS_DASHBOARD_VALIDOS = {
        30,
        60,
        120,
        300
    }

    ESCALAS_VALIDAS = {
        90,
        100,
        110,
        125
    }

    def __init__(
        self,
        caminho_arquivo: str | Path | None = None
    ):
        if caminho_arquivo is None:
            local_app_data = os.environ.get(
                "LOCALAPPDATA"
            )

            if local_app_data:
                pasta_base = Path(local_app_data)
            else:
                pasta_base = (
                    Path.home()
                    / "AppData"
                    / "Local"
                )

            caminho_arquivo = (
                pasta_base
                / "ArboHub"
                / "configuracoes.json"
            )

        self.caminho_arquivo = Path(
            caminho_arquivo
        ).expanduser().resolve()

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def configuracoes_padrao(self) -> dict[str, Any]:
        """
        Gera os padrões usando o usuário atual do Windows.
        """

        return {
            "versao_configuracao": 1,
            "geral": {
                "pagina_inicial": "inicio",
                "abrir_maximizado": True,
                "dashboard_atualizacao_automatica": True,
                "dashboard_intervalo_segundos": 60,
                "escala_interface": 100
            },
            "rotinas": {
                "modo_teste": True
            },
            "caminhos": {
                "historico_sinan": str(
                    Path.home()
                    / "Documents"
                    / "SINAN"
                    / "Historico"
                ),
                "teste_ab1": (
                    r"F:\Antropozoonoses\Teste AB1"
                ),
                "teste_ab2": (
                    r"F:\Antropozoonoses\Teste AB2"
                ),
                "bancos_atuais": str(
                    Path.home()
                    / "Documents"
                    / "SINAN"
                    / "Bancos_Atuais"
                )
            }
        }

    def obter(self) -> dict[str, Any]:
        """
        Lê as configurações e completa chaves novas com os padrões.
        """

        padrao = self.configuracoes_padrao()

        if not self.caminho_arquivo.exists():
            self.salvar(padrao)
            return copy.deepcopy(padrao)

        try:
            conteudo = json.loads(
                self.caminho_arquivo.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError
        ):
            backup = self.caminho_arquivo.with_suffix(
                ".json.invalido"
            )

            try:
                if backup.exists():
                    backup.unlink()

                self.caminho_arquivo.replace(
                    backup
                )
            except OSError:
                pass

            self.salvar(padrao)
            return copy.deepcopy(padrao)

        mesclado = self._mesclar_com_padrao(
            padrao=padrao,
            recebido=conteudo
        )

        validado = self._validar(
            mesclado
        )

        if validado != conteudo:
            self.salvar(validado)

        return copy.deepcopy(validado)

    def salvar(
        self,
        configuracoes: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Valida e grava de forma atômica.
        """

        padrao = self.configuracoes_padrao()
        mesclado = self._mesclar_com_padrao(
            padrao=padrao,
            recebido=configuracoes
        )
        validado = self._validar(
            mesclado
        )

        temporario = self.caminho_arquivo.with_suffix(
            ".json.tmp"
        )

        temporario.write_text(
            json.dumps(
                validado,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        os.replace(
            temporario,
            self.caminho_arquivo
        )

        return copy.deepcopy(validado)

    def atualizar_secao(
        self,
        secao: str,
        valores: dict[str, Any]
    ) -> dict[str, Any]:
        configuracoes = self.obter()

        if secao not in configuracoes:
            configuracoes[secao] = {}

        configuracoes[secao].update(
            valores
        )

        return self.salvar(
            configuracoes
        )

    def restaurar_padroes(self) -> dict[str, Any]:
        return self.salvar(
            self.configuracoes_padrao()
        )

    def _mesclar_com_padrao(
        self,
        padrao: dict[str, Any],
        recebido: Any
    ) -> dict[str, Any]:
        resultado = copy.deepcopy(
            padrao
        )

        if not isinstance(
            recebido,
            dict
        ):
            return resultado

        for chave, valor in recebido.items():
            if (
                chave in resultado
                and isinstance(
                    resultado[chave],
                    dict
                )
                and isinstance(
                    valor,
                    dict
                )
            ):
                resultado[chave] = (
                    self._mesclar_com_padrao(
                        padrao=resultado[chave],
                        recebido=valor
                    )
                )
            else:
                resultado[chave] = copy.deepcopy(
                    valor
                )

        return resultado

    def _validar(
        self,
        configuracoes: dict[str, Any]
    ) -> dict[str, Any]:
        padrao = self.configuracoes_padrao()

        geral = configuracoes.get(
            "geral",
            {}
        )
        rotinas = configuracoes.get(
            "rotinas",
            {}
        )
        caminhos = configuracoes.get(
            "caminhos",
            {}
        )

        pagina = str(
            geral.get(
                "pagina_inicial",
                "inicio"
            )
        ).strip().casefold()

        if pagina not in self.PAGINAS_VALIDAS:
            pagina = "inicio"

        try:
            intervalo = int(
                geral.get(
                    "dashboard_intervalo_segundos",
                    60
                )
            )
        except (
            TypeError,
            ValueError
        ):
            intervalo = 60

        if (
            intervalo
            not in self.INTERVALOS_DASHBOARD_VALIDOS
        ):
            intervalo = 60

        try:
            escala = int(
                geral.get(
                    "escala_interface",
                    100
                )
            )
        except (
            TypeError,
            ValueError
        ):
            escala = 100

        if escala not in self.ESCALAS_VALIDAS:
            escala = 100

        caminhos_validados = {}

        for chave, valor_padrao in padrao[
            "caminhos"
        ].items():
            valor = str(
                caminhos.get(
                    chave,
                    valor_padrao
                )
            ).strip()

            if not valor:
                valor = valor_padrao

            caminhos_validados[chave] = valor

        return {
            "versao_configuracao": 1,
            "geral": {
                "pagina_inicial": pagina,
                "abrir_maximizado": bool(
                    geral.get(
                        "abrir_maximizado",
                        True
                    )
                ),
                "dashboard_atualizacao_automatica":
                    bool(
                        geral.get(
                            "dashboard_atualizacao_automatica",
                            True
                        )
                    ),
                "dashboard_intervalo_segundos":
                    intervalo,
                "escala_interface": escala
            },
            "rotinas": {
                "modo_teste": bool(
                    rotinas.get(
                        "modo_teste",
                        True
                    )
                )
            },
            "caminhos": caminhos_validados
        }
