from __future__ import annotations

import re
import shutil
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from time import monotonic
from typing import Callable

from playwright.sync_api import Frame, Locator, Page

from app.automation.gal.navegador_gal import NavegadorGal


class ExportacaoSorotipoGal:
    """Prepara e baixa o relatorio semanal de sorotipo do GAL."""

    # Assim como no SINAN, estes valores sao limites maximos. Quando o
    # controle ou a tela esperada ja esta disponivel, a rotina continua
    # imediatamente, sem pausas fixas.
    INTERVALO_VERIFICACAO_MS = 60
    TEMPO_CONFIRMACAO_ACAO_SEGUNDOS = 2.5
    TEMPO_CONFIRMACAO_MENU_SEGUNDOS = 1.0

    CAMPOS_RELATORIO = (
        "Requisição, Data do 1º Sintomas, Paciente, "
        "Municipio de Residência, IBGE Município de Residência, "
        "Data da Liberação, Status Exame"
    )
    EXAME = "Pesquisa de Arbovírus (ZDC)"
    METODO = "RT-PCR em tempo real"
    PERIODO = "Por data de liberação"

    def __init__(self, navegador: NavegadorGal):
        self.navegador = navegador

    def baixar(
        self,
        pasta_temporaria: str | Path,
        data_inicio: date,
        data_fim: date,
        cancelado: Callable[[], bool] | None = None,
        ao_status: Callable[[str], None] | None = None
    ) -> Path:
        pasta_temporaria = Path(pasta_temporaria)
        pasta_temporaria.mkdir(parents=True, exist_ok=True)

        self._informar(
            ao_status,
            (
                "Fechando a janela 'Notícias do GAL' antes de "
                "procurar o menu Biologia Médica."
            )
        )
        self._fechar_noticias(cancelado=cancelado)
        self._navegar_para_relatorio(cancelado=cancelado)

        self._informar(
            ao_status,
            "Preenchendo campos, período, exame e método."
        )
        self._configurar_relatorio(
            data_inicio=data_inicio,
            data_fim=data_fim,
            cancelado=cancelado
        )

        self._informar(
            ao_status,
            "Solicitando o arquivo ao GAL."
        )
        _pagina, botao = self._localizar_texto(
            ("Gerar",),
            tempo_limite_segundos=20,
            cancelado=cancelado,
            preferir_controle=True
        )

        pasta_downloads = self.navegador.pasta_downloads

        if pasta_downloads is None:
            raise RuntimeError(
                "O navegador do GAL não disponibilizou a pasta "
                "privada de downloads."
            )

        arquivos_anteriores = self._listar_arquivos_downloads(
            pasta_downloads
        )

        try:
            botao.click(force=True, timeout=3_000)
        except Exception as erro:
            raise RuntimeError(
                "O botão Gerar foi localizado, mas não pôde ser "
                "acionado no GAL."
            ) from erro

        return self._aguardar_arquivo_baixado(
            pasta_downloads=pasta_downloads,
            arquivos_anteriores=arquivos_anteriores,
            pasta_destino=pasta_temporaria,
            data_inicio=data_inicio,
            data_fim=data_fim,
            cancelado=cancelado,
            ao_status=ao_status
        )

    def _aguardar_arquivo_baixado(
        self,
        pasta_downloads: Path,
        arquivos_anteriores: set[Path],
        pasta_destino: Path,
        data_inicio: date,
        data_fim: date,
        cancelado: Callable[[], bool] | None,
        ao_status: Callable[[str], None] | None
    ) -> Path:
        """
        Observa a pasta privada do Chromium ate o arquivo estabilizar.

        O GAL antigo pode iniciar o download a partir de outro frame e
        entregar um nome aleatorio, sem extensao. Nesses casos o evento
        ``download`` da pagina que contem o botao nao e confiavel, mas o
        Chromium ainda grava os bytes nesta pasta controlada.
        """

        limite = monotonic() + 120
        tamanhos: dict[Path, tuple[int, int]] = {}
        download_detectado = False

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)
            atuais = self._listar_arquivos_downloads(pasta_downloads)
            novos = sorted(
                atuais - arquivos_anteriores,
                key=lambda arquivo: arquivo.name,
                reverse=True
            )

            if novos and not download_detectado:
                download_detectado = True
                self._informar(
                    ao_status,
                    "Download detectado. Aguardando o arquivo terminar."
                )

            for arquivo in novos:
                if self._arquivo_temporario_do_navegador(arquivo):
                    continue

                try:
                    tamanho = arquivo.stat().st_size
                except OSError:
                    continue

                if tamanho <= 0:
                    continue

                tamanho_anterior, repeticoes = tamanhos.get(
                    arquivo,
                    (-1, 0)
                )
                repeticoes = (
                    repeticoes + 1
                    if tamanho == tamanho_anterior
                    else 1
                )
                tamanhos[arquivo] = (tamanho, repeticoes)

                # Cinco leituras iguais, com intervalo de 120 ms,
                # evitam copiar um arquivo que ainda esta crescendo.
                if repeticoes < 5:
                    continue

                return self._copiar_download_concluido(
                    origem=arquivo,
                    pasta_destino=pasta_destino,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )

            self._esperar(120)

        if download_detectado:
            raise RuntimeError(
                "O GAL iniciou o download, mas o arquivo não terminou "
                "dentro de 2 minutos."
            )

        raise RuntimeError(
            "O GAL não iniciou o download após o botão Gerar. Use a "
            "opção 'Usar arquivo já baixado' caso o relatório tenha "
            "sido salvo fora do navegador do ArboHub."
        )

    def _copiar_download_concluido(
        self,
        origem: Path,
        pasta_destino: Path,
        data_inicio: date,
        data_fim: date
    ) -> Path:
        extensao = self._identificar_extensao_relatorio(origem)
        nome_base = (
            f"relatorio_gal_{data_inicio:%Y%m%d}_{data_fim:%Y%m%d}"
        )
        destino = pasta_destino / f"{nome_base}{extensao}"
        contador = 2

        while destino.exists():
            destino = pasta_destino / (
                f"{nome_base}_{contador}{extensao}"
            )
            contador += 1

        shutil.copy2(origem, destino)

        if (
            not destino.is_file()
            or destino.stat().st_size != origem.stat().st_size
        ):
            try:
                destino.unlink(missing_ok=True)
            except OSError:
                pass

            raise RuntimeError(
                "O arquivo informado pelo GAL não foi copiado "
                "corretamente."
            )

        return destino

    def _identificar_extensao_relatorio(self, arquivo: Path) -> str:
        """Reconhece o formato mesmo quando o GAL usa um nome UUID."""

        if zipfile.is_zipfile(arquivo):
            try:
                with zipfile.ZipFile(arquivo) as arquivo_zip:
                    nomes = {
                        item.filename.casefold()
                        for item in arquivo_zip.infolist()
                    }

                if (
                    "[content_types].xml" in nomes
                    and any(nome.startswith("xl/") for nome in nomes)
                ):
                    return ".xlsx"
            except (OSError, zipfile.BadZipFile):
                pass

            return ".zip"

        try:
            conteudo = arquivo.read_bytes()
        except OSError as erro:
            raise RuntimeError(
                "O arquivo baixado pelo GAL não pôde ser lido."
            ) from erro

        if conteudo.startswith(
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        ):
            return ".xls"

        if self._parece_dbf(conteudo):
            return ".dbf"

        texto = self._decodificar_texto_relatorio(conteudo)

        if texto is not None:
            normalizado = self._normalizar(texto[:16_384])
            inicio = normalizado.lstrip()

            if (
                "<workbook" in inicio
                or "urn:schemas-microsoft-com:office:spreadsheet"
                in inicio
            ):
                return ".xls"

            if "<html" in inicio or "<!doctype html" in inicio:
                if (
                    "<table" in inicio
                    and any(
                        marcador in normalizado
                        for marcador in (
                            "requisicao",
                            "data da liberacao",
                            "status exame"
                        )
                    )
                ):
                    # Alguns relatorios antigos sao planilhas HTML que
                    # o Excel abre normalmente como XLS.
                    return ".xls"

                raise RuntimeError(
                    "O GAL baixou uma página HTML em vez do relatório. "
                    "Gere novamente ou use 'Usar arquivo já baixado'."
                )

            linhas = [
                linha
                for linha in texto.splitlines()
                if linha.strip()
            ]

            if linhas and any(
                separador in linhas[0]
                for separador in (";", "\t", ",")
            ):
                return ".csv"

            if linhas:
                return ".txt"

        extensao_original = arquivo.suffix.casefold()

        if extensao_original in {
            ".csv",
            ".xlsx",
            ".xls",
            ".txt",
            ".dbf"
        }:
            return extensao_original

        raise RuntimeError(
            "O GAL baixou um arquivo, mas o formato do relatório não "
            "foi reconhecido. Use 'Usar arquivo já baixado' e "
            "selecione o arquivo gerado pelo portal."
        )

    def _parece_dbf(self, conteudo: bytes) -> bool:
        if len(conteudo) < 32 or conteudo[0] not in {
            0x02,
            0x03,
            0x04,
            0x05,
            0x30,
            0x31,
            0x32,
            0x43,
            0x63,
            0x83,
            0x8B,
            0x8E,
            0xF5
        }:
            return False

        tamanho_cabecalho = int.from_bytes(conteudo[8:10], "little")
        tamanho_registro = int.from_bytes(conteudo[10:12], "little")
        return (
            32 <= tamanho_cabecalho <= len(conteudo)
            and tamanho_registro > 0
        )

    def _decodificar_texto_relatorio(
        self,
        conteudo: bytes
    ) -> str | None:
        if not conteudo or b"\x00" in conteudo[:4_096]:
            return None

        for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texto = conteudo.decode(codificacao)
            except UnicodeDecodeError:
                continue

            imprimiveis = sum(
                caractere.isprintable() or caractere in "\r\n\t"
                for caractere in texto
            )

            if texto and imprimiveis / len(texto) >= 0.85:
                return texto

        return None

    def _listar_arquivos_downloads(self, pasta: Path) -> set[Path]:
        try:
            return {
                arquivo
                for arquivo in pasta.iterdir()
                if arquivo.is_file()
            }
        except OSError:
            return set()

    def _arquivo_temporario_do_navegador(self, arquivo: Path) -> bool:
        nome = arquivo.name.casefold()
        return nome.endswith((".crdownload", ".part", ".tmp"))

    def _fechar_noticias(
        self,
        cancelado: Callable[[], bool] | None
    ):
        """
        Fecha o aviso modal exibido logo depois do login.

        O GAL antigo pode apresentar ``Fechar`` como ``input``, link,
        botao ou em uma pagina popup. A navegacao pelo menu so comeca
        depois que o desaparecimento do aviso foi confirmado.
        """

        limite_aparicao = monotonic() + 8
        aviso_encontrado = False
        area_pronta_desde: float | None = None

        while monotonic() < limite_aparicao:
            self._verificar_cancelamento(cancelado)
            alvo = self._localizar_noticias()

            if alvo is None:
                if aviso_encontrado:
                    return

                if self._item_arvore_visivel(
                    ("Biologia Médica", "Biologia Medica")
                ):
                    if area_pronta_desde is None:
                        area_pronta_desde = monotonic()
                    elif monotonic() - area_pronta_desde >= 0.8:
                        return
                else:
                    area_pronta_desde = None

                self._esperar(self.INTERVALO_VERIFICACAO_MS)
                continue

            aviso_encontrado = True
            pagina, botao, pagina_popup = alvo

            if botao is not None:
                try:
                    botao.click(force=True, timeout=3_000)
                except Exception:
                    pass

            self._esperar_com_pagina_disponivel(
                self.INTERVALO_VERIFICACAO_MS
            )

            if pagina_popup and not pagina.is_closed():
                try:
                    pagina.close()
                except Exception:
                    pass

            if self._aguardar_noticias_fechadas(
                tempo_limite_segundos=5,
                cancelado=cancelado
            ):
                return

        if aviso_encontrado or self._localizar_noticias() is not None:
            raise RuntimeError(
                "A janela 'Notícias do GAL' não pôde ser fechada. "
                "Feche-a manualmente e inicie a atualização novamente."
            )

    def _localizar_noticias(
        self
    ) -> tuple[Page, Locator | None, bool] | None:
        for pagina in reversed(self.navegador.paginas_ativas()):
            if pagina.is_closed():
                continue

            pagina_popup = self._pagina_e_noticias(pagina)

            for quadro in reversed(pagina.frames):
                botao = self._localizar_botao_fechar(quadro)

                if botao is not None and (
                    pagina_popup
                    or self._quadro_tem_titulo_noticias(quadro)
                    or len(self.navegador.paginas_ativas()) > 1
                ):
                    return pagina, botao, pagina_popup

            if pagina_popup:
                return pagina, None, True

        return None

    def _localizar_botao_fechar(
        self,
        quadro: Page | Frame
    ) -> Locator | None:
        seletores = (
            'input[type="button" i][value="Fechar" i]',
            'input[type="submit" i][value="Fechar" i]',
            'button',
            'a',
            '[role="button"]'
        )

        for seletor in seletores:
            try:
                candidatos = quadro.locator(seletor)

                for indice in range(min(candidatos.count(), 30)):
                    candidato = candidatos.nth(indice)

                    if not candidato.is_visible():
                        continue

                    try:
                        texto_interno = (
                            candidato.inner_text(timeout=1_000) or ""
                        )
                    except Exception:
                        texto_interno = ""

                    textos = (
                        candidato.get_attribute("value") or "",
                        candidato.get_attribute("title") or "",
                        candidato.get_attribute("aria-label") or "",
                        texto_interno
                    )

                    if any(
                        self._normalizar(texto) == "fechar"
                        for texto in textos
                    ):
                        return candidato
            except Exception:
                continue

        return None

    def _pagina_e_noticias(self, pagina: Page) -> bool:
        try:
            titulo = self._normalizar(pagina.title())
        except Exception:
            return False

        return "noticias do gal" in titulo

    def _quadro_tem_titulo_noticias(
        self,
        quadro: Page | Frame
    ) -> bool:
        for texto in ("Notícias do GAL", "Noticias do GAL"):
            try:
                candidatos = quadro.get_by_text(texto, exact=False)

                for indice in range(min(candidatos.count(), 5)):
                    if candidatos.nth(indice).is_visible():
                        return True
            except Exception:
                continue

        return False

    def _aguardar_noticias_fechadas(
        self,
        tempo_limite_segundos: int,
        cancelado: Callable[[], bool] | None
    ) -> bool:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            if self._localizar_noticias() is None:
                return True

            self._esperar_com_pagina_disponivel(
                self.INTERVALO_VERIFICACAO_MS
            )

        return self._localizar_noticias() is None

    def _esperar_com_pagina_disponivel(self, milissegundos: int):
        paginas = self.navegador.paginas_ativas()

        if not paginas:
            raise RuntimeError("A janela do GAL foi fechada.")

        paginas[-1].wait_for_timeout(milissegundos)

    def _navegar_para_relatorio(
        self,
        cancelado: Callable[[], bool] | None
    ):
        self._garantir_item_aberto(
            textos=("Biologia Médica", "Biologia Medica"),
            textos_filho=("Relatórios", "Relatorios"),
            cancelado=cancelado
        )
        self._garantir_item_aberto(
            textos=("Relatórios", "Relatorios"),
            textos_filho=("Epidemiológicos", "Epidemiologicos"),
            cancelado=cancelado
        )
        self._garantir_item_aberto(
            textos=("Epidemiológicos", "Epidemiologicos"),
            textos_filho=(
                "Relatórios epidemiológicos por Exame",
                "Relatorios epidemiologicos por Exame"
            ),
            cancelado=cancelado
        )
        self._abrir_relatorio_por_exame(cancelado=cancelado)
        self._aguardar_formulario_relatorio(cancelado=cancelado)

    def _garantir_item_aberto(
        self,
        textos: tuple[str, ...],
        textos_filho: tuple[str, ...],
        cancelado: Callable[[], bool] | None
    ):
        if self._item_arvore_visivel(textos_filho):
            return

        item = self._localizar_item_arvore(
            textos=textos,
            tempo_limite_segundos=20,
            cancelado=cancelado
        )

        # O menu do GAL e uma arvore antiga do ExtJS. Clicar no texto
        # pode apenas selecionar a linha; o controle correto para abrir
        # o ramo e o icone +/- (x-tree-ec-icon) no mesmo no.
        controles = self._controles_expansao_item(item)

        confirmacao = lambda: self._item_arvore_visivel(textos_filho)

        for controle in controles:
            if self._acionar_menu_e_confirmar(
                elemento=controle,
                confirmacao=confirmacao,
                cancelado=cancelado
            ):
                return

        if self._acionar_menu_e_confirmar(
            elemento=item,
            confirmacao=confirmacao,
            cancelado=cancelado,
            permitir_clique_duplo=True
        ):
            return

        raise RuntimeError(
            f"O menu '{textos[0]}' não abriu no GAL."
        )

    def _acionar_menu_e_confirmar(
        self,
        elemento: Locator,
        confirmacao: Callable[[], bool],
        cancelado: Callable[[], bool] | None,
        permitir_clique_duplo: bool = False
    ) -> bool:
        """Abre um ramo da arvore sem acumular esperas longas."""

        if confirmacao():
            return True

        try:
            elemento.scroll_into_view_if_needed()
        except Exception:
            pass

        clicou = False

        try:
            elemento.click(force=True, timeout=800)
            clicou = True
        except Exception:
            try:
                elemento.evaluate(
                    """
                    (elemento) => {
                        const controle = elemento.closest(
                            "a, img, [onclick]"
                        ) || elemento;
                        controle.click();
                    }
                    """
                )
                clicou = True
            except Exception:
                pass

        if clicou and self._aguardar_condicao(
            condicao=confirmacao,
            tempo_limite_segundos=self.TEMPO_CONFIRMACAO_MENU_SEGUNDOS,
            cancelado=cancelado
        ):
            return True

        if not permitir_clique_duplo or confirmacao():
            return confirmacao()

        try:
            elemento.dblclick(force=True, timeout=800)
        except Exception:
            return confirmacao()

        return self._aguardar_condicao(
            condicao=confirmacao,
            tempo_limite_segundos=self.TEMPO_CONFIRMACAO_MENU_SEGUNDOS,
            cancelado=cancelado
        )

    def _controles_expansao_item(
        self,
        item: Locator
    ) -> list[Locator]:
        controles: list[Locator] = []

        try:
            no = item.locator(
                "xpath=ancestor-or-self::*["
                "contains(concat(' ', normalize-space(@class), ' '), "
                "' x-tree-node-el ')][1]"
            )

            if no.count():
                expansores = no.first.locator(
                    ".x-tree-ec-icon, "
                    "img[class*='x-tree-ec-icon'], "
                    "[class*='tree-ec-icon']"
                )

                for indice in range(min(expansores.count(), 4)):
                    expansor = expansores.nth(indice)

                    if expansor.is_visible():
                        controles.append(expansor)
        except Exception:
            pass

        try:
            linha = item.locator(
                "xpath=ancestor-or-self::*[self::div or self::td or "
                "self::li][1]"
            )
            imagens = linha.locator("img")

            for indice in range(min(imagens.count(), 4)):
                imagem = imagens.nth(indice)

                if imagem.is_visible():
                    controles.append(imagem)
        except Exception:
            pass

        return controles

    def _localizar_item_arvore(
        self,
        textos: tuple[str, ...],
        tempo_limite_segundos: float,
        cancelado: Callable[[], bool] | None
    ) -> Locator:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)
            item = self._procurar_item_arvore(textos)

            if item is not None:
                return item

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        raise RuntimeError(
            f"O item de menu '{textos[0]}' não foi localizado no GAL."
        )

    def _procurar_item_arvore(
        self,
        textos: tuple[str, ...]
    ) -> Locator | None:
        for _pagina, quadro in self.navegador.quadros_ativos():
            for texto in textos:
                for exato in (True, False):
                    try:
                        candidatos = quadro.get_by_text(
                            texto,
                            exact=exato
                        )

                        for indice in range(min(candidatos.count(), 16)):
                            candidato = candidatos.nth(indice)

                            if (
                                candidato.is_visible()
                                and self._elemento_pertence_arvore(candidato)
                            ):
                                return candidato
                    except Exception:
                        continue

        return None

    def _item_arvore_visivel(self, textos: tuple[str, ...]) -> bool:
        return self._procurar_item_arvore(textos) is not None

    def _elemento_pertence_arvore(self, elemento: Locator) -> bool:
        try:
            no = elemento.locator(
                "xpath=ancestor-or-self::*["
                "contains(@class, 'x-tree-node')][1]"
            )

            if no.count() > 0:
                return True
        except Exception:
            pass

        # Recuperacao para variantes antigas sem as classes padrao. O
        # navegador do ArboHub usa viewport fixo e a arvore fica na coluna
        # esquerda; evita confundir o menu com textos da grade central.
        try:
            caixa = elemento.bounding_box()
            return caixa is not None and caixa["x"] < 320
        except Exception:
            return False

    def _abrir_relatorio_por_exame(
        self,
        cancelado: Callable[[], bool] | None
    ):
        """
        Seleciona a linha do relatorio e aciona ``Gerar Relatório``.

        Na grade antiga do GAL, clicar no nome apenas deixa a linha azul.
        A abertura real ocorre pelo botao da barra superior. Cada tentativa
        so e considerada concluida quando o formulario aparece.
        """

        if self._formulario_relatorio_esta_aberto():
            return

        textos_relatorio = (
            "Relatórios Epidemiológicos por Exame",
            "Relatórios epidemiológicos por Exame",
            "Relatorios Epidemiologicos por Exame",
            "Relatorios epidemiologicos por Exame"
        )
        limite = monotonic() + 20
        ultima_falha: Exception | None = None

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            localizado = self._procurar_texto_visivel(
                textos=textos_relatorio,
                preferir_controle=False
            )

            if localizado is None:
                self._esperar(self.INTERVALO_VERIFICACAO_MS)
                continue

            _pagina, item = localizado

            try:
                item.scroll_into_view_if_needed()
                item.click(timeout=2_000)
            except Exception as erro:
                ultima_falha = erro

                try:
                    item.click(force=True, timeout=2_000)
                except Exception as erro_forcado:
                    ultima_falha = erro_forcado
                    self._esperar(self.INTERVALO_VERIFICACAO_MS)
                    continue

            botao_localizado = self._procurar_texto_visivel(
                textos=("Gerar Relatório", "Gerar Relatorio"),
                preferir_controle=True
            )

            if botao_localizado is not None:
                _pagina_botao, botao = botao_localizado

                if self._acionar_e_confirmar(
                    elemento=botao,
                    confirmacao=self._formulario_relatorio_esta_aberto,
                    cancelado=cancelado,
                    permitir_clique_duplo=False
                ):
                    return

            # Alguns ambientes do GAL tambem aceitam abrir a linha com
            # clique duplo. Mantem-se como recuperacao, sempre confirmada
            # pelo formulario, nunca apenas pela selecao azul.
            try:
                item.dblclick(force=True, timeout=2_000)

                if self._aguardar_condicao(
                    condicao=self._formulario_relatorio_esta_aberto,
                    tempo_limite_segundos=(
                        self.TEMPO_CONFIRMACAO_ACAO_SEGUNDOS
                    ),
                    cancelado=cancelado
                ):
                    return
            except Exception as erro:
                ultima_falha = erro

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        detalhe = (
            f" Detalhe: {ultima_falha}"
            if ultima_falha is not None
            else ""
        )
        raise RuntimeError(
            "O relatório por Exame foi selecionado, mas o botão "
            "'Gerar Relatório' não abriu o formulário do GAL."
            f"{detalhe}"
        )

    def _acionar_e_confirmar(
        self,
        elemento: Locator,
        confirmacao: Callable[[], bool],
        cancelado: Callable[[], bool] | None,
        permitir_clique_duplo: bool
    ) -> bool:
        try:
            elemento.scroll_into_view_if_needed()
        except Exception:
            pass

        estrategias: list[Callable[[], object]] = [
            lambda: elemento.click(timeout=2_000),
            lambda: elemento.click(force=True, timeout=2_000),
            lambda: elemento.evaluate(
                """
                (elemento) => {
                    const controle = elemento.closest(
                        "button, a, input, [onclick]"
                    ) || elemento;
                    controle.click();
                }
                """
            )
        ]

        if permitir_clique_duplo:
            estrategias.append(
                lambda: elemento.dblclick(force=True, timeout=2_000)
            )

        for acao in estrategias:
            self._verificar_cancelamento(cancelado)

            try:
                acao()
            except Exception:
                continue

            if self._aguardar_condicao(
                condicao=confirmacao,
                tempo_limite_segundos=(
                    self.TEMPO_CONFIRMACAO_ACAO_SEGUNDOS
                ),
                cancelado=cancelado
            ):
                return True

        return False

    def _aguardar_formulario_relatorio(
        self,
        cancelado: Callable[[], bool] | None
    ):
        if self._aguardar_condicao(
            condicao=self._formulario_relatorio_esta_aberto,
            tempo_limite_segundos=30,
            cancelado=cancelado
        ):
            return

        raise RuntimeError(
            "O formulário do Relatório Epidemiológico por Exame "
            "não carregou no GAL."
        )

    def _formulario_relatorio_esta_aberto(self) -> bool:
        grupos = (
            ("Campos",),
            ("Consultar período", "Consultar periodo"),
            ("Exame",),
            ("Método", "Metodo")
        )
        encontrados = sum(
            self._texto_visivel(textos)
            for textos in grupos
        )
        return encontrados >= 3

    def _configurar_relatorio(
        self,
        data_inicio: date,
        data_fim: date,
        cancelado: Callable[[], bool] | None
    ):
        # O criterio vem primeiro porque o GAL pode reconstruir os campos
        # de data quando ``Consultar periodo`` e alterado. Confirmamos a
        # escolha e so depois relocalizamos e preenchemos os demais campos.
        self._selecionar_valor(
            rotulos=("Consultar período", "Consultar periodo"),
            valor=self.PERIODO,
            cancelado=cancelado
        )
        self._preencher_associado(
            rotulos=("Campos",),
            valor=self.CAMPOS_RELATORIO,
            cancelado=cancelado,
            aceitar_textarea=True
        )
        self._preencher_associado(
            rotulos=("Início", "Inicio", "Data inicial"),
            valor=data_inicio.strftime("%d/%m/%Y"),
            cancelado=cancelado
        )
        self._preencher_associado(
            rotulos=("Fim", "Data final"),
            valor=data_fim.strftime("%d/%m/%Y"),
            cancelado=cancelado
        )
        self._selecionar_linha_exame_metodo(cancelado=cancelado)

    def _selecionar_linha_exame_metodo(
        self,
        cancelado: Callable[[], bool] | None
    ):
        """
        Seleciona uma unica linha contendo o exame e o metodo esperados.

        No GAL, ``Exame`` e ``Metodo`` sao colunas da mesma grade. Depois
        que a linha fica selecionada, a proxima acao deve ser ``Gerar``;
        nao existe um segundo controle de metodo a ser aberto.
        """

        limite = monotonic() + 20

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            for _pagina, quadro in self.navegador.quadros_ativos():
                localizado = self._linha_exame_metodo(quadro)

                if localizado is None:
                    continue

                linha, alvo_clique = localizado

                if self._linha_grade_selecionada(linha):
                    return

                try:
                    alvo_clique.scroll_into_view_if_needed()
                    alvo_clique.click(force=True, timeout=1_000)
                except Exception:
                    try:
                        linha.click(force=True, timeout=1_000)
                    except Exception:
                        continue

                if self._aguardar_condicao(
                    condicao=lambda l=linha: (
                        self._linha_grade_selecionada(l)
                    ),
                    tempo_limite_segundos=1.2,
                    cancelado=cancelado
                ):
                    return

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        raise RuntimeError(
            "A linha 'Pesquisa de Arbovírus (ZDC) — RT-PCR em tempo "
            "real' não foi selecionada no GAL."
        )

    def _linha_exame_metodo(
        self,
        quadro: Page | Frame
    ) -> tuple[Locator, Locator] | None:
        exame_esperado = self._normalizar(self.EXAME)
        metodo_esperado = self._normalizar(self.METODO)

        for exato in (True, False):
            try:
                candidatos = quadro.get_by_text(self.EXAME, exact=exato)
                quantidade = min(candidatos.count(), 30)
            except Exception:
                continue

            for indice in range(quantidade):
                try:
                    exame = candidatos.nth(indice)

                    if not exame.is_visible():
                        continue

                    linhas = exame.locator(
                        "xpath=ancestor::*["
                        "contains(concat(' ', normalize-space(@class), "
                        "' '), ' x-grid3-row ')][1]"
                    )

                    if not linhas.count():
                        linhas = exame.locator(
                            "xpath=ancestor::tr[1]"
                        )

                    if not linhas.count():
                        continue

                    linha = linhas.first
                    texto = self._normalizar(linha.inner_text(timeout=500))

                    if (
                        exame_esperado in texto
                        and metodo_esperado in texto
                    ):
                        return linha, exame
                except Exception:
                    continue

        return None

    def _linha_grade_selecionada(self, linha: Locator) -> bool:
        try:
            classe = self._normalizar(
                linha.get_attribute("class") or ""
            )
            aria = self._normalizar(
                linha.get_attribute("aria-selected") or ""
            )

            return (
                "x-grid3-row-selected" in classe
                or "x-item-selected" in classe
                or "x-grid-item-selected" in classe
                or aria == "true"
            )
        except Exception:
            return False

    def _preencher_associado(
        self,
        rotulos: tuple[str, ...],
        valor: str,
        cancelado: Callable[[], bool] | None,
        aceitar_textarea: bool = False
    ):
        limite = monotonic() + 20

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            for _pagina, quadro in self.navegador.quadros_ativos():
                campo = self._campo_associado(
                    quadro=quadro,
                    rotulos=rotulos,
                    aceitar_textarea=aceitar_textarea
                )

                if campo is None:
                    continue

                try:
                    campo.click(force=True)
                    campo.fill(valor)
                    return
                except Exception:
                    continue

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        raise RuntimeError(
            f"O campo '{rotulos[0]}' não foi localizado no GAL."
        )

    def _campo_associado(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...],
        aceitar_textarea: bool
    ) -> Locator | None:
        for rotulo in rotulos:
            try:
                candidatos = quadro.get_by_label(
                    rotulo,
                    exact=False
                )

                for indice in range(min(candidatos.count(), 5)):
                    candidato = candidatos.nth(indice)

                    if candidato.is_visible():
                        return candidato
            except Exception:
                pass

        seletores = "input, textarea" if aceitar_textarea else "input"
        palavras = {
            self._normalizar(rotulo)
            for rotulo in rotulos
        }

        try:
            candidatos = quadro.locator(seletores)

            for indice in range(min(candidatos.count(), 80)):
                candidato = candidatos.nth(indice)

                if not candidato.is_visible():
                    continue

                tipo = (candidato.get_attribute("type") or "").casefold()

                if tipo in {"hidden", "radio", "checkbox", "button"}:
                    continue

                atributos = " ".join(
                    candidato.get_attribute(nome) or ""
                    for nome in (
                        "id",
                        "name",
                        "placeholder",
                        "aria-label",
                        "title"
                    )
                )
                atributos = self._normalizar(atributos)

                if any(palavra in atributos for palavra in palavras):
                    return candidato
        except Exception:
            pass

        for rotulo in rotulos:
            try:
                label = quadro.get_by_text(rotulo, exact=False).first
                seguinte = label.locator(
                    "xpath=following::textarea[1]"
                    if aceitar_textarea
                    else "xpath=following::input[1]"
                )

                if seguinte.count() and seguinte.is_visible():
                    return seguinte
            except Exception:
                continue

        return None

    def _selecionar_valor(
        self,
        rotulos: tuple[str, ...],
        valor: str,
        cancelado: Callable[[], bool] | None
    ):
        limite = monotonic() + 20

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            for _pagina, quadro in self.navegador.quadros_ativos():
                if self._valor_esta_selecionado(
                    quadro=quadro,
                    rotulos=rotulos,
                    valor=valor
                ):
                    return

                # Primeiro aciona controles nativos, inclusive selects
                # escondidos pelo ExtJS e grupos de radio antigos. A busca
                # e ancorada no rotulo; so usa a opcao sem rotulo quando ela
                # existe em um unico controle no quadro.
                if self._selecionar_controle_nativo(
                    quadro=quadro,
                    rotulos=rotulos,
                    valor=valor
                ) and self._aguardar_condicao(
                    condicao=lambda q=quadro: (
                        self._valor_esta_selecionado(
                            quadro=q,
                            rotulos=rotulos,
                            valor=valor
                        )
                    ),
                    tempo_limite_segundos=(
                        self.TEMPO_CONFIRMACAO_ACAO_SEGUNDOS
                    ),
                    cancelado=cancelado
                ):
                    return

                if self._selecionar_controle_visual(
                    quadro=quadro,
                    rotulos=rotulos,
                    valor=valor,
                    cancelado=cancelado
                ):
                    return

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        raise RuntimeError(
            f"A opção '{valor}' não foi selecionada no campo "
            f"'{rotulos[0]}' do GAL."
        )

    def _selecionar_controle_nativo(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...],
        valor: str
    ) -> bool:
        """Seleciona ``select`` ou ``radio`` associado ao rotulo."""
        try:
            return bool(
                quadro.evaluate(
                    self._script_controle_nativo(acionar=True),
                    {
                        "rotulos": list(rotulos),
                        "valor": valor
                    }
                )
            )
        except Exception:
            return False

    def _valor_esta_selecionado(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...],
        valor: str
    ) -> bool:
        try:
            if quadro.evaluate(
                self._script_controle_nativo(acionar=False),
                {
                    "rotulos": list(rotulos),
                    "valor": valor
                }
            ):
                return True
        except Exception:
            pass

        alvo = self._normalizar(valor)

        for controle in self._controles_associados(quadro, rotulos):
            try:
                valor_atual = self._normalizar(
                    controle.input_value(timeout=500)
                )

                if valor_atual == alvo or alvo in valor_atual:
                    return True
            except Exception:
                continue

        return False

    def _selecionar_controle_visual(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...],
        valor: str,
        cancelado: Callable[[], bool] | None
    ) -> bool:
        """Abre combos ExtJS e clica somente em uma opcao visivel."""

        controles = self._controles_associados(quadro, rotulos)

        # Em grupos de radio, a opcao ja fica visivel e nao exige que um
        # campo seja aberto antes. Tentamos esse caminho primeiro.
        if self._clicar_opcao_visivel(
            quadro=quadro,
            rotulos=rotulos,
            valor=valor,
            cancelado=cancelado
        ):
            return True

        for controle in controles:
            self._verificar_cancelamento(cancelado)

            try:
                tipo = (controle.get_attribute("type") or "").casefold()

                if tipo in {"radio", "checkbox", "hidden"}:
                    continue

                controle.scroll_into_view_if_needed()
                controle.click(force=True, timeout=1_500)
            except Exception:
                continue

            if self._clicar_opcao_visivel(
                quadro=quadro,
                rotulos=rotulos,
                valor=valor,
                cancelado=cancelado
            ):
                return True

            for gatilho in self._gatilhos_controle(controle):
                try:
                    gatilho.click(force=True, timeout=1_500)
                except Exception:
                    continue

                if self._clicar_opcao_visivel(
                    quadro=quadro,
                    rotulos=rotulos,
                    valor=valor,
                    cancelado=cancelado
                ):
                    return True

        return False

    def _clicar_opcao_visivel(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...],
        valor: str,
        cancelado: Callable[[], bool] | None
    ) -> bool:
        alvo = self._normalizar(valor)

        for exato in (True, False):
            try:
                candidatos = quadro.get_by_text(valor, exact=exato)
                quantidade = min(candidatos.count(), 30)
            except Exception:
                continue

            for indice in range(quantidade):
                self._verificar_cancelamento(cancelado)
                candidato = candidatos.nth(indice)

                try:
                    if not candidato.is_visible():
                        continue

                    texto = self._normalizar(
                        candidato.inner_text(timeout=500) or ""
                    )

                    if texto != alvo and alvo not in texto:
                        continue

                    candidato.scroll_into_view_if_needed()
                    candidato.click(force=True, timeout=1_500)
                except Exception:
                    continue

                if self._aguardar_condicao(
                    condicao=lambda q=quadro: (
                        self._valor_esta_selecionado(
                            quadro=q,
                            rotulos=rotulos,
                            valor=valor
                        )
                    ),
                    tempo_limite_segundos=(
                        self.TEMPO_CONFIRMACAO_ACAO_SEGUNDOS
                    ),
                    cancelado=cancelado
                ):
                    return True

        return False

    def _controles_associados(
        self,
        quadro: Page | Frame,
        rotulos: tuple[str, ...]
    ) -> list[Locator]:
        controles: list[Locator] = []

        for rotulo in rotulos:
            try:
                candidatos = quadro.get_by_label(rotulo, exact=False)

                for indice in range(min(candidatos.count(), 12)):
                    candidato = candidatos.nth(indice)

                    if candidato.is_visible():
                        controles.append(candidato)
            except Exception:
                pass

            try:
                labels = quadro.get_by_text(rotulo, exact=False)
                quantidade = min(labels.count(), 12)
            except Exception:
                continue

            for indice in range(quantidade):
                try:
                    label = labels.nth(indice)

                    if not label.is_visible():
                        continue

                    seletores = (
                        "xpath=ancestor::tr[1]//*[self::select or "
                        "self::input or @role='combobox']",
                        "xpath=ancestor::*[contains(@class, "
                        "'x-form-item')][1]//*[self::select or "
                        "self::input or @role='combobox']",
                        "xpath=following::*[self::select or self::input "
                        "or @role='combobox'][1]"
                    )

                    for seletor in seletores:
                        encontrados = label.locator(seletor)

                        for posicao in range(
                            min(encontrados.count(), 12)
                        ):
                            controle = encontrados.nth(posicao)

                            if controle.is_visible():
                                controles.append(controle)
                except Exception:
                    continue

        return controles

    def _gatilhos_controle(self, controle: Locator) -> list[Locator]:
        gatilhos: list[Locator] = []
        seletores = (
            "xpath=following-sibling::*[contains(@class, "
            "'x-form-trigger')]",
            "xpath=ancestor::*[contains(@class, "
            "'x-form-field-wrap')][1]//*[contains(@class, "
            "'x-form-trigger')]",
            "xpath=ancestor::td[1]//*[contains(@class, "
            "'x-form-trigger')]"
        )

        for seletor in seletores:
            try:
                candidatos = controle.locator(seletor)

                for indice in range(min(candidatos.count(), 6)):
                    candidato = candidatos.nth(indice)

                    if candidato.is_visible():
                        gatilhos.append(candidato)
            except Exception:
                continue

        return gatilhos

    def _script_controle_nativo(self, acionar: bool) -> str:
        acionar_js = "true" if acionar else "false"

        return f"""
            (dados) => {{
                const acionar = {acionar_js};
                const normalizar = (texto) => (texto || "")
                    .normalize("NFD")
                    .replace(/[\\u0300-\\u036f]/g, "")
                    .toLocaleLowerCase("pt-BR")
                    .replace(/\\s+/g, " ")
                    .trim();
                const rotulos = dados.rotulos.map(normalizar);
                const alvo = normalizar(dados.valor);
                const correspondeRotulo = (texto) => {{
                    const atual = normalizar(texto);
                    return rotulos.some(
                        (rotulo) => atual.includes(rotulo)
                    );
                }};
                const textoContexto = (controle) => {{
                    const partes = [
                        controle.id,
                        controle.name,
                        controle.getAttribute("aria-label"),
                        controle.getAttribute("title")
                    ];

                    if (controle.labels) {{
                        for (const label of controle.labels) {{
                            partes.push(label.textContent);
                        }}
                    }}

                    const recipiente = controle.closest(
                        "tr, fieldset, .x-form-item, .form-group"
                    ) || controle.parentElement;
                    partes.push(recipiente && recipiente.textContent);
                    return partes.filter(Boolean).join(" ");
                }};
                const correspondeOpcao = (texto) => {{
                    const atual = normalizar(texto);
                    return atual === alvo || atual.includes(alvo);
                }};

                const selects = Array.from(
                    document.querySelectorAll("select")
                ).map((controle) => {{
                    const opcoes = Array.from(controle.options || []);
                    const indice = opcoes.findIndex(
                        (opcao) => correspondeOpcao(
                            opcao.textContent || opcao.innerText
                        )
                    );
                    return {{
                        controle,
                        opcoes,
                        indice,
                        associado: correspondeRotulo(
                            textoContexto(controle)
                        )
                    }};
                }}).filter((item) => item.indice >= 0);

                const selectsAssociados = selects.filter(
                    (item) => item.associado
                );
                const candidatosSelect = selectsAssociados.length
                    ? selectsAssociados
                    : (selects.length === 1 ? selects : []);

                for (const item of candidatosSelect) {{
                    if (item.controle.selectedIndex === item.indice) {{
                        return true;
                    }}

                    if (!acionar) {{
                        continue;
                    }}

                    item.controle.selectedIndex = item.indice;
                    item.opcoes[item.indice].selected = true;
                    item.controle.dispatchEvent(
                        new Event("input", {{bubbles: true}})
                    );
                    item.controle.dispatchEvent(
                        new Event("change", {{bubbles: true}})
                    );

                    if (item.controle.selectedIndex === item.indice) {{
                        return true;
                    }}
                }}

                const radios = Array.from(document.querySelectorAll(
                    'input[type="radio"]'
                )).map((controle) => {{
                    const partesOpcao = [
                        controle.value,
                        controle.getAttribute("aria-label"),
                        controle.getAttribute("title")
                    ];

                    if (controle.labels) {{
                        for (const label of controle.labels) {{
                            partesOpcao.push(label.textContent);
                        }}
                    }}

                    partesOpcao.push(
                        controle.parentElement
                        && controle.parentElement.textContent
                    );
                    return {{
                        controle,
                        opcaoCorreta: correspondeOpcao(
                            partesOpcao.filter(Boolean).join(" ")
                        ),
                        associado: correspondeRotulo(
                            textoContexto(controle)
                        )
                    }};
                }}).filter((item) => item.opcaoCorreta);

                const radiosAssociados = radios.filter(
                    (item) => item.associado
                );
                const candidatosRadio = radiosAssociados.length
                    ? radiosAssociados
                    : (radios.length === 1 ? radios : []);

                for (const item of candidatosRadio) {{
                    if (item.controle.checked) {{
                        return true;
                    }}

                    if (!acionar) {{
                        continue;
                    }}

                    item.controle.click();

                    if (!item.controle.checked) {{
                        item.controle.checked = true;
                        item.controle.dispatchEvent(
                            new Event("input", {{bubbles: true}})
                        );
                        item.controle.dispatchEvent(
                            new Event("change", {{bubbles: true}})
                        );
                    }}

                    if (item.controle.checked) {{
                        return true;
                    }}
                }}

                const campos = Array.from(document.querySelectorAll(
                    'input:not([type="radio"]):not([type="hidden"]), '
                    + '[role="combobox"]'
                ));

                for (const campo of campos) {{
                    if (!correspondeRotulo(textoContexto(campo))) {{
                        continue;
                    }}

                    const atual = normalizar(
                        campo.value
                        || campo.getAttribute("aria-valuetext")
                        || campo.textContent
                    );

                    if (atual === alvo || atual.includes(alvo)) {{
                        return true;
                    }}
                }}

                const marcados = document.querySelectorAll(
                    '[aria-selected="true"], [aria-checked="true"], '
                    + '.x-combo-selected, .x-boundlist-selected, '
                    + '.x-item-selected, .x-form-radio-checked'
                );

                for (const marcado of marcados) {{
                    if (correspondeOpcao(marcado.textContent)) {{
                        return true;
                    }}
                }}

                return false;
            }}
        """

    def _localizar_texto(
        self,
        textos: tuple[str, ...],
        tempo_limite_segundos: int,
        cancelado: Callable[[], bool] | None,
        preferir_controle: bool = False
    ) -> tuple[Page, Locator]:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            localizado = self._procurar_texto_visivel(
                textos=textos,
                preferir_controle=preferir_controle
            )

            if localizado is not None:
                return localizado

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        raise RuntimeError(
            f"O controle '{textos[0]}' não foi localizado no GAL."
        )

    def _procurar_texto_visivel(
        self,
        textos: tuple[str, ...],
        preferir_controle: bool
    ) -> tuple[Page, Locator] | None:
        """Executa uma busca imediata em paginas e frames do GAL."""

        for pagina, quadro in self.navegador.quadros_ativos():
            for texto in textos:
                candidatos: list[Locator] = []

                if preferir_controle:
                    padrao = re.compile(
                        rf"^\s*{re.escape(texto)}\s*$",
                        re.IGNORECASE
                    )

                    for papel in ("button", "link"):
                        try:
                            candidatos.append(
                                quadro.get_by_role(
                                    papel,
                                    name=padrao
                                )
                            )
                        except Exception:
                            pass

                candidatos.extend((
                    quadro.get_by_text(texto, exact=True),
                    quadro.get_by_text(texto, exact=False)
                ))

                for grupo in candidatos:
                    try:
                        quantidade = min(grupo.count(), 12)

                        for indice in range(quantidade):
                            candidato = grupo.nth(indice)

                            if candidato.is_visible():
                                return pagina, candidato
                    except Exception:
                        continue

        return None

    def _aguardar_texto_visivel(
        self,
        textos: tuple[str, ...],
        tempo_limite_segundos: int,
        cancelado: Callable[[], bool] | None
    ) -> bool:
        return self._aguardar_condicao(
            condicao=lambda: self._texto_visivel(textos),
            tempo_limite_segundos=tempo_limite_segundos,
            cancelado=cancelado
        )

    def _aguardar_condicao(
        self,
        condicao: Callable[[], bool],
        tempo_limite_segundos: float,
        cancelado: Callable[[], bool] | None
    ) -> bool:
        limite = monotonic() + tempo_limite_segundos

        while monotonic() < limite:
            self._verificar_cancelamento(cancelado)

            try:
                if condicao():
                    return True
            except Exception:
                pass

            self._esperar(self.INTERVALO_VERIFICACAO_MS)

        try:
            return bool(condicao())
        except Exception:
            return False

    def _texto_visivel(self, textos: tuple[str, ...]) -> bool:
        for _pagina, quadro in self.navegador.quadros_ativos():
            for texto in textos:
                try:
                    candidatos = quadro.get_by_text(
                        texto,
                        exact=False
                    )

                    for indice in range(min(candidatos.count(), 12)):
                        if candidatos.nth(indice).is_visible():
                            return True
                except Exception:
                    continue

        return False

    def _esperar(self, milissegundos: int):
        paginas = self.navegador.paginas_ativas()

        if not paginas:
            raise RuntimeError("A janela do GAL foi fechada.")

        paginas[-1].wait_for_timeout(milissegundos)

    def _verificar_cancelamento(
        self,
        cancelado: Callable[[], bool] | None
    ):
        if cancelado is not None and cancelado():
            raise RuntimeError("A atualização do GAL foi cancelada.")

    def _normalizar(self, texto: str) -> str:
        sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )
        return " ".join(sem_acentos.casefold().split())

    def _informar(
        self,
        callback: Callable[[str], None] | None,
        mensagem: str
    ):
        if callback is not None:
            callback(mensagem)
