# Segurança e dados

## Princípios

O ArboHub atua em um contexto de saúde e deve seguir necessidade, minimização, autorização e rastreabilidade. A existência técnica de uma funcionalidade não substitui o consentimento do setor, do responsável pelo dado ou da equipe de segurança institucional.

Regras permanentes:

- processar somente o necessário para a rotina autorizada;
- não publicar dados operacionais ou de saúde no Git;
- não reutilizar credenciais entre pessoas;
- não sincronizar dados entre computadores sem aprovação formal;
- manter supervisão humana sobre as automações;
- interromper a rotina quando a origem, o destino ou o responsável estiverem incertos.

## Inventário local

| Item | Conteúdo | Local | Observação |
| --- | --- | --- | --- |
| Configurações | aparência, caminhos, parâmetros e contatos de supervisão | `%LOCALAPPDATA%\ArboHub\configuracoes.json` | não contém senha, mas pode conter nomes, contato e caminhos internos |
| Banco operacional | datas, estados, horários, responsável, observações e números de solicitações | `%LOCALAPPDATA%\ArboHub\dados\arbohub.db` | não deve conter registros de pacientes |
| Credencial SINAN | usuário e senha | Gerenciador de Credenciais do Windows | alvo `ArboHub/SINAN`, associado à conta do Windows |
| Temporários SINAN | arquivos intermediários de exportação | `%LOCALAPPDATA%\ArboHub\temp\exportacoes` | devem existir apenas durante o processamento necessário |
| Arquivos SINAN/GAL | DBF, CSV e ZIP validados | destinos configurados | podem conter dados sensíveis e seguem as regras do setor |
| Banco legado | cópia anterior do estado operacional | `data\arbohub.db` em instalações migradas | recuperação temporária; não é mais o banco ativo |

## Credenciais

A senha do SINAN não é escrita no SQLite, no JSON, nos logs ou no repositório. O serviço usa a API do Gerenciador de Credenciais do Windows e evita representar a senha em mensagens de diagnóstico.

Ainda assim:

- o salvamento automático deve ser opcional;
- o operador deve consentir antes de salvar;
- cada pessoa deve usar sua própria conta;
- credenciais devem ser removidas ao trocar de função ou computador;
- não se deve enviar senha por e-mail, chat, planilha ou commit.

O fluxo atual do GAL permanece com login e CAPTCHA supervisionados manualmente.

## Proteção do banco local

Mover o SQLite para `%LOCALAPPDATA%` evita que ele seja versionado ou distribuído junto com o código. Isso não equivale a criptografia.

O banco depende das proteções da conta e do computador Windows. Em ambiente institucional, recomenda-se:

- bloqueio de tela e senha individual;
- BitLocker ou política institucional equivalente;
- atualizações de segurança do sistema;
- princípio do menor privilégio;
- restrição de cópias para nuvens pessoais, pendrives e e-mails;
- backup somente em destino institucional autorizado.

## Repositório

O `.gitignore` exclui bancos, dados, logs, arquivos exportados, credenciais e rastros comuns. Antes de cada commit, execute:

```powershell
git status --short
git diff --cached --check
git diff --cached --stat
```

Se aparecer `.db`, `.dbf`, `.csv`, `.zip`, `.env`, log, captura de tela de portal ou arquivo desconhecido, interrompa o commit e revise.

## Portais e rede

As automações acessam somente os endereços definidos para SINAN e GAL no código. O navegador é visível para permitir supervisão humana. O GAL usa `ignore_https_errors=True` no contexto automatizado; essa exceção deve ser revista com a infraestrutura institucional antes da distribuição final.

## Compartilhamento entre computadores

Não há sincronização nesta versão. Caso o setor aprove futuramente um painel compartilhado, o escopo mínimo previsto é:

- módulo;
- data de referência;
- concluído ou pendente;
- data e hora de conclusão;
- responsável.

Não devem ser sincronizados DBFs, CSVs, ZIPs, números de solicitação, observações, credenciais, caminhos, logs, conteúdo clínico ou o banco SQLite completo.

Antes de implementar esse compartilhamento serão necessários, no mínimo:

- aprovação do responsável pelo processo e da segurança institucional;
- base legal e finalidade registradas;
- autenticação individual;
- autorização por perfil;
- criptografia em trânsito e em repouso;
- trilha de auditoria;
- política de retenção e exclusão;
- procedimento de incidente e revogação de acesso.

## Comunicação de suporte

Ao relatar problemas, informe versão, módulo, horário e mensagem de erro. Remova dados de pacientes, senhas, números de solicitação, caminhos internos e capturas de portais, salvo quando houver canal institucional explicitamente autorizado.
