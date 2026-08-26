# Qualifica Vigilância

## Estratégia de reconstrução

O programa legado será incorporado ao ArboHub uma rotina por vez. A ordem
de desenvolvimento respeita as dependências entre os relatórios e evita
que uma única tela concentre regras de negócio, leitura de arquivos e
processamento em segundo plano.

Cada rotina passa pelas seguintes etapas:

1. caracterização do comportamento existente;
2. testes com registros totalmente sintéticos;
3. implementação do serviço sem interface;
4. comparação dos nomes, colunas e resultados esperados;
5. validação operacional autorizada;
6. integração à página Qualifica.

Nenhum DBF, CSV ou XLSX operacional é armazenado no repositório ou nos
testes.

## Relatório de 72 horas

O primeiro serviço implementado calcula a oportunidade de digitação das
notificações do SINAN.

### Entradas

- dicionário XLSX com código IBGE, nome do município e CRS;
- um ou mais bancos DBF do SINAN;
- período inclusivo da data dos primeiros sintomas;
- caminho do relatório XLSX de saída.

### Regra preservada

- o filtro usa `DT_SIN_PRI`;
- o município avaliado é `ID_MUNICIP`, município de notificação;
- o atraso é `DT_DIGITA - DT_NOTIFIC`;
- de zero a três dias, inclusive, é considerado dentro do prazo;
- datas ausentes, inválidas ou anteriores à notificação ficam fora do prazo;
- números de notificação repetidos não são removidos automaticamente;
- todos os municípios do dicionário aparecem, inclusive aqueles sem casos;
- o resultado contém as abas `Resumo_Estadual` e `Dados_Municipios`.

O serviço retorna e exporta somente agregados municipais. Identificadores
individuais não são incluídos no resultado nem nas mensagens operacionais.

### Calendário epidemiológico

A semana epidemiológica começa no domingo e termina no sábado. A semana 1
é aquela que contém a maior quantidade de dias de janeiro. O cálculo é
local e não depende da disponibilidade de um site durante a execução.

Referência institucional:
https://portalsinan.saude.gov.br/perguntas-frequentes

### Segurança da saída

O XLSX é escrito em arquivo temporário, reaberto para validação e publicado
no destino somente depois dessa conferência. Se a publicação falhar, um
arquivo anterior permanece preservado.

### Validação manual antes da interface

Após instalar as dependências do projeto, o serviço pode ser validado em
um cenário autorizado com:

```powershell
python scripts\testar_qualifica_72h.py `
    --dicionario "C:\caminho\dicionario_municipios.xlsx" `
    --dbf "C:\caminho\DENGON26.dbf" `
    --inicio "04/01/2026" `
    --fim "31/01/2026" `
    --saida "C:\caminho\Relatorio_72h.xlsx"
```

O comando apresenta somente totais agregados e mensagens operacionais.
