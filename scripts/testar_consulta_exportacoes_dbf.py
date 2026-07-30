from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


def imprimir_resultado(
    nome: str,
    resultado: dict
):
    print()
    print(nome)
    print(
        "  Número:",
        resultado["numero_solicitacao"]
    )
    print(
        "  Encontrada:",
        resultado["encontrada"]
    )
    print(
        "  Quantidade de registros:",
        resultado["quantidade_registros"] or "não informada"
    )
    print(
        "  Status:",
        resultado["status"]
    )
    print(
        "  Processamento concluído:",
        resultado["processamento_concluido"]
    )
    print(
        "  Link disponível:",
        resultado["link_disponivel"]
    )
    print(
        "  Texto do link:",
        resultado["texto_link"] or "ainda indisponível"
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
                "Execute primeiro a solicitação diária das "
                "duas bases."
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
            "Consultando os dois números uma única vez..."
        )

        resultados = (
            exportacao.consultar_solicitacoes_dbf(
                numero_dengue=numero_dengue,
                numero_chikungunya=numero_chikungunya
            )
        )

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
                ExportacaoDbfService.AGRAVO_CHIKUNGUNYA
            ),
            resultado=resultados["chikungunya"]
        )

        imprimir_resultado(
            "DENGUE",
            resultados["dengue"]
        )
        imprimir_resultado(
            "FEBRE DE CHIKUNGUNYA",
            resultados["chikungunya"]
        )

        ambos_encontrados = (
            resultados["dengue"]["encontrada"]
            and resultados["chikungunya"]["encontrada"]
        )

        ambos_disponiveis = (
            resultados["dengue"]["link_disponivel"]
            and resultados["chikungunya"]["link_disponivel"]
        )

        print()
        print(
            "Ambos os números encontrados:",
            ambos_encontrados
        )
        print(
            "Ambos os links disponíveis:",
            ambos_disponiveis
        )
        print(
            "Downloads iniciados:",
            False
        )
        print(
            "Dados de pacientes lidos:",
            False
        )

        print()
        print(
            "A automação fez somente uma leitura da tabela."
        )
        print(
            "Ela não clicou em Atualizar e não iniciou downloads."
        )

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    except KeyboardInterrupt:
        print()
        print("Teste interrompido pelo usuário.")

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