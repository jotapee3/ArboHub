# Dependências

## Ambiente validado

Em 12 de agosto de 2026, os testes do ArboHub foram executados com:

- Python 3.14.6;
- CustomTkinter 6.0.0;
- Pillow 12.3.0;
- Playwright 1.61.0;
- Watchfiles 1.2.0.

O comando `python -m pip check` informou que não havia requisitos quebrados.

## Arquivos

### `requirements.txt`

Contém apenas as dependências diretas necessárias para executar o aplicativo:

- CustomTkinter;
- Pillow;
- Playwright.

### `requirements-dev.txt`

Inclui `requirements.txt` e adiciona Watchfiles, usado pelo supervisor `dev.py`.

### `requirements.lock.txt`

Registra as versões exatas das dependências diretas e transitivas instaladas no ambiente validado. É o arquivo recomendado para reproduzir o desenvolvimento atual.

### `requirements-build.txt`

Inclui o ambiente validado e fixa as ferramentas usadas para gerar o
protótipo Windows:

- PyInstaller 6.22.0;
- pyinstaller-hooks-contrib 2026.6.

Essas ferramentas são necessárias somente no computador de build e não
fazem parte do uso normal do código-fonte.

Um arquivo fechado por versão reduz alterações inesperadas, mas não fornece, sozinho, verificação criptográfica dos pacotes. A etapa de distribuição deverá avaliar hashes, origem dos artefatos e processo institucional de atualização.

Antes de um build destinado a outro computador, execute também a
auditoria e gere o SBOM conforme
[Homologação de segurança](HOMOLOGACAO_SEGURANCA.md). O resultado é uma
evidência datada: a ausência de alertas hoje não garante ausência de
vulnerabilidades descobertas futuramente.

## Instalação reproduzível

Em um ambiente virtual vazio:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
python -m pip check
python scripts/verificar_ambiente.py
python -m unittest discover -s tests -p "test_*.py" -v
```

O Chromium é gerenciado separadamente pelo Playwright e não aparece no resultado de `pip freeze`.

## Atualizações

Não atualize uma biblioteca isolada diretamente no ambiente de trabalho. Use este processo:

1. crie uma branch específica;
2. crie um ambiente virtual limpo;
3. instale as versões candidatas;
4. execute `pip check`, o verificador e os testes;
5. abra o aplicativo sem iniciar uma rotina real;
6. valide SINAN e GAL em cenário autorizado;
7. atualize os três arquivos de dependência;
8. registre a mudança e o motivo no commit.

Depois de qualquer atualização do Playwright, execute novamente:

```powershell
python -m playwright install chromium
```

## Produção e desenvolvimento

Watchfiles não é necessário para o uso comum do aplicativo; ele serve apenas a `dev.py`. O futuro executável não deve incluir ferramentas de desenvolvimento sem necessidade.

O primeiro protótipo usa PyInstaller 6.22.0 com Python 3.14. A validação
final depende do build no Windows e do teste em um segundo computador.
