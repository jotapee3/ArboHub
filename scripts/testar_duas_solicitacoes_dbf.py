from app.automation.sinan.exportacao_bases import (
    ExportacaoBasesDbf
)
from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.services.exportacao_dbf_service import (
    ExportacaoDbfService
)


def main():
    navegador = NavegadorSinan()
    registro_service = ExportacaoDbfService()
    lote_id = None

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
        print("Preparando DENGUE...")

        dengue_preparada = (
            exportacao.preparar_primeira_exportacao()
        )

        print()
        print("Formulário de DENGUE preparado.")
        print(
            "Data Inicial:",
            dengue_preparada["data_inicial"]
        )
        print(
            "Data Final:",
            dengue_preparada["data_final"]
        )
        print(
            "Checkbox marcado:",
            dengue_preparada["checkpoint_marcado"]
        )

        print()
        print(
            "ATENÇÃO: esta validação criará duas solicitações "
            "REAIS no SINAN: DENGUE e FEBRE DE CHIKUNGUNYA."
        )

        confirmacao = input(
            "\nDigite SOLICITAR DUAS para continuar: "
        ).strip()

        if confirmacao != "SOLICITAR DUAS":
            print()
            print(
                "Operação cancelada. "
                "Nenhuma solicitação foi criada."
            )
            return

        print()
        print("Solicitando DENGUE...")

        dengue = (
            exportacao.solicitar_exportacao_dengue()
        )

        # O lote é criado somente depois que o número
        # apareceu na tela e foi capturado com sucesso.
        lote_id = registro_service.criar_lote()

        registro_service.salvar_solicitacao(
            lote_id=lote_id,
            agravo=(
                ExportacaoDbfService.AGRAVO_DENGUE
            ),
            numero_solicitacao=(
                dengue["numero_solicitacao"]
            )
        )

        print(
            "Número de DENGUE:",
            dengue["numero_solicitacao"]
        )
        print(
            "Número capturado da tela e salvo automaticamente:",
            True
        )

        print()
        print(
            "Alterando apenas o Agravo para "
            "FEBRE DE CHIKUNGUNYA..."
        )

        chikungunya_preparada = (
            exportacao.preparar_exportacao_chikungunya()
        )

        print()
        print("Formulário de Chikungunya preparado.")
        print(
            "Agravo:",
            chikungunya_preparada["agravo"]
        )
        print(
            "Data Inicial:",
            chikungunya_preparada["data_inicial"]
        )
        print(
            "Data Final:",
            chikungunya_preparada["data_final"]
        )
        print(
            "Localização:",
            chikungunya_preparada["localizacao"]
        )
        print(
            "Checkbox marcado:",
            chikungunya_preparada["checkpoint_marcado"]
        )
        print(
            "Campos mantidos:",
            chikungunya_preparada["campos_mantidos"]
        )

        confirmacao_chiku = input(
            "\nConfira o formulário e digite CHIKUNGUNYA "
            "para criar a segunda solicitação: "
        ).strip()

        if confirmacao_chiku != "CHIKUNGUNYA":
            print()
            print(
                "A solicitação de DENGUE foi criada, mas a "
                "solicitação de Chikungunya foi cancelada."
            )
            return

        print()
        print("Solicitando FEBRE DE CHIKUNGUNYA...")

        chikungunya = (
            exportacao.solicitar_exportacao_chikungunya(
                numero_solicitacao_dengue=(
                    dengue["numero_solicitacao"]
                )
            )
        )

        registro_service.salvar_solicitacao(
            lote_id=lote_id,
            agravo=(
                ExportacaoDbfService.AGRAVO_CHIKUNGUNYA
            ),
            numero_solicitacao=(
                chikungunya["numero_solicitacao"]
            )
        )

        print()
        print("Duas solicitações concluídas e salvas.")
        print(
            "Lote local:",
            lote_id
        )
        print(
            "DENGUE:",
            dengue["numero_solicitacao"]
        )
        print(
            "FEBRE DE CHIKUNGUNYA:",
            chikungunya["numero_solicitacao"]
        )
        print(
            "Números distintos:",
            (
                dengue["numero_solicitacao"]
                != chikungunya["numero_solicitacao"]
            )
        )
        print(
            "Dados de pacientes lidos:",
            False
        )

        print()
        print(
            "A automação parou antes de abrir "
            "'Consultar Exportações DBF'."
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