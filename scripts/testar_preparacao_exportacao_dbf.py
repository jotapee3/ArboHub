from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)


def main():
    navegador = NavegadorSinan()

    try:
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
            "Solicitar Exportação de Base de Dados em DBF..."
        )

        exportacao.abrir_solicitacao_exportacao_dbf()

        print()
        print(
            "Preenchendo Período, datas e localização; "
            "depois localizando o checkbox..."
        )

        resultado = (
            exportacao.preparar_primeira_exportacao()
        )

        print()
        print("Primeira etapa concluída.")
        print(
            "Período:",
            resultado["periodo"]
        )
        print(
            "Data Inicial:",
            resultado["data_inicial"]
        )
        print(
            "Data Final:",
            resultado["data_final"]
        )
        print(
            "Notificação ou Residência:",
            resultado["localizacao"]
        )
        print(
            "Checkpoint:",
            resultado["checkpoint"]
        )
        print(
            "Checkbox encontrado:",
            resultado["checkpoint_encontrado"]
        )
        print(
            "Checkbox marcado:",
            resultado["checkpoint_marcado"]
        )
        print(
            "Agravo alterado:",
            resultado["agravo_alterado"]
        )
        print(
            "Solicitar acionado:",
            resultado["solicitar_acionado"]
        )
        print(
            "Dados de pacientes lidos:",
            resultado["dados_de_pacientes_lidos"]
        )

        print()
        print(
            "Confira visualmente se o Agravo permanece DENGUE."
        )
        print(
            "A automação marcou o checkbox e parou antes "
            "de clicar em Solicitar."
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