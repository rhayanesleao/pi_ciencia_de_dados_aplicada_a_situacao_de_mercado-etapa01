# Registro de Execução dos Testes Automatizados

- **Data:** 22/11/2026
- **Responsável:** Paulo (`@paulogkl`)
- **Comando executado:** `pytest -q`
- **Status:** Sucesso (9 testes aprovados, 1 aviso de depreciação)

## Saída do Terminal
```text
.........                                                                                        [100%]
=========================================== warnings summary ===========================================
tests/test_transformacao.py::test_somente_pedidos_entregues_com_data
  /workspaces/pi_ciencia_de_dados_aplicada_a_situacao_de_mercado-etapa01/etl/transformacao.py:88: Pandas4Warning: Series.dt.dayofweek is deprecated and will be removed in a future version. Use Series.dt.day_of_week instead.
    dim["num_dia_semana"] = dim["data"].dt.dayofweek.astype(int)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 1 warning in 5.61s
```
