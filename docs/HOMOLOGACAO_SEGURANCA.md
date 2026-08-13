# Homologação de segurança e distribuição

Este documento organiza a revisão necessária antes de instalar o
ArboHub em outro computador ou ampliar seu uso. Ele não substitui a
avaliação da equipe institucional de tecnologia e segurança.

## Identificação da revisão

| Item | Valor |
| --- | --- |
| Versão | ArboHub v0.6 |
| Commit recebido | `658a805` |
| SHA-256 do código-fonte recebido | `E32C4A7923BDAF82F7816A0F9301B4A3EBE6EB47A8C076A7757C80EADC533D48` |
| Formato pretendido | protótipo `onedir` para Windows x64 |
| Assinatura atual | ausente |
| Sincronização entre computadores | não implementada |

O pacote de código recebido não continha banco SQLite, DBF, CSV, ZIP
operacional, credenciais, logs, rastros ou capturas dos portais.

## Resultado da revisão do código

### Controles confirmados

- credencial do SINAN armazenada pelo Gerenciador de Credenciais do
  Windows, sem gravação no JSON ou SQLite;
- banco e configurações fora da pasta do programa, em
  `%LOCALAPPDATA%\ArboHub`;
- migração do banco legado por cópia validada, sem apagar a origem;
- conexões SQLite fechadas explicitamente;
- consultas marcadas como somente leitura abertas com `mode=ro`;
- autenticação automática do SINAN permitida somente no endereço HTTPS
  e hostname oficial;
- downloads realizados em áreas temporárias e publicados nos destinos
  por substituição controlada;
- extrações de ZIP usam nomes de destino controlados, sem confiar no
  caminho interno do arquivo;
- e-mail de suporte preparado somente para o contato institucional
  configurado, sem incluir automaticamente a conta do Windows;
- artefatos sensíveis, arquivos compactados e chaves privadas excluídos
  pelo `.gitignore`;
- compactação UPX desativada no build;
- execução normal sem solicitação de privilégios administrativos.

### Bloqueios antes da distribuição

1. **Certificado do GAL:** o contexto automatizado ainda utiliza
   `ignore_https_errors=True`. A validação do hostname não substitui a
   validação do certificado. A infraestrutura institucional deve
   corrigir/confiar na cadeia do portal ou aprovar formalmente uma
   exceção documentada antes do uso ampliado.
2. **Assinatura digital:** o executável atual está `NotSigned`. Não se
   deve contornar o antivírus. A TI deve definir assinatura institucional
   ou implantação controlada em dispositivos gerenciados.
3. **Antivírus:** houve bloqueio do protótipo pelo Trend Micro como
   programa recém-encontrado. O evento deve acompanhar a solicitação de
   análise; não se deve desativar a proteção, criar exceção pessoal ou
   escolher “Permitir” sem autorização.
4. **Correspondência fonte/binário:** o executável existente foi gerado
   antes da conclusão desta revisão. Um novo build deve ser criado a
   partir do commit aprovado; hashes anteriores não identificam o novo
   artefato.
5. **Dependências:** ainda é necessário executar auditoria de
   vulnerabilidades e gerar o SBOM no dia do build aprovado.
6. **Sistema operacional:** o destino deve ser Windows 11 x64 ou Windows
   Server compatível e ainda suportado. O Playwright atual não declara
   Windows 10 como plataforma suportada.

## Dados e acessos

| Origem/destino | Conteúdo | Regra |
| --- | --- | --- |
| SINAN | autenticação, consultas e exportações autorizadas | conta individual e acesso institucional |
| GAL | login manual, CAPTCHA e relatório semanal | supervisão humana obrigatória |
| `%LOCALAPPDATA%\ArboHub` | configurações, metadados operacionais e temporários | perfil local do usuário |
| Gerenciador de Credenciais | usuário e senha do SINAN | consentimento explícito para salvar |
| Pastas configuradas | DBF, CSV e ZIP validados | somente destinos aprovados pelo setor |
| E-mail institucional | solicitação de suporte revisada pelo operador | nenhum envio automático |

O SQLite não deve receber conteúdo clínico ou linhas de pacientes. A
versão atual não envia o banco, arquivos ou progresso para outro
computador.

## Auditoria das dependências

Faça a auditoria em um ambiente separado, com acesso de rede autorizado:

```powershell
py -3.14 -m venv .venv-audit
$ArboHubPythonAudit = ".\.venv-audit\Scripts\python.exe"

& $ArboHubPythonAudit -m pip install pip-audit==2.10.1
& $ArboHubPythonAudit -m pip_audit `
    --strict `
    --no-deps `
    -r requirements-build.txt

& $ArboHubPythonAudit -m pip_audit `
    --strict `
    --no-deps `
    -r requirements-build.txt `
    --format cyclonedx-json `
    --output dist\ArboHub-v0.6-sbom.cdx.json
```

Não use `--fix` automaticamente. Qualquer atualização deve passar por
ambiente limpo, testes, novo build e validação operacional autorizada.

## Evidências para a TI

Entregar em conjunto:

- este documento;
- commit e SHA-256 do código revisado;
- resultado dos testes automatizados;
- resultado do `pip-audit` e SBOM;
- log completo do build;
- SHA-256 do ZIP final e do `ArboHub.exe`;
- saída de `Get-AuthenticodeSignature`;
- captura e identificação do evento do Trend Micro;
- lista dos dois domínios acessados e dos diretórios gravados;
- responsável pela instalação, suporte, atualização e revogação.

Não envie o executável a serviços públicos de análise de arquivos sem
autorização institucional: o pacote pode revelar estrutura interna,
dependências e endereços operacionais.

## Teste controlado após aprovação

1. usar um computador institucional de teste, sem dados reais;
2. conferir o hash recebido antes de extrair;
3. instalar/extrair em caminho estável aprovado, não em `%TEMP%`;
4. executar sem privilégios administrativos;
5. validar primeiro `ArboHub.exe --verificar-distribuicao`;
6. abrir a interface e revisar os caminhos em **Configurações**;
7. não salvar credenciais nem executar rotinas reais no primeiro teste;
8. registrar alertas, comportamento, versão do Windows e antivírus;
9. somente depois da aprovação funcional testar os portais com conta
   autorizada e acompanhamento.

## Registro de decisão

| Decisão | Responsável | Data | Evidência |
| --- | --- | --- | --- |
| finalidade e escopo aprovados |  |  |  |
| exceção/correção do certificado GAL |  |  |  |
| dependências e SBOM revisados |  |  |  |
| assinatura ou implantação definida |  |  |  |
| teste em segundo computador aprovado |  |  |  |
| uso operacional autorizado |  |  |  |

## Referências técnicas

- [Requisitos do Playwright para Python](https://playwright.dev/python/docs/intro)
- [Opções oficiais de assinatura de código no Windows](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options)
- [pip-audit](https://pypi.org/project/pip-audit/2.10.1/)
