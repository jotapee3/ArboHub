# Roadmap de estabilização

## Concluído nesta fase

- integração semanal do GAL;
- testes de regressão dos fluxos principais;
- remoção da estrutura inicial vazia dentro de `app`;
- centralização das conexões SQLite;
- fechamento garantido das conexões;
- migração não destrutiva do banco para o perfil local do Windows;
- preservação do banco legado;
- registro do ambiente validado e separação das dependências;
- verificação local do Python, pacotes e Chromium;
- documentação da arquitetura, instalação, segurança e recuperação.
- reprodução completa do ambiente em uma máquina virtual limpa;
- preparação do build `onedir` com Chromium incluído.

## Próximas etapas recomendadas

### 1. Distribuição para Windows

- criar executável de teste;
- incluir ícones e recursos necessários;
- validar o Chromium incluído no pacote;
- testar em um segundo computador sem ambiente Python preparado;
- validar atualização sem apagar `%LOCALAPPDATA%\ArboHub`.

### 2. Segurança operacional

- revisar o uso de `ignore_https_errors=True` no GAL;
- definir backup institucional autorizado;
- revisar permissões dos diretórios de DBF, CSV e ZIP;
- realizar revisão de segurança antes de uso ampliado;
- documentar responsáveis por instalação, suporte e revogação de acesso.

### 3. Qualidade

- aumentar testes dos serviços SINAN sem chamar o portal real;
- testar falhas de permissão e caminhos indisponíveis;
- testar migração e recuperação em Windows limpo;
- adicionar verificação automatizada no GitHub sem dados reais;
- criar procedimento de versão e notas de lançamento.

### 4. Novas abas

Somente depois de estabilizar a distribuição:

- definir finalidade e dados mínimos da nova aba;
- obter consentimento e aprovação do setor;
- criar automação, serviço e interface separados;
- adicionar testes antes de integrar ao painel.

### 5. Estado compartilhado opcional

Avaliar apenas se houver necessidade institucional confirmada. A primeira versão deve compartilhar exclusivamente módulo, data de referência, conclusão, horário e responsável, nunca arquivos ou conteúdo clínico.

## Fora do escopo imediato

- sincronizar o banco SQLite inteiro;
- guardar credenciais em servidor próprio;
- copiar automaticamente dados de um computador para outro;
- hospedar DBF, CSV ou ZIP em serviço externo;
- adicionar novas integrações antes de estabilizar instalação e segurança.
