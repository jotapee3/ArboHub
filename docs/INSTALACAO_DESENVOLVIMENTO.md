# Instalação para desenvolvimento

Este procedimento é destinado ao desenvolvimento e à validação interna. A distribuição para usuários finais será tratada em uma etapa posterior por meio de um executável e de um processo de instalação controlado.

## Pré-requisitos

- Windows 10 ou 11 atualizado;
- Python 3.14 no ambiente atualmente validado;
- Git;
- acesso de rede autorizado aos portais utilizados;
- permissões do setor para ler e escrever nos destinos configurados.

Não use uma conta administrativa apenas para executar o ArboHub. A conta comum autorizada do operador é suficiente e reduz o impacto de uma eventual falha.

## Obter o projeto

```powershell
git clone https://github.com/jotapee3/ArboHub.git
cd ArboHub
git switch estabilizacao-arquitetura
```

Para uma cópia já existente:

```powershell
git status
git pull --ff-only
```

Interrompa a atualização se houver alterações locais não reconhecidas.

## Criar o ambiente

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock.txt
python -m playwright install chromium
python scripts/verificar_ambiente.py
```

O comando `python -m playwright install chromium` instala o navegador controlado pelo Playwright. A presença do Chrome ou Edge comum não substitui necessariamente essa etapa.

Os arquivos de dependência têm finalidades diferentes:

- `requirements.txt`: bibliotecas diretas necessárias ao aplicativo;
- `requirements-dev.txt`: bibliotecas diretas do aplicativo e do desenvolvimento;
- `requirements.lock.txt`: fotografia exata do ambiente validado, incluindo dependências transitivas.

Para reproduzir o ambiente atual, use o arquivo `requirements.lock.txt`. Consulte [Dependências](DEPENDENCIAS.md) antes de atualizar qualquer versão.

## Validar antes da primeira abertura

```powershell
python -m compileall -q app tests
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/verificar_ambiente.py
git status --short
```

O conjunto atual possui oito testes. O número pode aumentar; o critério permanente é que todos terminem com `OK`.

## Executar

Uso normal em desenvolvimento:

```powershell
python main.py
```

Reinicialização automática ao editar arquivos Python:

```powershell
python dev.py
```

## Primeira abertura

Na primeira abertura de uma instalação antiga, o banco `data\arbohub.db` é copiado para `%LOCALAPPDATA%\ArboHub\dados\arbohub.db`. A origem é preservada.

Confira em **Configurações → Sobre** qual banco está ativo. Não conclua uma rotina enquanto essa verificação não estiver de acordo com o computador e a conta do operador.

## Configuração operacional

Revise em **Configurações**:

- caminhos de histórico do SINAN;
- destinos de teste AB1 e AB2;
- pasta de Bancos_Atuais;
- nomes finais dos DBFs;
- preferência de login automático;
- identidade exibida do Windows;
- credencial do SINAN, se o armazenamento for autorizado.

Os destinos podem variar entre computadores. Não presuma que a unidade `F:` existe ou possui a mesma permissão em outra estação.

## Instalação em outro computador

Enquanto não houver executável oficial:

1. obtenha o código somente do repositório autorizado;
2. crie um ambiente virtual próprio naquele computador;
3. instale as dependências e o Chromium;
4. execute os testes;
5. abra e revise as configurações sem iniciar rotinas;
6. valide os destinos com a responsável pelo setor;
7. cadastre credenciais apenas com consentimento do titular.

Não copie automaticamente `configuracoes.json`, `arbohub.db`, credenciais ou arquivos exportados de outro usuário.

## Atualização segura

Antes de atualizar:

```powershell
git status
python -m unittest discover -s tests -p "test_*.py" -v
```

Depois de atualizar:

```powershell
python -m compileall -q app tests
python -m unittest discover -s tests -p "test_*.py" -v
python main.py
```

Verifique as páginas antes de executar uma rotina real.
