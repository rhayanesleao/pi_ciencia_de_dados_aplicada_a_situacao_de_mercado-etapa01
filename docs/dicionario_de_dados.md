# Dicionário de dados

Modelo estrela gerado por `etl/transformacao.py` a partir do dataset da Olist. Todas as tabelas ficam em `data/*.parquet`.

## fato_pedidos

Grão: um item de pedido entregue.

| Coluna | Tipo | Descrição |
|---|---|---|
| `id_pedido` | texto | Identificador do pedido (`order_id`) |
| `id_item` | inteiro | Posição do item dentro do pedido |
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
| `prazo_outlier` | booleano | Verdadeiro quando o prazo de entrega está acima do percentil 98 |

## dim_tempo

| Coluna | Descrição |
|---|---|
| `id_tempo` | Data no formato AAAAMMDD |
| `data` | Data |
| `ano`, `mes`, `trimestre` | Partes da data |
| `nome_mes` | Nome do mês em português |
| `ano_mes` | Ano e mês (AAAA-MM) |
| `num_dia_semana` | 0 = segunda a 6 = domingo |
| `dia_semana` | Nome do dia da semana |

## dim_cliente

| Coluna | Descrição |
|---|---|
| `id_cliente` | Identificador do cliente no pedido (`customer_id`) |
| `id_cliente_unico` | Identificador da pessoa (`customer_unique_id`), igual entre pedidos do mesmo cliente |
| `cep_prefixo_cliente` | Prefixo do CEP |
| `cidade_cliente`, `uf_cliente` | Cidade e estado |

## dim_produto

| Coluna | Descrição |
|---|---|
| `id_produto` | Identificador do produto |
| `categoria` | Categoria (`sem_categoria` quando ausente) |
| `peso_g` | Peso em gramas |
| `comprimento_cm`, `altura_cm`, `largura_cm` | Dimensões em centímetros |
| `qtd_fotos` | Quantidade de fotos do anúncio |

## dim_vendedor

| Coluna | Descrição |
|---|---|
| `id_vendedor` | Identificador do vendedor |
| `cep_prefixo_vendedor` | Prefixo do CEP |
| `cidade_vendedor`, `uf_vendedor` | Cidade e estado |

## dim_pagamento

Combinações de forma de pagamento e faixa de parcelas. Para pedidos com mais de um pagamento vale o de maior valor.

| Coluna | Descrição |
|---|---|
| `id_pagamento` | Chave (0 = "Não informado") |
| `tipo_pagamento` | Cartão de crédito, Boleto, Voucher, Cartão de débito ou Não definido |
| `faixa_parcelas` | À vista (1x), 2 a 5x, 6 a 10x ou Mais de 10x |

## dim_entrega

Oito linhas fixas: situação da entrega combinada com a faixa de prazo.

| Coluna | Descrição |
|---|---|
| `id_entrega` | Chave |
| `situacao_entrega` | No prazo ou Atrasado |
| `faixa_prazo` | Até 7 dias, 8 a 14 dias, 15 a 30 dias ou Mais de 30 dias |

## qualidade_etl.json

Relatório gerado a cada execução do ETL: pedidos por etapa do filtro, itens e pedidos na fato, pedidos sem pagamento,
produtos sem categoria, limite de prazo atípico (percentil 98), percentual de pedidos atrasados, chaves órfãs
(esperado zero) e número de linhas por tabela.
