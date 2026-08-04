from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


class ConfiguracoesService:
    """
    Gerencia preferências locais e não sensíveis do ArboHub.

    O arquivo fica fora do repositório, em LOCALAPPDATA, para que
    cada conta do Windows tenha suas próprias preferências.
    """

    PAGINAS_VALIDAS = {
        "inicio",
        "sinan",
        "gal"
    }

    INTERVALOS_VALIDOS = {
        30,
        60,
        120,
        300
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
        ).expanduser()

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def obter_padroes(self) -> dict[str, Any]:
        return {
            "versao": 1,
            "geral": {
                "pagina_inicial": "inicio",
                "abrir_maximizado": False
            },
            "dashboard": {
                "atualizacao_automatica": True,
                "intervalo_segundos": 60
            }
        }

    def carregar(self) -> dict[str, Any]:
        padroes = self.obter_padroes()

        if not self.caminho_arquivo.exists():
            return self.salvar(padroes)

        try:
            recebido = json.loads(
                self.caminho_arquivo.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError
        ):
            self._preservar_arquivo_invalido()
            return self.salvar(padroes)

        mesclado = self._mesclar(
            padroes,
            recebido
        )
        validado = self._validar(
            mesclado
        )

        if validado != recebido:
            self.salvar(validado)

        return copy.deepcopy(validado)

    def salvar(
        self,
        configuracoes: dict[str, Any]
    ) -> dict[str, Any]:
        validado = self._validar(
            self._mesclar(
                self.obter_padroes(),
                configuracoes
            )
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

    def restaurar_padroes(self) -> dict[str, Any]:
        return self.salvar(
            self.obter_padroes()
        )

    def _mesclar(
        self,
        padroes: dict[str, Any],
        recebido: Any
    ) -> dict[str, Any]:
        resultado = copy.deepcopy(
            padroes
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
                resultado[chave] = self._mesclar(
                    resultado[chave],
                    valor
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
        geral = configuracoes.get(
            "geral",
            {}
        )
        dashboard = configuracoes.get(
            "dashboard",
            {}
        )

        pagina_inicial = str(
            geral.get(
                "pagina_inicial",
                "inicio"
            )
        ).strip().casefold()

        if pagina_inicial not in self.PAGINAS_VALIDAS:
            pagina_inicial = "inicio"

        try:
            intervalo = int(
                dashboard.get(
                    "intervalo_segundos",
                    60
                )
            )
        except (
            TypeError,
            ValueError
        ):
            intervalo = 60

        if intervalo not in self.INTERVALOS_VALIDOS:
            intervalo = 60

        return {
            "versao": 1,
            "geral": {
                "pagina_inicial": pagina_inicial,
                "abrir_maximizado": bool(
                    geral.get(
                        "abrir_maximizado",
                        False
                    )
                )
            },
            "dashboard": {
                "atualizacao_automatica": bool(
                    dashboard.get(
                        "atualizacao_automatica",
                        True
                    )
                ),
                "intervalo_segundos": intervalo
            }
        }

    def _preservar_arquivo_invalido(self):
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
