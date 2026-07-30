from __future__ import annotations

import hashlib
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile


class ArquivosExportacaoDbfService:
    """
    Organiza, valida e arquiva os ZIPs baixados do SINAN.

    Fluxo seguro:
    1. baixa em uma pasta temporária privada do ArboHub;
    2. valida a integridade do ZIP;
    3. confirma DENGON para Dengue e CHIKON para Chikungunya;
    4. renomeia os arquivos;
    5. copia a dupla para o histórico anual/mensal;
    6. somente depois remove a pasta temporária.

    O serviço também pode instalar a dupla validada em:
    - F:\\Antropozoonoses\\Teste AB1;
    - F:\\Antropozoonoses\\Teste AB2.

    Ele ainda não substitui os arquivos de Bancos_Atuais.
    """

    AGRAVO_DENGUE = "dengue"
    AGRAVO_CHIKUNGUNYA = "chikungunya"

    PREFIXOS_DBF = {
        AGRAVO_DENGUE: "DENGON",
        AGRAVO_CHIKUNGUNYA: "CHIKON"
    }

    NOMES_ZIP = {
        AGRAVO_DENGUE: "dengue",
        AGRAVO_CHIKUNGUNYA: "chiku"
    }

    PASTAS_HISTORICO = {
        AGRAVO_DENGUE: "dengue",
        AGRAVO_CHIKUNGUNYA: "chiku"
    }

    MESES_PT_BR = {
        1: "01_Janeiro",
        2: "02_Fevereiro",
        3: "03_Março",
        4: "04_Abril",
        5: "05_Maio",
        6: "06_Junho",
        7: "07_Julho",
        8: "08_Agosto",
        9: "09_Setembro",
        10: "10_Outubro",
        11: "11_Novembro",
        12: "12_Dezembro"
    }

    def __init__(
        self,
        raiz_staging: str | Path | None = None,
        raiz_historico: str | Path | None = None
    ):
        if raiz_staging is None:
            local_app_data = os.environ.get(
                "LOCALAPPDATA"
            )

            if local_app_data:
                base_local = Path(local_app_data)
            else:
                base_local = (
                    Path.home()
                    / "AppData"
                    / "Local"
                )

            raiz_staging = (
                base_local
                / "ArboHub"
                / "temp"
                / "exportacoes"
            )

        if raiz_historico is None:
            raiz_historico = (
                Path.home()
                / "Documents"
                / "SINAN"
                / "Historico"
            )

        self.raiz_staging = Path(
            raiz_staging
        ).expanduser().resolve()

        self.raiz_historico = Path(
            raiz_historico
        ).expanduser().resolve()

    # ------------------------------------------------------------------
    # Pasta temporária
    # ------------------------------------------------------------------

    def criar_pasta_lote(
        self,
        lote_id: str,
        data_referencia: date | None = None
    ) -> Path:
        """
        Cria uma pasta temporária legível.

        Exemplo:
        AppData\\Local\\ArboHub\\temp\\exportacoes\\
        exportacao_2026-07-30_10-11-32_ea107174

        O sufixo curto continua permitindo distinguir duas
        execuções feitas no mesmo segundo, sem expor o UUID inteiro.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        lote_id = str(lote_id).strip()

        if not lote_id:
            raise ValueError(
                "O identificador do lote não pode ficar vazio."
            )

        sufixo_lote = "".join(
            caractere
            for caractere in lote_id
            if caractere.isalnum()
        )[:8]

        if not sufixo_lote:
            sufixo_lote = "lote"

        agora = datetime.now()
        nome_base = (
            f"exportacao_{data_referencia.isoformat()}_"
            f"{agora.strftime('%H-%M-%S')}_"
            f"{sufixo_lote}"
        )

        self.raiz_staging.mkdir(
            parents=True,
            exist_ok=True
        )

        pasta = self.raiz_staging / nome_base
        contador = 2

        while pasta.exists():
            pasta = (
                self.raiz_staging
                / f"{nome_base}_{contador}"
            )
            contador += 1

        pasta.mkdir(
            parents=True,
            exist_ok=False
        )

        return pasta

    def caminho_temporario(
        self,
        pasta_lote: str | Path,
        agravo: str
    ) -> Path:
        agravo = self._validar_agravo(
            agravo
        )

        pasta_lote = Path(pasta_lote)
        pasta_lote.mkdir(
            parents=True,
            exist_ok=True
        )

        return (
            pasta_lote
            / f".{agravo}.download"
        )

    # ------------------------------------------------------------------
    # Validação dos downloads
    # ------------------------------------------------------------------

    def validar_e_finalizar(
        self,
        caminho_temporario: str | Path,
        pasta_lote: str | Path,
        agravo: str,
        data_referencia: date | None = None
    ) -> dict[str, object]:
        """
        Valida o download e o renomeia dentro do staging.

        O ZIP ainda não é movido para o histórico neste método.
        """

        agravo = self._validar_agravo(
            agravo
        )
        data_referencia = (
            data_referencia
            or date.today()
        )

        caminho_temporario = Path(
            caminho_temporario
        )
        pasta_lote = Path(
            pasta_lote
        )

        inspecao = self._inspecionar_zip(
            caminho_zip=caminho_temporario,
            agravo=agravo
        )

        nome_final = self._nome_zip_final(
            agravo=agravo,
            data_referencia=data_referencia
        )
        caminho_final = (
            pasta_lote
            / nome_final
        )

        if caminho_final.exists():
            raise FileExistsError(
                "O arquivo final já existe no staging e não "
                f"será sobrescrito: {caminho_final}"
            )

        caminho_temporario.replace(
            caminho_final
        )

        return {
            "agravo": agravo,
            "caminho": caminho_final,
            "nome": caminho_final.name,
            "tamanho_bytes": inspecao[
                "tamanho_bytes"
            ],
            "prefixo_confirmado": inspecao[
                "prefixo_confirmado"
            ],
            "dbfs_encontrados": inspecao[
                "dbfs_encontrados"
            ],
            "zip_valido": True
        }

    def _inspecionar_zip(
        self,
        caminho_zip: str | Path,
        agravo: str
    ) -> dict[str, object]:
        agravo = self._validar_agravo(
            agravo
        )
        caminho_zip = Path(caminho_zip)

        if not caminho_zip.exists():
            raise FileNotFoundError(
                "O arquivo ZIP não foi encontrado: "
                f"{caminho_zip}"
            )

        tamanho = caminho_zip.stat().st_size

        if tamanho <= 0:
            raise RuntimeError(
                "O arquivo baixado está vazio."
            )

        prefixo_esperado = self.PREFIXOS_DBF[
            agravo
        ]

        try:
            with ZipFile(
                caminho_zip,
                "r"
            ) as arquivo_zip:
                arquivo_ruim = (
                    arquivo_zip.testzip()
                )

                if arquivo_ruim is not None:
                    raise RuntimeError(
                        "O ZIP apresentou falha de integridade "
                        f"no item {arquivo_ruim!r}."
                    )

                nomes = arquivo_zip.namelist()

        except BadZipFile as erro:
            raise RuntimeError(
                "O arquivo baixado não é um ZIP válido."
            ) from erro

        dbfs = [
            Path(nome).name
            for nome in nomes
            if Path(nome).suffix.casefold() == ".dbf"
        ]

        dbfs_esperados = [
            nome
            for nome in dbfs
            if nome.upper().startswith(
                prefixo_esperado
            )
        ]

        if not dbfs_esperados:
            encontrados = (
                ", ".join(dbfs)
                if dbfs
                else "nenhum DBF"
            )

            raise RuntimeError(
                f"O ZIP de {agravo} não contém um DBF "
                f"iniciado por {prefixo_esperado}. "
                f"Encontrado: {encontrados}."
            )

        return {
            "agravo": agravo,
            "caminho": caminho_zip,
            "tamanho_bytes": tamanho,
            "prefixo_confirmado": prefixo_esperado,
            "dbfs_encontrados": dbfs_esperados,
            "zip_valido": True
        }

    # ------------------------------------------------------------------
    # Extração segura para validação
    # ------------------------------------------------------------------

    def validar_extracao_historico(
        self,
        data_referencia: date | None = None
    ) -> dict[str, object]:
        """
        Testa a extração dos DBFs já arquivados no histórico.

        O método:
        - abre os ZIPs de Dengue e Chikungunya;
        - localiza somente o DBF com prefixo DENGON ou CHIKON;
        - extrai cada arquivo para uma pasta temporária privada;
        - confirma que os dois arquivos existem e não estão vazios;
        - não lê registros internos;
        - não copia para F:;
        - não substitui Bancos_Atuais;
        - exclui automaticamente a pasta temporária após sucesso.

        Em caso de falha, a pasta temporária é preservada para
        diagnóstico.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        caminho_zip_dengue = self.caminho_historico(
            agravo=self.AGRAVO_DENGUE,
            data_referencia=data_referencia
        )
        caminho_zip_chikungunya = self.caminho_historico(
            agravo=self.AGRAVO_CHIKUNGUNYA,
            data_referencia=data_referencia
        )

        if not caminho_zip_dengue.exists():
            raise FileNotFoundError(
                "O ZIP histórico de Dengue não foi encontrado: "
                f"{caminho_zip_dengue}"
            )

        if not caminho_zip_chikungunya.exists():
            raise FileNotFoundError(
                "O ZIP histórico de Chikungunya não foi "
                f"encontrado: {caminho_zip_chikungunya}"
            )

        pasta_extracao = self.criar_pasta_extracao(
            data_referencia=data_referencia
        )

        sucesso = False

        try:
            dengue = self.extrair_dbf_para_staging(
                caminho_zip=caminho_zip_dengue,
                pasta_destino=pasta_extracao,
                agravo=self.AGRAVO_DENGUE,
                nome_destino=(
                    f"Teste{data_referencia.year}_AB1.dbf"
                )
            )

            chikungunya = self.extrair_dbf_para_staging(
                caminho_zip=caminho_zip_chikungunya,
                pasta_destino=pasta_extracao,
                agravo=self.AGRAVO_CHIKUNGUNYA,
                nome_destino=(
                    f"Teste{data_referencia.year}_AB2.dbf"
                )
            )

            sucesso = True

            resultado = {
                "data_referencia":
                    data_referencia.isoformat(),
                "dengue": dengue,
                "chikungunya": chikungunya,
                "registros_lidos": False,
                "copiado_para_f": False,
                "bancos_atuais_substituidos": False,
                "pasta_temporaria": pasta_extracao
            }

        finally:
            if sucesso:
                self.excluir_pasta_lote(
                    pasta_extracao
                )

        resultado["pasta_temporaria_excluida"] = (
            not pasta_extracao.exists()
        )

        return resultado

    def criar_pasta_extracao(
        self,
        data_referencia: date | None = None
    ) -> Path:
        """
        Cria uma pasta temporária exclusiva para testar a extração.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        agora = datetime.now().strftime(
            "%H-%M-%S-%f"
        )

        self.raiz_staging.mkdir(
            parents=True,
            exist_ok=True
        )

        pasta = (
            self.raiz_staging
            / (
                f"extracao_{data_referencia.isoformat()}_"
                f"{agora}"
            )
        )

        pasta.mkdir(
            parents=True,
            exist_ok=False
        )

        return pasta

    def extrair_dbf_para_staging(
        self,
        caminho_zip: str | Path,
        pasta_destino: str | Path,
        agravo: str,
        nome_destino: str
    ) -> dict[str, object]:
        """
        Extrai exatamente um DBF esperado para a pasta temporária.

        A extração não usa o caminho interno do ZIP, evitando
        travessia de diretórios. O conteúdo do DBF não é lido.
        """

        agravo = self._validar_agravo(
            agravo
        )

        caminho_zip = Path(
            caminho_zip
        ).resolve()

        pasta_destino = Path(
            pasta_destino
        ).resolve()

        pasta_destino.mkdir(
            parents=True,
            exist_ok=True
        )

        prefixo = self.PREFIXOS_DBF[
            agravo
        ]

        nome_destino = Path(
            nome_destino
        ).name

        if Path(nome_destino).suffix.casefold() != ".dbf":
            raise ValueError(
                "O nome de destino precisa terminar em .dbf."
            )

        caminho_destino = (
            pasta_destino
            / nome_destino
        )

        if caminho_destino.exists():
            raise FileExistsError(
                "O DBF de destino já existe no staging: "
                f"{caminho_destino}"
            )

        try:
            with ZipFile(
                caminho_zip,
                "r"
            ) as arquivo_zip:
                candidatos = [
                    info
                    for info in arquivo_zip.infolist()
                    if (
                        not info.is_dir()
                        and Path(
                            info.filename
                        ).suffix.casefold() == ".dbf"
                        and Path(
                            info.filename
                        ).name.upper().startswith(
                            prefixo
                        )
                    )
                ]

                if len(candidatos) != 1:
                    nomes = [
                        Path(
                            info.filename
                        ).name
                        for info in candidatos
                    ]

                    raise RuntimeError(
                        f"Era esperado exatamente um DBF "
                        f"iniciado por {prefixo}; foram "
                        f"encontrados {len(candidatos)}: {nomes}."
                    )

                info = candidatos[0]

                with arquivo_zip.open(
                    info,
                    "r"
                ) as origem, caminho_destino.open(
                    "wb"
                ) as destino:
                    shutil.copyfileobj(
                        origem,
                        destino
                    )

        except BadZipFile as erro:
            raise RuntimeError(
                "O arquivo histórico não é um ZIP válido: "
                f"{caminho_zip}"
            ) from erro

        if (
            not caminho_destino.exists()
            or caminho_destino.stat().st_size <= 0
        ):
            raise RuntimeError(
                "A extração não produziu um DBF válido."
            )

        return {
            "agravo": agravo,
            "zip_origem": caminho_zip,
            "nome_interno": Path(
                info.filename
            ).name,
            "nome_preparado": caminho_destino.name,
            "caminho_temporario": caminho_destino,
            "tamanho_bytes":
                caminho_destino.stat().st_size,
            "prefixo_confirmado": prefixo,
            "extraido": True,
            "registros_lidos": False
        }

    # ------------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------------

    def caminho_historico(
        self,
        agravo: str,
        data_referencia: date | None = None
    ) -> Path:
        agravo = self._validar_agravo(
            agravo
        )
        data_referencia = (
            data_referencia
            or date.today()
        )

        return (
            self.raiz_historico
            / str(data_referencia.year)
            / self.PASTAS_HISTORICO[agravo]
            / self.MESES_PT_BR[data_referencia.month]
            / self._nome_zip_final(
                agravo=agravo,
                data_referencia=data_referencia
            )
        )

    def arquivar_lote(
        self,
        caminho_dengue: str | Path,
        caminho_chikungunya: str | Path,
        pasta_lote: str | Path,
        data_referencia: date | None = None,
        substituir_existentes: bool = False
    ) -> dict[str, object]:
        """
        Arquiva a dupla de ZIPs como uma operação coordenada.

        Antes de alterar o histórico:
        - valida os dois ZIPs;
        - calcula os dois destinos;
        - verifica conflitos;
        - copia ambos para arquivos temporários no destino.

        Se algo falhar, tenta restaurar os arquivos anteriores.
        A pasta de staging só é excluída depois que os dois ZIPs
        chegam corretamente ao histórico.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )
        pasta_lote = Path(
            pasta_lote
        ).resolve()

        itens = [
            {
                "agravo": self.AGRAVO_DENGUE,
                "origem": Path(caminho_dengue).resolve()
            },
            {
                "agravo": self.AGRAVO_CHIKUNGUNYA,
                "origem": Path(
                    caminho_chikungunya
                ).resolve()
            }
        ]

        for item in itens:
            inspecao = self._inspecionar_zip(
                caminho_zip=item["origem"],
                agravo=item["agravo"]
            )
            item["inspecao"] = inspecao
            item["destino"] = self.caminho_historico(
                agravo=item["agravo"],
                data_referencia=data_referencia
            )
            item["temporario_destino"] = (
                item["destino"].parent
                / (
                    f".{item['destino'].name}."
                    f"novo-{os.getpid()}-"
                    f"{datetime.now().strftime('%H%M%S%f')}"
                )
            )
            item["backup"] = None
            item["instalado"] = False

        conflitos = [
            item["destino"]
            for item in itens
            if item["destino"].exists()
        ]

        if conflitos and not substituir_existentes:
            caminhos = "\n".join(
                str(caminho)
                for caminho in conflitos
            )

            raise FileExistsError(
                "Já existe arquivo histórico para esta data:\n"
                f"{caminhos}"
            )

        try:
            # Primeiro copia e valida os dois arquivos temporários.
            for item in itens:
                destino = item["destino"]
                temporario = item[
                    "temporario_destino"
                ]

                destino.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(
                    item["origem"],
                    temporario
                )

                self._inspecionar_zip(
                    caminho_zip=temporario,
                    agravo=item["agravo"]
                )

            # Depois protege os arquivos anteriores.
            for item in itens:
                destino = item["destino"]

                if destino.exists():
                    backup = (
                        destino.parent
                        / (
                            f".{destino.name}.backup-"
                            f"{datetime.now().strftime('%H%M%S%f')}"
                        )
                    )
                    os.replace(
                        destino,
                        backup
                    )
                    item["backup"] = backup

            # Instala a nova dupla.
            for item in itens:
                os.replace(
                    item["temporario_destino"],
                    item["destino"]
                )
                item["instalado"] = True

            # Confirma novamente os arquivos finais.
            for item in itens:
                self._inspecionar_zip(
                    caminho_zip=item["destino"],
                    agravo=item["agravo"]
                )

            # Só após sucesso remove backups e staging.
            for item in itens:
                backup = item["backup"]

                if (
                    backup is not None
                    and backup.exists()
                ):
                    backup.unlink()

                if item["origem"].exists():
                    item["origem"].unlink()

            self.excluir_pasta_lote(
                pasta_lote
            )

            resultado = {
                item["agravo"]: {
                    "agravo": item["agravo"],
                    "caminho": item["destino"],
                    "nome": item["destino"].name,
                    "substituiu_existente": (
                        item["backup"] is not None
                    ),
                    "prefixo_confirmado": (
                        item["inspecao"][
                            "prefixo_confirmado"
                        ]
                    ),
                    "dbfs_encontrados": (
                        item["inspecao"][
                            "dbfs_encontrados"
                        ]
                    )
                }
                for item in itens
            }

            resultado["pasta_temporaria_excluida"] = (
                not pasta_lote.exists()
            )

            return resultado

        except Exception:
            # Remove novas instalações parciais.
            for item in reversed(itens):
                destino = item["destino"]
                backup = item["backup"]
                temporario = item[
                    "temporario_destino"
                ]

                try:
                    if item["instalado"] and destino.exists():
                        destino.unlink()
                except Exception:
                    pass

                try:
                    if (
                        backup is not None
                        and backup.exists()
                    ):
                        os.replace(
                            backup,
                            destino
                        )
                except Exception:
                    pass

                try:
                    if temporario.exists():
                        temporario.unlink()
                except Exception:
                    pass

            raise

    # ------------------------------------------------------------------
    # Instalação segura nas pastas de teste
    # ------------------------------------------------------------------

    def caminhos_pastas_teste(
        self,
        data_referencia: date | None = None,
        pasta_ab1: str | Path | None = None,
        pasta_ab2: str | Path | None = None
    ) -> dict[str, Path]:
        """
        Retorna os caminhos finais esperados para o ano informado.

        Por padrão:
        Dengue:
        F:\\Antropozoonoses\\Teste AB1\\TesteAAAA_AB1.dbf

        Chikungunya:
        F:\\Antropozoonoses\\Teste AB2\\TesteAAAA_AB2.dbf
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        if pasta_ab1 is None:
            pasta_ab1 = Path(
                r"F:\Antropozoonoses\Teste AB1"
            )

        if pasta_ab2 is None:
            pasta_ab2 = Path(
                r"F:\Antropozoonoses\Teste AB2"
            )

        pasta_ab1 = Path(pasta_ab1)
        pasta_ab2 = Path(pasta_ab2)

        return {
            self.AGRAVO_DENGUE: (
                pasta_ab1
                / f"Teste{data_referencia.year}_AB1.dbf"
            ),
            self.AGRAVO_CHIKUNGUNYA: (
                pasta_ab2
                / f"Teste{data_referencia.year}_AB2.dbf"
            )
        }

    def instalar_dbfs_pastas_teste(
        self,
        data_referencia: date | None = None,
        pasta_ab1: str | Path | None = None,
        pasta_ab2: str | Path | None = None
    ) -> dict[str, object]:
        """
        Extrai e instala a dupla de DBFs nas pastas de teste.

        Antes da instalação, considera como arquivo anterior
        qualquer arquivo com o mesmo nome-base do destino e com
        extensão ``.dbf`` ou ``.txt``.

        Exemplos removidos após sucesso:
        - Teste2026_AB1.dbf
        - Teste2026_AB1.txt
        - Teste2026_AB2.dbf
        - Teste2026_AB2.txt

        Proteções:
        - valida os dois ZIPs históricos;
        - confirma DENGON e CHIKON;
        - exige que as pastas AB1 e AB2 já existam;
        - copia primeiro para arquivos temporários no destino;
        - compara tamanho e SHA-256;
        - move todos os arquivos anteriores para backup;
        - instala a nova dupla;
        - restaura todos os anteriores se algo falhar;
        - exclui os backups apenas após sucesso;
        - exclui o staging apenas após sucesso.

        Nenhum registro interno do DBF é interpretado.
        """

        data_referencia = (
            data_referencia
            or date.today()
        )

        destinos = self.caminhos_pastas_teste(
            data_referencia=data_referencia,
            pasta_ab1=pasta_ab1,
            pasta_ab2=pasta_ab2
        )

        for agravo, destino in destinos.items():
            if not destino.parent.exists():
                raise FileNotFoundError(
                    "A pasta de destino não foi encontrada para "
                    f"{agravo}: {destino.parent}"
                )

            if not destino.parent.is_dir():
                raise NotADirectoryError(
                    "O destino informado não é uma pasta: "
                    f"{destino.parent}"
                )

        caminho_zip_dengue = self.caminho_historico(
            agravo=self.AGRAVO_DENGUE,
            data_referencia=data_referencia
        )
        caminho_zip_chikungunya = self.caminho_historico(
            agravo=self.AGRAVO_CHIKUNGUNYA,
            data_referencia=data_referencia
        )

        if not caminho_zip_dengue.exists():
            raise FileNotFoundError(
                "O ZIP histórico de Dengue não foi encontrado: "
                f"{caminho_zip_dengue}"
            )

        if not caminho_zip_chikungunya.exists():
            raise FileNotFoundError(
                "O ZIP histórico de Chikungunya não foi "
                f"encontrado: {caminho_zip_chikungunya}"
            )

        pasta_staging = self.criar_pasta_extracao(
            data_referencia=data_referencia
        )

        itens = []
        sucesso = False

        try:
            dengue_extraida = self.extrair_dbf_para_staging(
                caminho_zip=caminho_zip_dengue,
                pasta_destino=pasta_staging,
                agravo=self.AGRAVO_DENGUE,
                nome_destino=(
                    f"Teste{data_referencia.year}_AB1.dbf"
                )
            )

            chikungunya_extraida = (
                self.extrair_dbf_para_staging(
                    caminho_zip=caminho_zip_chikungunya,
                    pasta_destino=pasta_staging,
                    agravo=self.AGRAVO_CHIKUNGUNYA,
                    nome_destino=(
                        f"Teste{data_referencia.year}_AB2.dbf"
                    )
                )
            )

            extraidos = {
                self.AGRAVO_DENGUE: dengue_extraida,
                self.AGRAVO_CHIKUNGUNYA:
                    chikungunya_extraida
            }

            identificador = (
                datetime.now().strftime("%Y%m%d%H%M%S%f")
            )

            for agravo in (
                self.AGRAVO_DENGUE,
                self.AGRAVO_CHIKUNGUNYA
            ):
                origem = Path(
                    extraidos[agravo][
                        "caminho_temporario"
                    ]
                )
                destino = destinos[agravo]

                temporario_destino = (
                    destino.parent
                    / (
                        f".{destino.name}.novo-"
                        f"{os.getpid()}-{identificador}"
                    )
                )

                arquivos_anteriores = (
                    self._localizar_arquivos_anteriores_teste(
                        destino
                    )
                )

                backups = []

                for indice, anterior in enumerate(
                    arquivos_anteriores,
                    start=1
                ):
                    backup = (
                        anterior.parent
                        / (
                            f".{anterior.name}.backup-"
                            f"{identificador}-{indice}"
                        )
                    )

                    backups.append(
                        {
                            "original": anterior,
                            "backup": backup,
                            "criado": False
                        }
                    )

                itens.append(
                    {
                        "agravo": agravo,
                        "origem": origem,
                        "destino": destino,
                        "temporario_destino":
                            temporario_destino,
                        "arquivos_anteriores":
                            arquivos_anteriores,
                        "backups": backups,
                        "instalado": False,
                        "hash_origem":
                            self._sha256_arquivo(origem),
                        "tamanho_origem":
                            origem.stat().st_size,
                        "prefixo_confirmado":
                            extraidos[agravo][
                                "prefixo_confirmado"
                            ],
                        "nome_interno":
                            extraidos[agravo][
                                "nome_interno"
                            ]
                    }
                )

            # Copia os dois arquivos para temporários no próprio
            # volume de destino e valida antes de remover algo.
            for item in itens:
                shutil.copy2(
                    item["origem"],
                    item["temporario_destino"]
                )

                self._validar_copia_identica(
                    origem=item["origem"],
                    copia=item["temporario_destino"]
                )

            # Protege todos os arquivos anteriores, inclusive
            # placeholders .txt com o mesmo nome-base.
            for item in itens:
                for registro_backup in item["backups"]:
                    original = registro_backup["original"]
                    backup = registro_backup["backup"]

                    if original.exists():
                        os.replace(
                            original,
                            backup
                        )
                        registro_backup["criado"] = True

            # Instala a nova dupla em formato DBF.
            for item in itens:
                os.replace(
                    item["temporario_destino"],
                    item["destino"]
                )
                item["instalado"] = True

            # Validação final dos dois destinos.
            for item in itens:
                self._validar_copia_identica(
                    origem=item["origem"],
                    copia=item["destino"]
                )

            # Somente após sucesso remove todos os backups.
            for item in itens:
                for registro_backup in item["backups"]:
                    backup = registro_backup["backup"]

                    if (
                        registro_backup["criado"]
                        and backup.exists()
                    ):
                        backup.unlink()

            sucesso = True

            resultado = {
                item["agravo"]: {
                    "agravo": item["agravo"],
                    "destino": item["destino"],
                    "nome": item["destino"].name,
                    "tamanho_bytes":
                        item["destino"].stat().st_size,
                    "sha256":
                        self._sha256_arquivo(
                            item["destino"]
                        ),
                    "substituiu_existente": bool(
                        item["arquivos_anteriores"]
                    ),
                    "arquivos_anteriores_removidos": [
                        caminho.name
                        for caminho in item[
                            "arquivos_anteriores"
                        ]
                    ],
                    "prefixo_confirmado":
                        item["prefixo_confirmado"],
                    "nome_interno":
                        item["nome_interno"],
                    "instalado": True
                }
                for item in itens
            }

            resultado.update(
                {
                    "data_referencia":
                        data_referencia.isoformat(),
                    "registros_lidos": False,
                    "bancos_atuais_substituidos": False,
                    "pasta_staging": pasta_staging
                }
            )

        except Exception:
            # Remove novas instalações e restaura todos os
            # arquivos anteriores, inclusive os .txt.
            for item in reversed(itens):
                try:
                    if (
                        item["instalado"]
                        and item["destino"].exists()
                    ):
                        item["destino"].unlink()
                except Exception:
                    pass

                for registro_backup in reversed(
                    item["backups"]
                ):
                    original = registro_backup["original"]
                    backup = registro_backup["backup"]

                    try:
                        if (
                            registro_backup["criado"]
                            and backup.exists()
                        ):
                            os.replace(
                                backup,
                                original
                            )
                    except Exception:
                        pass

                try:
                    if item[
                        "temporario_destino"
                    ].exists():
                        item[
                            "temporario_destino"
                        ].unlink()
                except Exception:
                    pass

            raise

        finally:
            if sucesso:
                self.excluir_pasta_lote(
                    pasta_staging
                )

        resultado["pasta_temporaria_excluida"] = (
            not pasta_staging.exists()
        )

        return resultado

    def _localizar_arquivos_anteriores_teste(
        self,
        destino_dbf: str | Path
    ) -> list[Path]:
        """
        Localiza variantes anteriores do mesmo arquivo lógico.

        Apenas ``.dbf`` e ``.txt`` são aceitos para evitar apagar
        outros arquivos que possam existir na pasta.
        """

        destino_dbf = Path(
            destino_dbf
        )

        nome_base = destino_dbf.stem.casefold()
        extensoes_permitidas = {
            ".dbf",
            ".txt"
        }

        encontrados = []

        for arquivo in destino_dbf.parent.iterdir():
            if not arquivo.is_file():
                continue

            if arquivo.name.startswith("."):
                continue

            if arquivo.stem.casefold() != nome_base:
                continue

            if arquivo.suffix.casefold() not in (
                extensoes_permitidas
            ):
                continue

            encontrados.append(
                arquivo
            )

        return sorted(
            encontrados,
            key=lambda caminho: caminho.name.casefold()
        )

    def _validar_copia_identica(
        self,
        origem: str | Path,
        copia: str | Path
    ):
        origem = Path(origem)
        copia = Path(copia)

        if not copia.exists():
            raise FileNotFoundError(
                "A cópia esperada não foi encontrada: "
                f"{copia}"
            )

        if origem.stat().st_size != copia.stat().st_size:
            raise RuntimeError(
                "A cópia possui tamanho diferente do arquivo "
                "de origem."
            )

        if (
            self._sha256_arquivo(origem)
            != self._sha256_arquivo(copia)
        ):
            raise RuntimeError(
                "A verificação SHA-256 indicou que a cópia "
                "não é idêntica ao arquivo de origem."
            )

    def _sha256_arquivo(
        self,
        caminho: str | Path
    ) -> str:
        """
        Calcula apenas o hash de integridade do arquivo.

        O DBF não é interpretado e nenhum conteúdo é salvo em log.
        """

        caminho = Path(caminho)
        hash_arquivo = hashlib.sha256()

        with caminho.open("rb") as arquivo:
            while True:
                bloco = arquivo.read(
                    1024 * 1024
                )

                if not bloco:
                    break

                hash_arquivo.update(bloco)

        return hash_arquivo.hexdigest()

    # ------------------------------------------------------------------
    # Limpeza
    # ------------------------------------------------------------------

    def limpar_temporario(
        self,
        caminho_temporario: str | Path
    ):
        caminho_temporario = Path(
            caminho_temporario
        )

        if caminho_temporario.exists():
            caminho_temporario.unlink()

    def excluir_pasta_lote(
        self,
        pasta_lote: str | Path
    ):
        """
        Exclui somente pastas localizadas dentro da raiz de staging.

        Essa verificação impede que um caminho incorreto provoque
        remoção fora da área temporária do ArboHub.
        """

        pasta_lote = Path(
            pasta_lote
        ).resolve()
        raiz = self.raiz_staging.resolve()

        try:
            pasta_lote.relative_to(
                raiz
            )
        except ValueError as erro:
            raise RuntimeError(
                "A pasta informada não pertence ao staging "
                "seguro do ArboHub."
            ) from erro

        if pasta_lote == raiz:
            raise RuntimeError(
                "A raiz geral de staging não pode ser excluída."
            )

        if pasta_lote.exists():
            shutil.rmtree(
                pasta_lote
            )

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def _nome_zip_final(
        self,
        agravo: str,
        data_referencia: date
    ) -> str:
        return (
            f"{self.NOMES_ZIP[agravo]}_"
            f"{data_referencia.isoformat()}.zip"
        )

    def _validar_agravo(
        self,
        agravo: str
    ) -> str:
        agravo = str(
            agravo
        ).strip().casefold()

        if agravo not in self.PREFIXOS_DBF:
            raise ValueError(
                "Agravo inválido. Use dengue ou chikungunya."
            )

        return agravo