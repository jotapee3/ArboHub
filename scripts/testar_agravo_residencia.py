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

        print("Selecionando Dengue e Residência...")

        filtros = (
            verificacao.preencher_agravo_e_residencia(
                agravo="Dengue"
            )
        )

        print()
        print("Filtros básicos preenchidos com sucesso.")
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

        print()
        print(
            "Nenhum critério foi adicionado e nenhuma "
            "pesquisa foi realizada."
        )

        input(
            "\nConfira os campos no navegador e pressione "
            "Enter para fechar..."
        )

    except TimeoutError as erro:
        print()
        print(f"Tempo encerrado: {erro}")

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