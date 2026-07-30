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
            "Preparando a solicitação de DENGUE..."
        )

        preparacao = (
            exportacao.preparar_primeira_exportacao()
        )

        print()
        print("Formulário preparado.")
        print(
            "Período:",
            preparacao["periodo"]
        )
        print(
            "Data Inicial:",
            preparacao["data_inicial"]
        )
        print(
            "Data Final:",
            preparacao["data_final"]
        )
        print(
            "Notificação ou Residência:",
            preparacao["localizacao"]
        )
        print(
            "Checkbox marcado:",
            preparacao["checkpoint_marcado"]
        )

        print()
        print(
            "ATENÇÃO: o próximo passo criará uma solicitação "
            "REAL de exportação de DENGUE no SINAN."
        )
        print(
            "O script não criará a solicitação de "
            "Chikungunya nesta execução."
        )

        confirmacao = input(
            "\nDigite SOLICITAR para continuar: "
        ).strip()

        if confirmacao != "SOLICITAR":
            print()
            print(
                "Solicitação cancelada. "
                "Nenhuma exportação foi criada."
            )
            return

        print()
        print(
            "Enviando a solicitação de DENGUE..."
        )

        resultado = (
            exportacao.solicitar_exportacao_dengue()
        )

        print()
        print("Solicitação criada com sucesso.")
        print(
            "Agravo:",
            resultado["agravo"]
        )
        print(
            "Número da solicitação:",
            resultado["numero_solicitacao"]
        )
        print(
            "Solicitar acionado:",
            resultado["solicitar_acionado"]
        )
        print(
            "Solicitação confirmada:",
            resultado["solicitacao_confirmada"]
        )
        print(
            "Dados de pacientes lidos:",
            resultado["dados_de_pacientes_lidos"]
        )

        print()
        print(
            "Confira visualmente se o número exibido "
            "no SINAN é o mesmo informado acima."
        )
        print(
            "A automação parou antes de alterar o Agravo "
            "para FEBRE DE CHIKUNGUNYA."
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