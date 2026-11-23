# Validação dos indicadores do dashboard contra a Etapa 1

Este documento compara os números do dashboard (Etapa 2) com os da análise exploratória (Etapa 1) e explica cada diferença.

## Conclusão

Os indicadores validados (receita, pedidos, ticket médio, prazo de entrega, atraso, ranking de estados, formas de pagamento, categorias e UF do vendedor) são consistentes com a Etapa 1. As diferenças que aparecem vêm de **decisões de método da Etapa 2**, descritas abaixo, e não de erro de cálculo.

## Comparação

| Indicador | Etapa 1 | Dashboard (Etapa 2) | Situação |
|---|---|---|---|
| Pedidos entregues | 96.478 | 96.470 | 8 pedidos entregues sem data de entrega foram removidos no ETL |
| Receita total (preço + frete) | cerca de R$ 15,42 mi | R$ 15,42 mi | Confere |
| Mês de maior receita | 2017-11 | 2017-11 | Confere |
| Prazo médio de entrega | 11,2 dias | 12,1 dias | Muda a regra de outliers (ver abaixo) |
| Entregas atrasadas | 7,9% | 6,8% | Muda a unidade de contagem e a regra de atraso (ver abaixo) |
| Formas de pagamento | uma linha por pagamento | pagamento principal por pedido | Muda a regra, evita duplicar pedidos |

Outros indicadores conferidos no dashboard: ticket médio de R$ 159,83, SP com 37,4% da receita e AL com a maior taxa de atraso (21,4%).

## Por que os números mudaram

**Prazo médio (11,2 para 12,1 dias).** Na Etapa 1, o cálculo do prazo médio descartava os 2% maiores prazos de entrega (valores atípicos) antes da média. No dashboard, o indicador usa todos os pedidos, e os prazos atípicos ficam apenas sinalizados na coluna `prazo_outlier` da tabela-fato. A média sobe porque as entregas muito demoradas passam a contar. O histograma do dashboard continua sem os 2% maiores prazos, para que o gráfico seja legível, e isso está indicado na própria tela.

**Entregas atrasadas (7,9% para 6,8%).** Duas regras mudaram:

- A Etapa 1 contava por **item** do pedido; o dashboard conta por **pedido**. Pedidos com muitos itens deixam de pesar mais.
- A Etapa 1 comparava data e hora da entrega com a data estimada. O dashboard considera atraso somente quando a entrega ocorre em um **dia do calendário posterior** ao estimado.

**Formas de pagamento.** A Etapa 1 contava cada linha de pagamento. Como um pedido pode ter mais de um pagamento, isso multiplicava pedidos. No modelo estrela, cada pedido recebe o pagamento de **maior valor**.

**Pedidos entregues (96.478 para 96.470).** O ETL mantém apenas pedidos com status `delivered` e data de entrega preenchida. Oito pedidos entregues não tinham data e foram removidos. O relatório `data/qualidade_etl.json` registra essa remoção.

## Categorias e UF do vendedor validadas contra os CSVs originais

O arquivo `pedidos_recorte.csv` do dashboard traz uma linha por pedido e não inclui categoria nem UF do vendedor. Por isso, essas duas dimensões foram conferidas de outra forma: a receita por categoria e por UF do vendedor calculada a partir do modelo estrela (`data/*.parquet`) foi comparada com a calculada direto dos CSVs originais da Olist, usando o mesmo critério (pedidos entregues com data de entrega, receita = preço + frete).

| Verificação | Resultado |
|---|---|
| Maior diferença de receita por categoria | R$ 0,00 |
| Maior diferença de receita por UF do vendedor | R$ 0,00 |
| Número de categorias (modelo estrela e CSVs) | 74 e 74 |
| Número de UFs do vendedor (modelo estrela e CSVs) | 22 e 22 |

Maiores categorias por receita: beleza_saude (R$ 1.412.089,53), relogios_presentes (R$ 1.264.016,98) e cama_mesa_banho (R$ 1.225.209,26). Maiores UFs do vendedor: SP (R$ 9.955.994,13), PR (R$ 1.424.161,25) e MG (R$ 1.184.111,40).

Conclusão: categorias e UF do vendedor do dashboard coincidem exatamente com os dados originais.

## Como reproduzir a validação de categorias e UF do vendedor

No Google Colab, depois de baixar os CSVs da Olist em `olist_data/` (mesma célula do notebook do ETL) e com os arquivos `data/*.parquet` do repositório:

```python
import pandas as pd

# 1) Valores do modelo estrela
fato = pd.read_parquet("data/fato_pedidos.parquet")
prod = pd.read_parquet("data/dim_produto.parquet")[["id_produto", "categoria"]]
vend = pd.read_parquet("data/dim_vendedor.parquet")[["id_vendedor", "uf_vendedor"]]
df = fato.merge(prod, on="id_produto").merge(vend, on="id_vendedor")
cat_dw = df.groupby("categoria")["receita"].sum().sort_values(ascending=False)
uf_dw = df.groupby("uf_vendedor")["receita"].sum().sort_values(ascending=False)

# 2) Mesmos totais direto dos CSVs originais
p = "olist_data/"
orders = pd.read_csv(p + "olist_orders_dataset.csv")
itens = pd.read_csv(p + "olist_order_items_dataset.csv")
produtos = pd.read_csv(p + "olist_products_dataset.csv")
vendedores = pd.read_csv(p + "olist_sellers_dataset.csv")

ok = orders[(orders.order_status == "delivered")
            & orders.order_delivered_customer_date.notna()][["order_id"]]
raw = (itens.merge(ok, on="order_id")
            .merge(produtos[["product_id", "product_category_name"]], on="product_id", how="left")
            .merge(vendedores[["seller_id", "seller_state"]], on="seller_id", how="left"))
raw["receita"] = raw["price"] + raw["freight_value"]
raw["product_category_name"] = raw["product_category_name"].fillna("sem_categoria")

cat_raw = raw.groupby("product_category_name")["receita"].sum().sort_values(ascending=False)
uf_raw = raw.groupby("seller_state")["receita"].sum().sort_values(ascending=False)

# 3) Diferença máxima (esperado: próxima de zero)
print(cat_dw.sub(cat_raw, fill_value=0).abs().max())
print(uf_dw.sub(uf_raw, fill_value=0).abs().max())
print(cat_dw.head(10))
print(uf_dw.head(10))
```

Se as duas diferenças máximas forem próximas de zero (da ordem de centavos), as categorias e as UFs do vendedor do dashboard estão corretas.
