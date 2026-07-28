from app.automation.sinan.navegador_sinan import (
    NavegadorSinan
)


def main():
    navegador = NavegadorSinan()

    try:
        print("Abrindo o SINAN...")
        navegador.abrir()

        print()
        print("Faça o login manualmente no navegador.")
        print("O programa não registra usuário ou senha.")
        print("Tempo disponível: 10 minutos.")
        print()

        navegador.aguardar_login_manual(
            tempo_limite_segundos=600
        )

        print()
        print("Login detectado com sucesso.")
        print(
            "Nenhuma credencial ou sessão foi salva."
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
            "Não foi possível concluir o teste."
        )
        print(f"Detalhes técnicos: {erro}")

    finally:
        navegador.fechar()
        print("Navegador fechado.")


if __name__ == "__main__":
    main()