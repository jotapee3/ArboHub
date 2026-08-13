# Distribuição para Windows

Esta etapa gera um protótipo interno do ArboHub em formato `onedir`.
O computador de destino não precisa possuir Python nem instalar o
Chromium separadamente, mas deve receber a pasta completa da
distribuição.

O protótipo ainda não é um instalador oficial. Ele mantém o console
visível para facilitar o diagnóstico no primeiro teste em outro
computador.

## Conteúdo da distribuição

- `ArboHub.exe`;
- interpretador Python e bibliotecas necessárias;
- temas do CustomTkinter;
- ícones e logos do ArboHub;
- driver do Playwright;
- Chromium compatível com a versão fixada do Playwright.

O banco, as configurações, as credenciais e os arquivos exportados não
são incluídos. Cada usuário continua usando `%LOCALAPPDATA%\ArboHub` e
o Gerenciador de Credenciais do próprio Windows.

## Gerar o protótipo

Execute na raiz do projeto, em um Windows x64:

```powershell
.\scripts\construir_executavel.ps1
```

O script:

1. cria o ambiente isolado `.venv-build`;
2. instala as versões de `requirements-build.txt`;
3. baixa somente o Chromium necessário para uso visível;
4. remove metadados locais que não devem ir para o pacote;
5. gera `dist\ArboHub`;
6. executa uma verificação interna sem abrir a interface;
7. cria `dist\ArboHub-v0.6-windows-x64.zip`;
8. informa o hash SHA-256 do ZIP.

O primeiro build pode demorar e consumir centenas de megabytes. Não
interrompa enquanto houver download, análise ou compactação em curso.

## Validar no computador de build

Após a conclusão:

```powershell
.\dist\ArboHub\ArboHub.exe --verificar-distribuicao
.\dist\ArboHub\ArboHub.exe
```

Confirme a abertura das páginas, os ícones, a rolagem e os diálogos.
Não execute uma rotina real apenas para testar o pacote.

## Validar em outro computador

1. copie apenas o ZIP gerado por um meio institucional autorizado;
2. confira o hash SHA-256 antes de extrair;
3. extraia a pasta completa em um local autorizado;
4. execute primeiro `ArboHub.exe --verificar-distribuicao`;
5. abra o ArboHub sem privilégios administrativos;
6. revise os caminhos em **Configurações**;
7. confirme em **Sobre** o banco localizado em `%LOCALAPPDATA%`;
8. valide SINAN e GAL somente com autorização e acompanhamento.

Não copie somente `ArboHub.exe`: as dependências e o Chromium ficam na
pasta `_internal` ao lado dele.

## Limites deste protótipo

- ainda não possui assinatura digital;
- ainda não possui instalador ou atualizador;
- o console permanece visível;
- a compatibilidade deve ser confirmada no Windows institucional;
- qualquer alerta do antivírus deve ser analisado, nunca contornado;
- nenhuma distribuição ampliada deve ocorrer antes da revisão de
  segurança e da autorização do setor.

Depois dos testes, o próximo ciclo poderá ocultar o console, criar um
instalador assinado e documentar atualização e desinstalação.
