from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)
from app.automation.sinan.verificacao_obitos import (
    VerificacaoObitos
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
        print(
            "Abrindo Consulta → Notificação Individual..."
        )

        verificacao = VerificacaoObitos(
            pagina
        )

        verificacao.abrir_notificacao_individual()

        print("Preenchendo período e datas...")

        periodo = (
            verificacao.preencher_periodo_e_datas()
        )

        print(
            "Selecionando Dengue e "
            "Notificação ou Residência..."
        )

        filtros = (
            verificacao.preencher_agravo_e_residencia(
                agravo="Dengue"
            )
        )

        print(
            "Selecionando Evolução e "
            "2 - Óbito por Agravo..."
        )

        criterio = (
            verificacao.preencher_criterio_obito()
        )

        print("Clicando em Adicionar...")

        adicao = (
            verificacao.adicionar_criterio_obito()
        )

        print()
        print("Critério adicionado com sucesso.")
        print(
            "Data inicial:",
            periodo["data_inicial"]
        )
        print(
            "Data final:",
            periodo["data_final"]
        )
        print(
            "Agravo:",
            filtros["agravo"]
        )
        print(
            "Localização:",
            filtros["localizacao"]
        )
        print(
            "Campo:",
            criterio["campo"]
        )
        print(
            "Operador:",
            adicao["operador"]
        )
        print(
            "Critério:",
            criterio["criterio"]
        )
        print(
            "Registros do critério antes:",
            adicao["ocorrencias_antes"]
        )
        print(
            "Registros do critério depois:",
            adicao["ocorrencias_depois"]
        )

        print()
        print(
            "O botão Pesquisar não foi acionado."
        )

        input(
            "\nConfira o critério na lista e pressione "
            "Enter para fechar..."
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