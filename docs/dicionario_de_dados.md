# Dicionário de dados

Modelo estrela gerado por `etl/transformacao.py` a partir do dataset da Olist. Todas as tabelas ficam em `data/*.parquet`.

## fato_pedidos

Grão: um item de pedido entregue (com `order_status == "delivered"` e data de entrega preenchida).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pedido` | texto | Identificador do pedido (`order_id`) |
| `id_item` | inteiro | Posição do item dentro do pedido (`order_item_id`) |
| `id_tempo` | inteiro | Data da compra no formato AAAAMMDD (chave de `dim_tempo`) |
| `hora_compra` | inteiro | Hora da compra (0 a 23) |
| `id_cliente` | texto | Chave de `dim_cliente` |
| `id_produto` | texto | Chave de `dim_produto` |
| `id_vendedor` | texto | Chave de `dim_vendedor` |
| `id_pagamento` | inteiro | Chave de `dim_pagamento` (0 = pedido sem pagamento registrado) |
| `id_entrega` | inteiro | Chave de `dim_entrega` |
| `preco` | decimal | Preço do item em reais |
| `frete` | decimal | Frete do item em reais |
| `receita` | decimal | `preco` + `frete` |
| `prazo_entrega_dias` | inteiro | Dias completos entre a compra e a entrega ao cliente |
| `prazo_estimado_dias` | inteiro | Dias completos entre a compra e a data estimada de entrega |
| `dias_atraso` | inteiro | Dias de calendário entre a data estimada e a entrega, zero se no prazo |
| `prazo_outlier` | booleano | Verdadeiro quando o prazo de entrega está estritamente acima do percentil 98 |

## dim_tempo

Calendário contínuo entre a primeira e a última data de compra.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_tempo` | inteiro | Data no formato AAAAMMDD |
| `data` | data | Data normalizada (sem horário) |
| `ano`, `mes`, `trimestre` | inteiro | Partes numéricas da data |
| `nome_mes` | texto | Nome do mês em português |
| `ano_mes` | texto | Ano e mês (AAAA-MM) |
| `num_dia_semana` | inteiro | 0 = segunda a 6 = domingo |
| `dia_semana` | texto | Nome do dia da semana em português |

## dim_cliente

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_cliente` | texto | Identificador do cliente no pedido (`customer_id`) |
| `id_cliente_unico` | texto | Identificador da pessoa (`customer_unique_id`), igual entre pedidos do mesmo cliente |
| `cep_prefixo_cliente` | inteiro | Prefixo numérico do CEP |
| `cidade_cliente`, `uf_cliente` | texto | Cidade (padronizada com iniciais maiúsculas) e estado |

## dim_produto

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_produto` | texto | Identificador do produto |
| `categoria` | texto | Categoria (`sem_categoria` quando ausente) |
| `peso_g` | decimal | Peso em gramas |
| `comprimento_cm`, `altura_cm`, `largura_cm` | decimal | Dimensões em centímetros |
| `qtd_fotos` | decimal | Quantidade de fotos do anúncio |

## dim_vendedor

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_vendedor` | texto | Identificador do vendedor |
| `cep_prefixo_vendedor` | inteiro | Prefixo numérico do CEP |
| `cidade_vendedor`, `uf_vendedor` | texto | Cidade (padronizada com iniciais maiúsculas) e estado |

## dim_pagamento

Combinações de forma de pagamento e faixa de parcelas. Para pedidos com mais de um pagamento vale o de maior valor (com desempate pelo menor `payment_sequential`).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pagamento` | inteiro | Chave (0 = pedido sem pagamento registrado) |
| `tipo_pagamento` | texto | Cartão de crédito, Boleto, Voucher, Cartão de débito, Não definido ou Não informado (quando `id_pagamento = 0`) |
| `faixa_parcelas` | texto | À vista (1x), 2 a 5x, 6 a 10x, Mais de 10x ou Não informado (quando `id_pagamento = 0`) |

## dim_entrega

Oito linhas fixas: situação da entrega combinada com a faixa de prazo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_entrega` | inteiro | Chave (1 a 8) |
| `situacao_entrega` | texto | No prazo ou Atrasado |
| `faixa_prazo` | texto | Até 7 dias, 8 a 14 dias, 15 a 30 dias ou Mais de 30 dias |

## qualidade_etl.json

Relatório gerado a cada execução do ETL: pedidos por etapa do filtro, itens e pedidos na fato, pedidos sem pagamento,
produtos sem categoria, limite de prazo atípico (percentil 98), percentual de pedidos atrasados, chaves órfãs
(esperado zero) e número de linhas por tabela.

---

## Histórico de Revisão

- **22/11/2026 (`@paulogkl`):** Dicionário de dados revisado contra `etl/transformacao.py` (Issue #1). Adicionada tipagem nas dimensões e detalhadas regras de tratamento (`id_pagamento = 0`, padronização de cidades e critério de desempate de pagamentos).
