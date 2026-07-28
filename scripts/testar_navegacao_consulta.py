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

        print()
        print(
            "Tela de Notificação Individual detectada "
            "com sucesso."
        )
        print(
            "Nenhum filtro foi preenchido e nenhuma "
            "pesquisa foi realizada."
        )

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    except TimeoutError as erro:
        print()
        print(f"Tempo encerrado: {erro}")

    except KeyboardInterrupt:
        print()
        print("Teste interrompido pelo usuário.")

    except Exception as erro:
        print()
        print(
            "Não foi possível concluir a navegação."
        )
        print(f"Detalhes técnicos: {erro}")

        input(
            "\nPressione Enter para fechar o navegador..."
        )

    finally:
        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()