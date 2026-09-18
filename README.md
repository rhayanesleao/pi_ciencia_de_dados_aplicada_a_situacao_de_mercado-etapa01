# PI Ciência de Dados aplicada a Situações de Mercado — Etapa 1

**Curso:** Banco de Dados — SENAC EAD
**Disciplina:** Projeto Integrador - Ciência de Dados Aplicada a Situação de Mercado

**Integrantes do grupo:**
- Arno Wendt Filho
- David Calazans Tavares
- Julyana Mendes
- Paulo Augusto Silva Amorim
- Rafaella Silva
- Rhayane Bernardino Souza Leão

## Fonte de dados

**Brazilian E-Commerce Public Dataset by Olist** — Kaggle
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Mais de 100 mil pedidos reais e anonimizados feitos entre 2016 e 2018 na Olist Store, marketplace
brasileiro que conecta pequenos vendedores a grandes plataformas de e-commerce. O notebook usa as
tabelas de pedidos, itens, clientes, produtos e pagamentos.

## Escopo

Evolução das vendas ao longo do tempo, categorias de produto mais relevantes, distribuição
geográfica das vendas por estado, prazo de entrega e formas de pagamento utilizadas — sempre com
o objetivo de mostrar como cada visualização apoiaria uma decisão real de negócio.

## Como rodar

1. Abra o arquivo `PI_CIÊNCIA_DE_DADOS_APLICADA_A_SITUAÇÕES_DE_MERCADO.ipynb` no
   [Google Colab](https://colab.research.google.com/) (`Arquivo > Fazer upload de notebook`).
2. Crie uma conta gratuita no [Kaggle](https://www.kaggle.com), se ainda não tiver.
3. Em **kaggle.com/settings > API > Create New Token**, baixe o arquivo `kaggle.json`.
4. Execute as células em ordem. Quando a célula de upload pedir, selecione o `kaggle.json`
   baixado — isso autoriza o download automático do dataset dentro do notebook.

## O que o notebook traz

1. Fonte de dados e escopo da análise
2. Ambiente e bibliotecas (Pandas, NumPy, Matplotlib)
3. Download e carga dos dados via API do Kaggle
4. Análise exploratória com Pandas/NumPy (limpeza, merge das tabelas, colunas derivadas)
5. Cinco visualizações em Matplotlib, cada uma com a justificativa de como apoia a tomada de
   decisão:
   - Receita total por mês (sazonalidade)
   - Top 10 categorias de produto por receita
   - Top 10 estados por receita
   - Distribuição do prazo de entrega
   - Formas de pagamento utilizadas
6. Conclusão
