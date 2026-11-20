"""ETL da Olist: CSVs brutos do Kaggle -> modelo estrela em arquivos parquet.

Entrada (pasta com os CSVs originais):
    olist_orders_dataset.csv, olist_order_items_dataset.csv,
    olist_customers_dataset.csv, olist_products_dataset.csv,
    olist_sellers_dataset.csv, olist_order_payments_dataset.csv

Saida (pasta de destino):
    fato_pedidos.parquet  (grao: um item de pedido entregue)
    dim_tempo, dim_cliente, dim_produto, dim_vendedor,
    dim_pagamento, dim_entrega (.parquet)
    qualidade_etl.json    (contagens e checagens de qualidade)

Uso na linha de comando:
    python etl/transformacao.py --origem olist_data --destino data
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
TIPOS_PAGAMENTO = {
    "credit_card": "Cartão de crédito",
    "boleto": "Boleto",
    "voucher": "Voucher",
    "debit_card": "Cartão de débito",
    "not_defined": "Não definido",
}
FAIXAS_PARCELAS = ["À vista (1x)", "2 a 5x", "6 a 10x", "Mais de 10x"]
FAIXAS_PRAZO = ["Até 7 dias", "8 a 14 dias", "15 a 30 dias", "Mais de 30 dias"]
SITUACOES_ENTREGA = ["No prazo", "Atrasado"]
COLUNAS_DATA = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def carregar_tabelas(origem):
    """Le os seis CSVs da Olist necessarios para o modelo estrela."""
    origem = Path(origem)
    return {
        "orders": pd.read_csv(origem / "olist_orders_dataset.csv", parse_dates=COLUNAS_DATA),
        "order_items": pd.read_csv(origem / "olist_order_items_dataset.csv"),
        "customers": pd.read_csv(origem / "olist_customers_dataset.csv"),
        "products": pd.read_csv(origem / "olist_products_dataset.csv"),
        "sellers": pd.read_csv(origem / "olist_sellers_dataset.csv"),
        "payments": pd.read_csv(origem / "olist_order_payments_dataset.csv"),
    }


def filtrar_pedidos_entregues(orders):
    """Mantem so pedidos entregues e com data de entrega preenchida."""
    entregues = orders[orders["order_status"] == "delivered"]
    sem_data = entregues["order_delivered_customer_date"].isna()
    validos = entregues[~sem_data].copy()
    log = {
        "pedidos_total": int(len(orders)),
        "pedidos_entregues": int(len(entregues)),
        "entregues_sem_data_de_entrega_removidos": int(sem_data.sum()),
        "pedidos_validos": int(len(validos)),
    }
    return validos, log


def construir_dim_tempo(datas):
    """Calendario continuo, do primeiro ao ultimo dia de compra."""
    dias = pd.date_range(datas.min().normalize(), datas.max().normalize(), freq="D")
    dim = pd.DataFrame({"data": dias})
    dim["id_tempo"] = dim["data"].dt.strftime("%Y%m%d").astype(int)
    dim["ano"] = dim["data"].dt.year.astype(int)
    dim["mes"] = dim["data"].dt.month.astype(int)
    dim["nome_mes"] = dim["mes"].map(lambda m: MESES[m - 1])
    dim["ano_mes"] = dim["data"].dt.strftime("%Y-%m")
    dim["trimestre"] = dim["data"].dt.quarter.astype(int)
    dim["num_dia_semana"] = dim["data"].dt.dayofweek.astype(int)
    dim["dia_semana"] = dim["num_dia_semana"].map(lambda i: DIAS_SEMANA[i])
    return dim


def construir_dim_cliente(customers):
    dim = customers.rename(
        columns={
            "customer_id": "id_cliente",
            "customer_unique_id": "id_cliente_unico",
            "customer_zip_code_prefix": "cep_prefixo_cliente",
            "customer_city": "cidade_cliente",
            "customer_state": "uf_cliente",
        }
    )[["id_cliente", "id_cliente_unico", "cep_prefixo_cliente", "cidade_cliente", "uf_cliente"]]
    dim = dim.drop_duplicates("id_cliente").copy()
    dim["cidade_cliente"] = dim["cidade_cliente"].str.title()
    return dim


def construir_dim_produto(products):
    dim = products.rename(
        columns={
            "product_id": "id_produto",
            "product_category_name": "categoria",
            "product_weight_g": "peso_g",
            "product_length_cm": "comprimento_cm",
            "product_height_cm": "altura_cm",
            "product_width_cm": "largura_cm",
            "product_photos_qty": "qtd_fotos",
        }
    )[["id_produto", "categoria", "peso_g", "comprimento_cm", "altura_cm", "largura_cm", "qtd_fotos"]]
    dim = dim.drop_duplicates("id_produto").copy()
    dim["categoria"] = dim["categoria"].fillna("sem_categoria")
    return dim


def construir_dim_vendedor(sellers):
    dim = sellers.rename(
        columns={
            "seller_id": "id_vendedor",
            "seller_zip_code_prefix": "cep_prefixo_vendedor",
            "seller_city": "cidade_vendedor",
            "seller_state": "uf_vendedor",
        }
    )[["id_vendedor", "cep_prefixo_vendedor", "cidade_vendedor", "uf_vendedor"]]
    dim = dim.drop_duplicates("id_vendedor").copy()
    dim["cidade_vendedor"] = dim["cidade_vendedor"].str.title()
    return dim


def preparar_pagamento_por_pedido(payments):
    """Um pedido pode ter varios pagamentos; fica o de maior valor (principal).

    Assim o pagamento nao multiplica a receita ao ser ligado aos itens.
    """
    ordenado = payments.sort_values(
        ["order_id", "payment_value", "payment_sequential"], ascending=[True, False, True]
    )
    principal = ordenado.drop_duplicates("order_id", keep="first").copy()
    principal["tipo_pagamento"] = principal["payment_type"].map(TIPOS_PAGAMENTO).fillna("Não definido")
    principal["faixa_parcelas"] = pd.cut(
        principal["payment_installments"],
        bins=[-np.inf, 1, 5, 10, np.inf],
        labels=FAIXAS_PARCELAS,
    ).astype(str)
    return principal[["order_id", "tipo_pagamento", "faixa_parcelas"]]


def construir_dim_pagamento(pagamento_por_pedido):
    """Dimensao pequena: combinacoes de tipo de pagamento e faixa de parcelas."""
    combos = (
        pagamento_por_pedido[["tipo_pagamento", "faixa_parcelas"]]
        .drop_duplicates()
        .sort_values(["tipo_pagamento", "faixa_parcelas"])
        .reset_index(drop=True)
    )
    combos.insert(0, "id_pagamento", np.arange(1, len(combos) + 1))
    nao_informado = pd.DataFrame(
        {"id_pagamento": [0], "tipo_pagamento": ["Não informado"], "faixa_parcelas": ["Não informado"]}
    )
    return pd.concat([nao_informado, combos], ignore_index=True)


def construir_dim_entrega():
    """Dimensao fixa: situacao da entrega x faixa de prazo."""
    linhas = [(s, f) for s in SITUACOES_ENTREGA for f in FAIXAS_PRAZO]
    dim = pd.DataFrame(linhas, columns=["situacao_entrega", "faixa_prazo"])
    dim.insert(0, "id_entrega", np.arange(1, len(dim) + 1))
    return dim


def construir_fato(order_items, pedidos, pagamento_por_pedido, dim_pagamento, dim_entrega):
    """Tabela-fato no grao de item de pedido, com medidas de receita e entrega."""
    cols_pedido = [
        "order_id", "customer_id", "order_purchase_timestamp",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ]
    fato = order_items.merge(pedidos[cols_pedido], on="order_id", how="inner")

    pagamentos = pagamento_por_pedido.merge(
        dim_pagamento, on=["tipo_pagamento", "faixa_parcelas"], how="left"
    )[["order_id", "id_pagamento"]]
    fato = fato.merge(pagamentos, on="order_id", how="left")
    fato["id_pagamento"] = fato["id_pagamento"].fillna(0).astype(int)

    compra = fato["order_purchase_timestamp"]
    entrega = fato["order_delivered_customer_date"]
    estimada = fato["order_estimated_delivery_date"]

    fato["id_tempo"] = compra.dt.strftime("%Y%m%d").astype(int)
    fato["hora_compra"] = compra.dt.hour.astype(int)
    fato["prazo_entrega_dias"] = (entrega - compra).dt.days.astype(int)
    fato["prazo_estimado_dias"] = (estimada - compra).dt.days.astype(int)
    fato["dias_atraso"] = (entrega.dt.normalize() - estimada).dt.days.clip(lower=0).astype(int)

    situacao = np.where(fato["dias_atraso"] > 0, "Atrasado", "No prazo")
    faixa = pd.cut(
        fato["prazo_entrega_dias"],
        bins=[-np.inf, 7, 14, 30, np.inf],
        labels=FAIXAS_PRAZO,
    ).astype(str)
    chave = pd.DataFrame({"situacao_entrega": situacao, "faixa_prazo": faixa})
    chave = chave.merge(dim_entrega, on=["situacao_entrega", "faixa_prazo"], how="left")
    fato["id_entrega"] = chave["id_entrega"].to_numpy()

    fato["preco"] = fato["price"]
    fato["frete"] = fato["freight_value"]
    fato["receita"] = fato["preco"] + fato["frete"]

    limite = float(fato["prazo_entrega_dias"].quantile(0.98))
    fato["prazo_outlier"] = fato["prazo_entrega_dias"] > limite

    fato = fato.rename(
        columns={
            "order_id": "id_pedido",
            "order_item_id": "id_item",
            "customer_id": "id_cliente",
            "product_id": "id_produto",
            "seller_id": "id_vendedor",
        }
    )
    colunas = [
        "id_pedido", "id_item", "id_tempo", "hora_compra", "id_cliente", "id_produto",
        "id_vendedor", "id_pagamento", "id_entrega", "preco", "frete", "receita",
        "prazo_entrega_dias", "prazo_estimado_dias", "dias_atraso", "prazo_outlier",
    ]
    return fato[colunas].copy(), limite


def checar_integridade(fato, dims):
    """Conta chaves da fato sem correspondente na dimensao (esperado: zero)."""
    chaves = {
        "id_tempo": "dim_tempo", "id_cliente": "dim_cliente", "id_produto": "dim_produto",
        "id_vendedor": "dim_vendedor", "id_pagamento": "dim_pagamento", "id_entrega": "dim_entrega",
    }
    orfas = {}
    for chave, nome_dim in chaves.items():
        orfas[chave] = int((~fato[chave].isin(dims[nome_dim][chave])).sum())
    return orfas


def salvar(tabelas, destino):
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    for nome, df in tabelas.items():
        df.to_parquet(destino / f"{nome}.parquet", index=False)


def executar(origem, destino):
    """Roda o pipeline completo e devolve o relatorio de qualidade."""
    bruto = carregar_tabelas(origem)

    pedidos, log = filtrar_pedidos_entregues(bruto["orders"])

    dim_tempo = construir_dim_tempo(pedidos["order_purchase_timestamp"])
    dim_cliente = construir_dim_cliente(bruto["customers"])
    dim_produto = construir_dim_produto(bruto["products"])
    dim_vendedor = construir_dim_vendedor(bruto["sellers"])
    pagamento_por_pedido = preparar_pagamento_por_pedido(bruto["payments"])
    dim_pagamento = construir_dim_pagamento(pagamento_por_pedido)
    dim_entrega = construir_dim_entrega()

    fato, limite_outlier = construir_fato(
        bruto["order_items"], pedidos, pagamento_por_pedido, dim_pagamento, dim_entrega
    )

    tabelas = {
        "fato_pedidos": fato,
        "dim_tempo": dim_tempo,
        "dim_cliente": dim_cliente,
        "dim_produto": dim_produto,
        "dim_vendedor": dim_vendedor,
        "dim_pagamento": dim_pagamento,
        "dim_entrega": dim_entrega,
    }
    salvar(tabelas, destino)

    pedidos_na_fato = fato["id_pedido"].nunique()
    relatorio = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **log,
        "itens_na_fato": int(len(fato)),
        "pedidos_na_fato": int(pedidos_na_fato),
        "pedidos_sem_pagamento": int((fato.drop_duplicates("id_pedido")["id_pagamento"] == 0).sum()),
        "produtos_sem_categoria": int((dim_produto["categoria"] == "sem_categoria").sum()),
        "limite_outlier_prazo_dias_p98": limite_outlier,
        "itens_marcados_outlier_prazo": int(fato["prazo_outlier"].sum()),
        "percentual_pedidos_atrasados": round(
            float((fato.drop_duplicates("id_pedido")["dias_atraso"] > 0).mean() * 100), 2
        ),
        "chaves_orfas": checar_integridade(fato, tabelas),
        "linhas_por_tabela": {nome: int(len(df)) for nome, df in tabelas.items()},
    }
    with open(Path(destino) / "qualidade_etl.json", "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
    return relatorio


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL Olist -> modelo estrela (parquet)")
    parser.add_argument("--origem", default="olist_data", help="pasta com os CSVs da Olist")
    parser.add_argument("--destino", default="data", help="pasta onde salvar os parquets")
    args = parser.parse_args()
    print(json.dumps(executar(args.origem, args.destino), ensure_ascii=False, indent=2))
