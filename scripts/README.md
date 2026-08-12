# Scripts auxiliares

Esta pasta contém diagnósticos e testes manuais criados durante o desenvolvimento. Eles não substituem os testes automatizados de `tests/` e não fazem parte do uso normal do ArboHub.

## Regra de uso

- execute somente um script por vez;
- leia o arquivo completo antes de executar;
- confirme o computador, a conta, a data e os destinos;
- não use credenciais ou dados de produção apenas para experimentar;
- feche o ArboHub quando o script manipular o mesmo fluxo;
- interrompa se o navegador ou o portal estiver diferente do esperado.

## Categorias

### Verificação local

- `verificar_ambiente.py`: confere Python, versões dos pacotes e presença do Chromium sem acessar os portais.

### Diagnóstico do SINAN

- `diagnosticar_tempo_criterio_obito.py`;
- `testar_login_sinan.py`;
- `testar_navegacao_consulta.py`;
- `testar_pesquisa_obitos.py`;
- `testar_preenchimento_datas.py`;
- `testar_criterio_obito.py`;
- `testar_adicionar_criterio_obito.py`;
- `testar_agravo_residencia.py`.

### Fluxos de consulta

- `testar_fluxo_dengue_chikungunya.py`;
- `testar_fluxo_com_confirmacao_visual.py`;
- `testar_fluxo_com_janela_nativa.py`.

### Exportação e bases

- `testar_preparacao_exportacao_dbf.py`;
- `testar_solicitacao_dengue_dbf.py`;
- `testar_duas_solicitacoes_dbf.py`;
- `testar_consulta_exportacoes_dbf.py`;
- `testar_acompanhamento_exportacoes_dbf.py`;
- `testar_download_exportacoes_dbf.py`;
- `testar_extracao_dbfs_historico.py`;
- `testar_instalacao_dbfs_bancos_atuais.py`;
- `testar_instalacao_dbfs_pastas_teste.py`;
- `testar_rotina_pos_solicitacao_bases.py`;
- `testar_rotina_completa_bases.py`;
- `registrar_solicitacoes_dbf_existentes.py`.

## Reset de Bases

O reset oficial está em **Configurações → Manutenção** e usa `ManutencaoService`, com prévia, confirmação forte, backup e restauração em caso de falha.

O script antigo `resetar_bases_hoje.py` referencia a localização legada do banco e deve ser removido. Não o execute após a migração para `%LOCALAPPDATA%`.

## Testes automatizados

Para a validação segura que não acessa os portais reais:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
