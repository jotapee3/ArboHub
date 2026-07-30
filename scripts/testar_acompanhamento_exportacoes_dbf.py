from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


def resumir(
    nome: str,
    resultado: dict
) -> str:
    encontrado = (
        "encontrada"
        if resultado["encontrada"]
        else "não encontrada"
    )

    status = (
        resultado["status"]
        or "status ainda não informado"
    )

    link = (
        "link disponível"
        if resultado["link_disponivel"]
        else "link indisponível"
    )

    return (
        f"{nome}: {encontrado}; "
        f"{status}; {link}"
    )


def main():
    navegador = NavegadorSinan()
    registro_service = ExportacaoDbfService()

    try:
        lote = (
            registro_service.obter_lote_completo_do_dia()
        )

        if lote is None:
            raise RuntimeError(
                "Nenhum lote completo de Dengue e "
                "Chikungunya foi encontrado para hoje. "
                "Execute primeiro a solicitação diária "
                "das duas bases."
            )

        numero_dengue = (
            lote["dengue"]["numero_solicitacao"]
        )
        numero_chikungunya = (
            lote["chikungunya"]["numero_solicitacao"]
        )

        print("Lote completo de hoje localizado.")
        print(
            "Data de referência:",
            lote["data_referencia"]
        )
        print(
            "Número de DENGUE:",
            numero_dengue
        )
        print(
            "Número de CHIKUNGUNYA:",
            numero_chikungunya
        )

        print()
        print("Abrindo o SINAN...")
        pagina = navegador.abrir()

        print()
        print("Faça o login manualmente no navegador.")
        print("Nenhuma credencial será registrada.")
        print()

        navegador.aguardar_login_manual(
            tempo_limite_segundos=600
        )

        print("Login detectado com sucesso.")
        print()

        exportacao = ExportacaoBasesDbf(
            pagina
        )

        print(
            "Abrindo Exportação → "
            "Consultar Exportações DBF..."
        )

        exportacao.abrir_consulta_exportacoes_dbf()

        print()
        print(
            "Validando o botão Atualizar com uma "
            "atualização única..."
        )

        exportacao.atualizar_consulta_exportacoes_dbf()

        print("Botão Atualizar validado.")
        print()
        print(
            "Acompanhando as duas solicitações."
        )
        print(
            "Intervalo: 15 segundos. "
            "Tempo limite: 30 minutos."
        )
        print(
            "Use Ctrl+C para interromper o teste."
        )

        def ao_atualizar(
            tentativa: int,
            resultados: dict
        ):
            registro_service.atualizar_resultado_consulta(
                lote_id=lote["lote_id"],
                agravo=(
                    ExportacaoDbfService.AGRAVO_DENGUE
                ),
                resultado=resultados["dengue"]
            )
            registro_service.atualizar_resultado_consulta(
                lote_id=lote["lote_id"],
                agravo=(
                    ExportacaoDbfService
                    .AGRAVO_CHIKUNGUNYA
                ),
                resultado=resultados["chikungunya"]
            )

            print()
            print(f"Consulta {tentativa}")
            print(
                resumir(
                    "DENGUE",
                    resultados["dengue"]
                )
            )
            print(
                resumir(
                    "CHIKUNGUNYA",
                    resultados["chikungunya"]
                )
            )

        resultado_final = (
            exportacao.aguardar_solicitacoes_prontas(
                numero_dengue=numero_dengue,
                numero_chikungunya=(
                    numero_chikungunya
                ),
                intervalo_segundos=15,
                tempo_limite_segundos=1800,
                ao_atualizar=ao_atualizar
            )
        )

        print()
        print("As duas exportações estão disponíveis.")
        print(
            "Tentativas:",
            resultado_final["tentativas"]
        )
        print(
            "Tempo decorrido:",
            resultado_final[
                "tempo_decorrido_segundos"
            ],
            "segundos"
        )
        print(
            "DENGUE:",
            resultado_final["dengue"]["status"],
            "-",
            resultado_final["dengue"]["texto_link"]
        )
        print(
            "CHIKUNGUNYA:",
            resultado_final[
                "chikungunya"
            ]["status"],
            "-",
            resultado_final[
                "chikungunya"
            ]["texto_link"]
        )
        print(
            "Downloads iniciados:",
            resultado_final["downloads_iniciados"]
        )
        print(
            "Dados de pacientes lidos:",
            resultado_final[
                "dados_de_pacientes_lidos"
            ]
        )

        print()
        print(
            "A automação parou antes de clicar "
            "nos links de download."
        )

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    except KeyboardInterrupt:
        print()
        print(
            "Acompanhamento interrompido pelo usuário."
        )

    except Exception as erro:
        print()
        print("Não foi possível concluir o teste.")
        print(f"Detalhes técnicos: {erro}")

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    finally:
        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()