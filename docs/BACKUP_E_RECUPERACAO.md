# Backup e recuperação

Este documento trata do estado operacional do ArboHub. Não autoriza copiar bancos clínicos, DBFs, CSVs ou ZIPs dos sistemas oficiais.

## Identificar o banco ativo

Abra **Configurações → Sobre** e confira **Banco operacional**. O padrão atual é:

```text
%LOCALAPPDATA%\ArboHub\dados\arbohub.db
```

O arquivo `data\arbohub.db`, quando existir, é uma cópia legada e não recebe novas atualizações.

## Regras antes de qualquer cópia

1. feche o ArboHub e os scripts auxiliares;
2. confirme o caminho ativo em Configurações;
3. use apenas destino institucional autorizado;
4. não envie o arquivo por e-mail, chat ou repositório Git;
5. registre quem realizou a operação e por qual motivo.

## Cópia de recuperação local

A opção **Configurações → Manutenção → Backups de reset** abre os backups criados pelo reset controlado de Bases. Eles ficam junto ao diretório de dados ativo.

Uma cópia no mesmo computador protege contra erro operacional, mas não protege contra perda, furto ou falha do equipamento. Backup externo exige um destino institucional definido pela área responsável.

## Banco legado após a migração

Mantenha `data\arbohub.db` durante o período inicial de validação. Ele pode ser removido somente quando:

- o banco ativo estiver confirmado em Configurações;
- o progresso anterior estiver presente;
- pelo menos uma rotina posterior à migração tiver sido validada;
- existir uma cópia de recuperação autorizada;
- o responsável pelo projeto aprovar a remoção.

Apagar o legado não afeta o banco ativo, mas reduz uma opção de recuperação. A remoção deve ser consciente e registrada.

## Restaurar o estado operacional

Não substitua o banco ativo com o aplicativo aberto. O fluxo recomendado é:

1. fechar o ArboHub;
2. criar uma cópia do banco ativo atual com data e hora;
3. validar a integridade do arquivo de recuperação;
4. substituir o ativo somente após confirmar origem e período;
5. abrir o ArboHub e conferir Início e Histórico;
6. executar os testes antes de iniciar uma rotina real.

Enquanto não houver uma ferramenta de restauração validada na interface, essa operação deve ser feita apenas pelo responsável técnico. Não use comandos encontrados em scripts antigos ou mensagens anteriores sem conferir a versão atual.

## Reset não é restauração

O reset de Bases disponível nas Configurações atua sobre a rotina do dia e cria backup antes da alteração. Ele não restaura todo o aplicativo e não deve ser usado para corrigir uma migração ou trocar o banco ativo.

O reset do GAL limpa somente o checkpoint visual do GAL conforme a regra implementada; não apaga o estado do SINAN nem os arquivos já distribuídos.

## Sinais para interromper

Não prossiga com rotina, reset ou restauração se ocorrer qualquer um destes casos:

- o caminho exibido não pertence à conta esperada;
- o Histórico aparece vazio sem motivo;
- há dois bancos recentes e não se sabe qual é o correto;
- aparece erro de integridade, permissão ou arquivo em uso;
- o destino do backup não foi autorizado;
- o arquivo pode conter dados além dos metadados operacionais previstos.
