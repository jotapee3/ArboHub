from __future__ import annotations

import copy
import json
import os
from datetime import date
from pathlib import Path
from time import time_ns
from typing import Any


class ConfiguracoesService:
    """
    Gerencia preferências locais e não sensíveis do ArboHub.

    O arquivo fica fora do repositório, em LOCALAPPDATA, para que
    cada conta do Windows tenha suas próprias preferências.
    """

    VERSAO_CONFIGURACOES = 8

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

    ESCALAS_INTERFACE_VALIDAS = {
        90,
        100,
        110,
        125
    }

    TEMAS_INTERFACE_VALIDOS = {
        "escuro",
        "claro",
        "sistema"
    }

    INTERVALOS_EXPORTACAO_VALIDOS = {
        10,
        15,
        30,
        60
    }

    AVISOS_INICIAIS_VALIDOS = {
        60,
        120,
        180
    }

    AVISOS_LENTOS_VALIDOS = {
        300,
        420,
        600
    }

    AVISOS_REFORCADOS_VALIDOS = {
        600,
        720,
        900
    }

    LIMITES_EXPORTACAO_VALIDOS = {
        900,
        1200,
        1800,
        2700
    }

    CHAVES_CAMINHOS = (
        "historico_sinan",
        "teste_ab1",
        "teste_ab2",
        "bancos_atuais"
    )

    ROTULOS_CAMINHOS = {
        "historico_sinan": "Histórico do SINAN",
        "teste_ab1": "Dengue (AB1)",
        "teste_ab2": "Chikungunya (AB2)",
        "bancos_atuais": "Bancos_Atuais"
    }

    CHAVES_NOMES_ARQUIVOS_TESTE = (
        "dengue",
        "chikungunya"
    )

    ROTULOS_NOMES_ARQUIVOS_TESTE = {
        "dengue": "arquivo de Dengue (AB1)",
        "chikungunya": "arquivo de Chikungunya (AB2)"
    }

    CARACTERES_INVALIDOS_NOME_ARQUIVO = set(
        '<>:"/\\|?*'
    )

    NOMES_RESERVADOS_WINDOWS = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{numero}" for numero in range(1, 10)),
        *(f"LPT{numero}" for numero in range(1, 10))
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
            "versao": self.VERSAO_CONFIGURACOES,
            "geral": {
                "pagina_inicial": "inicio",
                "abrir_maximizado": False
            },
            "aparencia": {
                "tema": "escuro",
                "escala_percentual": 100
            },
            "dashboard": {
                "atualizacao_automatica": True,
                "intervalo_segundos": 60
            },
            "sinan": {
                "login_automatico": False
            },
            "notificacoes": {
                "som_conclusao": True,
                "som_atencao": True,
                "som_exportacao_disponivel": False,
                "supervisao": {
                    "nome": "",
                    "telefone": "",
                    "email": ""
                }
            },
            "operacional": {
                "caminhos": self.obter_caminhos_padroes(),
                "nomes_arquivos_teste": (
                    self.obter_nomes_arquivos_teste_padroes()
                ),
                "exportacao": {
                    "intervalo_consulta_segundos": 15,
                    "aviso_inicial_segundos": 60,
                    "aviso_lento_segundos": 300,
                    "aviso_reforcado_segundos": 600,
                    "tempo_limite_segundos": 1200,
                    "processar_disponivel_imediatamente": True,
                    "continuar_acompanhando_pendente": True,
                    "permitir_correcao_manual": True
                }
            }
        }

    def obter_caminhos_padroes(self) -> dict[str, str]:
        return {
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

    def obter_nomes_arquivos_teste_padroes(
        self
    ) -> dict[str, str]:
        return {
            "dengue": "Teste{ano}_AB1.dbf",
            "chikungunya": "Teste{ano}_AB2.dbf"
        }

    def validar_nome_arquivo_teste(
        self,
        chave: str,
        modelo: str
    ) -> str:
        """
        Valida um modelo de nome final sem aceitar caminhos.

        ``{ano}`` é o único marcador permitido. A extensão ``.dbf``
        é acrescentada quando o usuário informa somente o nome-base.
        """

        if chave not in self.CHAVES_NOMES_ARQUIVOS_TESTE:
            raise ValueError(
                "Tipo de arquivo de teste desconhecido."
            )

        nome = str(
            modelo
        ).strip()
        rotulo = self.ROTULOS_NOMES_ARQUIVOS_TESTE[
            chave
        ]

        if not nome:
            raise ValueError(
                f"O nome do {rotulo} não pode ficar vazio."
            )

        if len(nome) > 120:
            raise ValueError(
                f"O nome do {rotulo} deve ter no máximo "
                "120 caracteres."
            )

        resolvido = nome.replace(
            "{ano}",
            str(date.today().year)
        )

        if "{" in resolvido or "}" in resolvido:
            raise ValueError(
                f"O nome do {rotulo} possui um marcador inválido. "
                "Use somente {ano}."
            )

        if any(
            caractere in self.CARACTERES_INVALIDOS_NOME_ARQUIVO
            or ord(caractere) < 32
            for caractere in resolvido
        ):
            raise ValueError(
                f"O nome do {rotulo} contém caracteres não "
                "permitidos pelo Windows."
            )

        if resolvido.endswith((" ", ".")):
            raise ValueError(
                f"O nome do {rotulo} não pode terminar com espaço "
                "ou ponto."
            )

        if not nome.casefold().endswith(".dbf"):
            nome += ".dbf"
            resolvido += ".dbf"

        if len(nome) > 120:
            raise ValueError(
                f"O nome do {rotulo} deve ter no máximo "
                "120 caracteres, incluindo .dbf."
            )

        if (
            resolvido.startswith(".")
            or not Path(resolvido).stem.strip(". ")
        ):
            raise ValueError(
                f"O nome do {rotulo} precisa ter um nome-base "
                "antes de .dbf."
            )

        base_resolvida = Path(
            resolvido
        ).stem.upper()

        if base_resolvida in self.NOMES_RESERVADOS_WINDOWS:
            raise ValueError(
                f"O nome do {rotulo} é reservado pelo Windows."
            )

        return nome[:-4] + ".dbf"

    def validar_nomes_arquivos_teste(
        self,
        nomes: dict[str, str]
    ) -> dict[str, str]:
        return {
            chave: self.validar_nome_arquivo_teste(
                chave=chave,
                modelo=nomes.get(
                    chave,
                    ""
                )
            )
            for chave in self.CHAVES_NOMES_ARQUIVOS_TESTE
        }

    def resolver_nome_arquivo_teste(
        self,
        chave: str,
        ano: int,
        nomes: dict[str, str] | None = None
    ) -> str:
        if nomes is None:
            nomes = (
                self.carregar()
                ["operacional"]
                ["nomes_arquivos_teste"]
            )

        modelo = self.validar_nome_arquivo_teste(
            chave=chave,
            modelo=nomes.get(
                chave,
                ""
            )
        )

        return modelo.replace(
            "{ano}",
            str(int(ano))
        )

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

    def testar_pasta_operacional(
        self,
        chave: str,
        caminho: str | Path,
        testar_escrita: bool = True
    ) -> dict[str, object]:
        """
        Testa uma pasta sem manter qualquer arquivo nela.

        Retorna apenas metadados operacionais. Nenhum DBF é aberto.
        """

        try:
            caminho_validado = (
                self.validar_pasta_operacional(
                    chave=chave,
                    caminho=caminho,
                    testar_escrita=testar_escrita
                )
            )
        except Exception as erro:
            return {
                "valido": False,
                "chave": chave,
                "caminho": str(caminho),
                "mensagem": str(erro)
            }

        return {
            "valido": True,
            "chave": chave,
            "caminho": str(caminho_validado),
            "mensagem": (
                "Leitura e gravação confirmadas."
                if testar_escrita
                else "Pasta acessível para leitura."
            )
        }

    def validar_pasta_operacional(
        self,
        chave: str,
        caminho: str | Path,
        testar_escrita: bool = True
    ) -> Path:
        if chave not in self.CHAVES_CAMINHOS:
            raise ValueError(
                "Tipo de pasta operacional desconhecido."
            )

        texto = self._normalizar_caminho(
            caminho
        )

        if not texto:
            raise ValueError(
                f"{self.ROTULOS_CAMINHOS[chave]} não pode "
                "ficar sem caminho."
            )

        pasta = Path(texto).expanduser()

        if not pasta.exists():
            raise FileNotFoundError(
                f"{self.ROTULOS_CAMINHOS[chave]} não foi "
                f"encontrada: {pasta}"
            )

        if not pasta.is_dir():
            raise NotADirectoryError(
                f"{self.ROTULOS_CAMINHOS[chave]} não aponta "
                f"para uma pasta: {pasta}"
            )

        if not os.access(
            pasta,
            os.R_OK
        ):
            raise PermissionError(
                f"Sem permissão de leitura em "
                f"{self.ROTULOS_CAMINHOS[chave]}: {pasta}"
            )

        if testar_escrita:
            if not os.access(
                pasta,
                os.W_OK
            ):
                raise PermissionError(
                    f"Sem permissão de gravação em "
                    f"{self.ROTULOS_CAMINHOS[chave]}: {pasta}"
                )

            arquivo_teste = (
                pasta
                / (
                    f".arbohub_teste_escrita_"
                    f"{os.getpid()}_{time_ns()}.tmp"
                )
            )

            try:
                with arquivo_teste.open(
                    mode="x",
                    encoding="utf-8"
                ) as arquivo:
                    arquivo.write(
                        "Teste temporário de permissão do ArboHub."
                    )

                conteudo = arquivo_teste.read_text(
                    encoding="utf-8"
                )

                if not conteudo:
                    raise OSError(
                        "O arquivo de teste não pôde ser lido."
                    )

            except Exception as erro:
                raise PermissionError(
                    f"Não foi possível confirmar gravação em "
                    f"{self.ROTULOS_CAMINHOS[chave]}: {pasta}. "
                    f"Detalhe: {erro}"
                ) from erro

            finally:
                try:
                    if arquivo_teste.exists():
                        arquivo_teste.unlink()
                except OSError:
                    pass

        return pasta

    def validar_caminhos_operacionais(
        self,
        caminhos: dict[str, str | Path],
        testar_escrita: bool = True
    ) -> dict[str, str]:
        """
        Valida os quatro destinos e impede sobreposição acidental.
        """

        validados: dict[str, Path] = {}

        for chave in self.CHAVES_CAMINHOS:
            validados[chave] = (
                self.validar_pasta_operacional(
                    chave=chave,
                    caminho=caminhos.get(
                        chave,
                        ""
                    ),
                    testar_escrita=testar_escrita
                )
            )

        normalizados: dict[str, str] = {}

        for chave, caminho in validados.items():
            try:
                absoluto = caminho.resolve(
                    strict=False
                )
            except OSError:
                absoluto = caminho.absolute()

            normalizados[chave] = os.path.normcase(
                os.path.normpath(
                    str(absoluto)
                )
            )

        agrupados: dict[str, list[str]] = {}

        for chave, caminho in normalizados.items():
            agrupados.setdefault(
                caminho,
                []
            ).append(chave)

        repetidos = [
            chaves
            for chaves in agrupados.values()
            if len(chaves) > 1
        ]

        if repetidos:
            nomes = []

            for grupo in repetidos:
                nomes.append(
                    " e ".join(
                        self.ROTULOS_CAMINHOS[chave]
                        for chave in grupo
                    )
                )

            raise ValueError(
                "Destinos operacionais não podem usar a mesma "
                "pasta. Revise: "
                + "; ".join(nomes)
                + "."
            )

        return {
            chave: str(caminho)
            for chave, caminho in validados.items()
        }

    def validar_tempos_exportacao(
        self,
        exportacao: dict[str, Any]
    ) -> dict[str, object]:
        """
        Valida os tempos configuráveis e mantém as proteções ativas.
        """

        padrao = self.obter_padroes()[
            "operacional"
        ]["exportacao"]

        intervalo = self._inteiro_valido(
            exportacao.get(
                "intervalo_consulta_segundos"
            ),
            self.INTERVALOS_EXPORTACAO_VALIDOS,
            padrao["intervalo_consulta_segundos"]
        )
        aviso_inicial = self._inteiro_valido(
            exportacao.get(
                "aviso_inicial_segundos"
            ),
            self.AVISOS_INICIAIS_VALIDOS,
            padrao["aviso_inicial_segundos"]
        )
        aviso_lento = self._inteiro_valido(
            exportacao.get(
                "aviso_lento_segundos"
            ),
            self.AVISOS_LENTOS_VALIDOS,
            padrao["aviso_lento_segundos"]
        )
        aviso_reforcado = self._inteiro_valido(
            exportacao.get(
                "aviso_reforcado_segundos"
            ),
            self.AVISOS_REFORCADOS_VALIDOS,
            padrao["aviso_reforcado_segundos"]
        )
        tempo_limite = self._inteiro_valido(
            exportacao.get(
                "tempo_limite_segundos"
            ),
            self.LIMITES_EXPORTACAO_VALIDOS,
            padrao["tempo_limite_segundos"]
        )

        if not (
            0
            < aviso_inicial
            < aviso_lento
            < aviso_reforcado
            < tempo_limite
        ):
            aviso_inicial = padrao[
                "aviso_inicial_segundos"
            ]
            aviso_lento = padrao[
                "aviso_lento_segundos"
            ]
            aviso_reforcado = padrao[
                "aviso_reforcado_segundos"
            ]
            tempo_limite = padrao[
                "tempo_limite_segundos"
            ]

        return {
            "intervalo_consulta_segundos": intervalo,
            "aviso_inicial_segundos": aviso_inicial,
            "aviso_lento_segundos": aviso_lento,
            "aviso_reforcado_segundos": aviso_reforcado,
            "tempo_limite_segundos": tempo_limite,
            # Estas proteções permanecem obrigatórias nesta versão.
            "processar_disponivel_imediatamente": True,
            "continuar_acompanhando_pendente": True,
            "permitir_correcao_manual": True
        }

    def validar_supervisao(
        self,
        supervisao: dict[str, Any]
    ) -> dict[str, str]:
        """
        Valida dados institucionais opcionais da supervisão.

        Esses dados permanecem somente no arquivo local de
        configurações. Nenhum envio automático é realizado.
        """

        normalizado = self._normalizar_supervisao(
            supervisao
        )

        email = normalizado["email"]

        if email and not self._email_valido(
            email
        ):
            raise ValueError(
                "O e-mail institucional da supervisão não é válido."
            )

        telefone = normalizado[
            "telefone"
        ]

        if telefone:
            digitos = "".join(
                caractere
                for caractere in telefone
                if caractere.isdigit()
            )

            if len(digitos) < 6:
                raise ValueError(
                    "O telefone institucional precisa ter pelo "
                    "menos 6 dígitos."
                )

        return normalizado

    def _normalizar_supervisao(
        self,
        supervisao: Any
    ) -> dict[str, str]:
        if not isinstance(
            supervisao,
            dict
        ):
            supervisao = {}

        limites = {
            "nome": 120,
            "telefone": 40,
            "email": 160
        }

        resultado: dict[str, str] = {}

        for chave, limite in limites.items():
            valor = str(
                supervisao.get(
                    chave,
                    ""
                )
            ).strip()

            if chave in {
                "nome",
                "email"
            }:
                valor = " ".join(
                    valor.split()
                )

            if chave == "email":
                valor = valor.casefold()

            resultado[chave] = valor[
                :limite
            ]

        return resultado

    def _email_valido(
        self,
        email: str
    ) -> bool:
        if (
            " " in email
            or email.count("@") != 1
        ):
            return False

        usuario, dominio = email.rsplit(
            "@",
            1
        )

        return bool(
            usuario
            and dominio
            and "." in dominio
            and not dominio.startswith(".")
            and not dominio.endswith(".")
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
        aparencia = configuracoes.get(
            "aparencia",
            {}
        )
        dashboard = configuracoes.get(
            "dashboard",
            {}
        )
        sinan = configuracoes.get(
            "sinan",
            {}
        )
        notificacoes = configuracoes.get(
            "notificacoes",
            {}
        )
        supervisao = self._normalizar_supervisao(
            notificacoes.get(
                "supervisao",
                {}
            )
        )
        operacional = configuracoes.get(
            "operacional",
            {}
        )
        caminhos_recebidos = operacional.get(
            "caminhos",
            {}
        )
        nomes_arquivos_teste_recebidos = operacional.get(
            "nomes_arquivos_teste",
            {}
        )
        exportacao_recebida = operacional.get(
            "exportacao",
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

        intervalo = self._inteiro_valido(
            dashboard.get(
                "intervalo_segundos"
            ),
            self.INTERVALOS_VALIDOS,
            60
        )

        tema_interface = str(
            aparencia.get(
                "tema",
                "escuro"
            )
        ).strip().casefold()

        if tema_interface not in self.TEMAS_INTERFACE_VALIDOS:
            tema_interface = "escuro"

        escala_percentual = self._inteiro_valido(
            aparencia.get(
                "escala_percentual"
            ),
            self.ESCALAS_INTERFACE_VALIDAS,
            100
        )

        caminhos_padrao = self.obter_caminhos_padroes()
        caminhos = {
            chave: (
                self._normalizar_caminho(
                    caminhos_recebidos.get(
                        chave,
                        caminhos_padrao[chave]
                    )
                )
                or caminhos_padrao[chave]
            )
            for chave in self.CHAVES_CAMINHOS
        }

        nomes_arquivos_teste_padroes = (
            self.obter_nomes_arquivos_teste_padroes()
        )
        nomes_arquivos_teste = {}

        for chave in self.CHAVES_NOMES_ARQUIVOS_TESTE:
            try:
                nomes_arquivos_teste[chave] = (
                    self.validar_nome_arquivo_teste(
                        chave=chave,
                        modelo=nomes_arquivos_teste_recebidos.get(
                            chave,
                            nomes_arquivos_teste_padroes[chave]
                        )
                    )
                )
            except ValueError:
                nomes_arquivos_teste[chave] = (
                    nomes_arquivos_teste_padroes[chave]
                )

        exportacao = self.validar_tempos_exportacao(
            exportacao_recebida
        )

        return {
            "versao": self.VERSAO_CONFIGURACOES,
            "geral": {
                "pagina_inicial": pagina_inicial,
                "abrir_maximizado": bool(
                    geral.get(
                        "abrir_maximizado",
                        False
                    )
                )
            },
            "aparencia": {
                "tema": tema_interface,
                "escala_percentual": escala_percentual
            },
            "dashboard": {
                "atualizacao_automatica": bool(
                    dashboard.get(
                        "atualizacao_automatica",
                        True
                    )
                ),
                "intervalo_segundos": intervalo
            },
            "sinan": {
                "login_automatico": bool(
                    sinan.get(
                        "login_automatico",
                        False
                    )
                )
            },
            "notificacoes": {
                "som_conclusao": bool(
                    notificacoes.get(
                        "som_conclusao",
                        True
                    )
                ),
                "som_atencao": bool(
                    notificacoes.get(
                        "som_atencao",
                        True
                    )
                ),
                "som_exportacao_disponivel": bool(
                    notificacoes.get(
                        "som_exportacao_disponivel",
                        False
                    )
                ),
                "supervisao": supervisao
            },
            "operacional": {
                "caminhos": caminhos,
                "nomes_arquivos_teste": nomes_arquivos_teste,
                "exportacao": exportacao
            }
        }

    def _inteiro_valido(
        self,
        valor: Any,
        valores_validos: set[int],
        padrao: int
    ) -> int:
        try:
            convertido = int(
                valor
            )
        except (
            TypeError,
            ValueError
        ):
            return padrao

        if convertido not in valores_validos:
            return padrao

        return convertido

    def _normalizar_caminho(
        self,
        caminho: str | Path
    ) -> str:
        texto = str(
            caminho
        ).strip()

        if not texto:
            return ""

        return os.path.expandvars(
            texto
        )

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
