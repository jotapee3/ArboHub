from app.services.arquivos_exportacao_dbf_service import (
    ArquivosExportacaoDbfService
)


def main():
    service = ArquivosExportacaoDbfService()

    try:
        destinos = service.caminhos_pastas_teste()

        print(
            "Esta etapa atualizará somente as pastas de teste."
        )
        print()
        print("DENGUE:")
        print(destinos["dengue"])
        print()
        print("CHIKUNGUNYA:")
        print(destinos["chikungunya"])

        print()
        print(
            "Antes da substituição, os dois DBFs históricos "
            "serão extraídos, validados e copiados para arquivos "
            "temporários no próprio destino."
        )
        print(
            "Se qualquer parte falhar, o ArboHub tentará "
            "restaurar os dois arquivos anteriores."
        )
        print()
        print(
            "A pasta Documents\\SINAN\\Bancos_Atuais "
            "não será alterada."
        )

        confirmacao = input(
            "\nDigite ATUALIZAR TESTES para continuar: "
        ).strip()

        if confirmacao != "ATUALIZAR TESTES":
            print()
            print("Operação cancelada.")
            return

        resultado = (
            service.instalar_dbfs_pastas_teste()
        )

        print()
        print(
            "Pastas de teste atualizadas com sucesso."
        )

        print()
        print("DENGUE")
        print(
            "  Destino:",
            resultado["dengue"]["destino"]
        )
        print(
            "  Nome interno do ZIP:",
            resultado["dengue"]["nome_interno"]
        )
        print(
            "  Prefixo confirmado:",
            resultado["dengue"][
                "prefixo_confirmado"
            ]
        )
        print(
            "  Substituiu arquivo existente:",
            resultado["dengue"][
                "substituiu_existente"
            ]
        )
        print(
            "  Arquivos anteriores removidos:",
            (
                ", ".join(
                    resultado["dengue"][
                        "arquivos_anteriores_removidos"
                    ]
                )
                or "nenhum"
            )
        )
        print(
            "  Tamanho:",
            resultado["dengue"]["tamanho_bytes"],
            "bytes"
        )

        print()
        print("CHIKUNGUNYA")
        print(
            "  Destino:",
            resultado["chikungunya"]["destino"]
        )
        print(
            "  Nome interno do ZIP:",
            resultado[
                "chikungunya"
            ]["nome_interno"]
        )
        print(
            "  Prefixo confirmado:",
            resultado[
                "chikungunya"
            ]["prefixo_confirmado"]
        )
        print(
            "  Substituiu arquivo existente:",
            resultado[
                "chikungunya"
            ]["substituiu_existente"]
        )
        print(
            "  Arquivos anteriores removidos:",
            (
                ", ".join(
                    resultado["chikungunya"][
                        "arquivos_anteriores_removidos"
                    ]
                )
                or "nenhum"
            )
        )
        print(
            "  Tamanho:",
            resultado[
                "chikungunya"
            ]["tamanho_bytes"],
            "bytes"
        )

        print()
        print(
            "Pasta temporária excluída:",
            resultado["pasta_temporaria_excluida"]
        )
        print(
            "Registros internos interpretados:",
            resultado["registros_lidos"]
        )
        print(
            "Bancos_Atuais substituídos:",
            resultado[
                "bancos_atuais_substituidos"
            ]
        )

    except Exception as erro:
        print()
        print(
            "Não foi possível atualizar as pastas de teste."
        )
        print(f"Detalhes técnicos: {erro}")
        print()
        print(
            "Quando possível, os arquivos anteriores foram "
            "restaurados automaticamente."
        )


if __name__ == "__main__":
    main()