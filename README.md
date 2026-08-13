# ArboHub

Aplicação desktop interna para apoiar rotinas de vigilância em saúde no setor de Antropozoonoses. A versão atual é a **v0.6**, com fluxos operacionais para SINAN e GAL.

## Funcionalidades atuais

- painel diário com o estado das rotinas;
- consulta de óbitos de Dengue e Chikungunya no SINAN;
- solicitação, acompanhamento e organização das bases DBF do SINAN;
- atualização semanal do arquivo de sorotipo do GAL;
- histórico operacional local;
- configurações de aparência, caminhos e notificações;
- identificação do responsável pela conta do Windows;
- armazenamento da credencial do SINAN no Gerenciador de Credenciais do Windows.

O ArboHub não é um prontuário e não deve armazenar conteúdo clínico no banco operacional. Os arquivos exportados pelos sistemas oficiais permanecem nos destinos autorizados configurados pelo setor.

## Situação do projeto

O projeto está em estabilização arquitetural. Os fluxos SINAN e GAL estão implementados e a distribuição `onedir` para Windows está em preparação para teste interno. Ainda não existe um instalador oficial.

## Requisitos para desenvolvimento

- Windows 10 ou 11;
- Python 3.14 no ambiente atualmente validado;
- acesso autorizado aos portais SINAN e GAL;
- permissão para os diretórios operacionais configurados;
- dependências listadas em `requirements.txt`;
- navegador Chromium instalado pelo Playwright.

## Preparação do ambiente

No PowerShell, a partir da raiz do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
python scripts/verificar_ambiente.py
```

Para abrir o aplicativo:

```powershell
python main.py
```

Para desenvolvimento com reinicialização automática:

```powershell
python dev.py
```

## Testes

Os testes automatizados atuais verificam o processamento semanal do GAL, a independência dos estados SINAN/GAL e o ciclo de vida e a migração segura do SQLite.

```powershell
python -m compileall -q app tests
python -m unittest discover -s tests -p "test_*.py" -v
```

## Dados locais

| Conteúdo | Local padrão |
| --- | --- |
| Configurações | `%LOCALAPPDATA%\ArboHub\configuracoes.json` |
| Banco operacional ativo | `%LOCALAPPDATA%\ArboHub\dados\arbohub.db` |
| Temporários do SINAN | `%LOCALAPPDATA%\ArboHub\temp\exportacoes` |
| Credencial do SINAN | Gerenciador de Credenciais do Windows, alvo `ArboHub/SINAN` |

Uma instalação antiga pode manter `data\arbohub.db` como cópia de recuperação. Depois da migração, esse arquivo não é o banco ativo.

## Documentação

- [Arquitetura](docs/ARQUITETURA.md)
- [Instalação para desenvolvimento](docs/INSTALACAO_DESENVOLVIMENTO.md)
- [Segurança e dados](docs/SEGURANCA_E_DADOS.md)
- [Backup e recuperação](docs/BACKUP_E_RECUPERACAO.md)
- [Dependências](docs/DEPENDENCIAS.md)
- [Distribuição para Windows](docs/DISTRIBUICAO_WINDOWS.md)
- [Próximas etapas](docs/ROADMAP.md)
- [Scripts auxiliares](scripts/README.md)

## Segurança

Não publique bancos SQLite, DBFs, CSVs, ZIPs exportados, credenciais, configurações pessoais, logs, rastros de navegador ou capturas dos sistemas oficiais. O `.gitignore` bloqueia as extensões e pastas locais mais comuns, mas cada alteração deve ser revisada antes do commit.

## Responsável pelo desenvolvimento

João Paulo da Silveira Velho
