"""Dados sinteticos no formato da Olist, usados apenas nos testes automatizados.

Nao sao dados reais: servem para verificar a logica do ETL e do dashboard sem
precisar baixar o dataset do Kaggle. Os casos de borda (ids com prefixo
"edge_") tem resultado conhecido e sao conferidos em test_transformacao.py.
"""
from pathlib import Path

import numpy as np
import pandas as pd

UFS = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "PE", "CE", "ES", "PA", "MT", "MS"]
PESOS_UF = np.array([40, 13, 12, 6, 6, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1], dtype=float)
CATEGORIAS = [
    "cama_mesa_banho", "beleza_saude", "esporte_lazer", "moveis_decoracao",
    "informatica_acessorios", "utilidades_domesticas", "relogios_presentes",
    "telefonia", "brinquedos", "automotivo", "perfumaria", "ferramentas_jardim",
]


def gerar_csvs(pasta, n_pedidos=500, seed=7):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    n_clientes = n_pedidos + 10
    clientes = pd.DataFrame(
        {
            "customer_id": [f"cli_{i:05d}" for i in range(n_clientes)],
            "customer_unique_id": [f"uni_{i // 2:05d}" for i in range(n_clientes)],
            "customer_zip_code_prefix": rng.integers(1000, 99999, n_clientes),
            "customer_city": rng.choice(["sao paulo", "rio de janeiro", "belo horizonte", "curitiba"], n_clientes),
            "customer_state": rng.choice(UFS, n_clientes, p=PESOS_UF / PESOS_UF.sum()),
        }
    )

    produtos = pd.DataFrame(
        {
            "product_id": [f"prod_{i:04d}" for i in range(300)],
            "product_category_name": rng.choice(CATEGORIAS + [None], 300),
            "product_name_lenght": rng.integers(20, 60, 300),
            "product_description_lenght": rng.integers(100, 900, 300),
            "product_photos_qty": rng.integers(1, 6, 300),
            "product_weight_g": rng.integers(100, 5000, 300),
            "product_length_cm": rng.integers(10, 60, 300),
            "product_height_cm": rng.integers(5, 40, 300),
            "product_width_cm": rng.integers(10, 50, 300),
        }
    )
    vendedores = pd.DataFrame(
        {
            "seller_id": [f"vend_{i:03d}" for i in range(80)],
            "seller_zip_code_prefix": rng.integers(1000, 99999, 80),
            "seller_city": rng.choice(["campinas", "santos", "niteroi", "joinville"], 80),
            "seller_state": rng.choice(UFS, 80, p=PESOS_UF / PESOS_UF.sum()),
        }
    )

    inicio = pd.Timestamp("2017-01-01")
    compras = [
        inicio + pd.Timedelta(days=int(rng.integers(0, 600)), hours=int(rng.integers(0, 24)),
                              minutes=int(rng.integers(0, 60)))
        for _ in range(n_pedidos)
    ]
    status = rng.choice(["delivered", "canceled", "shipped"], n_pedidos, p=[0.95, 0.03, 0.02])
    prazos = np.clip(rng.lognormal(2.3, 0.55, n_pedidos), 1, 120).astype(int)
    estimados = rng.integers(10, 40, n_pedidos)

    pedidos = pd.DataFrame(
        {
            "order_id": [f"ped_{i:05d}" for i in range(n_pedidos)],
            "customer_id": clientes["customer_id"][:n_pedidos].to_numpy(),
            "order_status": status,
            "order_purchase_timestamp": compras,
            "order_approved_at": [c + pd.Timedelta(hours=1) for c in compras],
            "order_delivered_carrier_date": [c + pd.Timedelta(days=2) for c in compras],
            "order_delivered_customer_date": [
                c + pd.Timedelta(days=int(p), hours=3) if s == "delivered" else pd.NaT
                for c, p, s in zip(compras, prazos, status)
            ],
            "order_estimated_delivery_date": [
                (c + pd.Timedelta(days=int(e))).normalize() for c, e in zip(compras, estimados)
            ],
        }
    )

    itens, pagamentos = [], []
    for oid in pedidos["order_id"]:
        for seq in range(1, int(rng.choice([1, 1, 1, 2, 3])) + 1):
            itens.append(
                {
                    "order_id": oid, "order_item_id": seq,
                    "product_id": f"prod_{int(rng.integers(0, 300)):04d}",
                    "seller_id": f"vend_{int(rng.integers(0, 80)):03d}",
                    "shipping_limit_date": "2017-06-01 10:00:00",
                    "price": round(float(rng.uniform(10, 400)), 2),
                    "freight_value": round(float(rng.uniform(5, 50)), 2),
                }
            )
        pagamentos.append(
            {
                "order_id": oid, "payment_sequential": 1,
                "payment_type": rng.choice(["credit_card", "boleto", "voucher", "debit_card"], p=[0.74, 0.19, 0.05, 0.02]),
                "payment_installments": int(rng.choice([1, 1, 2, 3, 5, 8, 10, 12])),
                "payment_value": round(float(rng.uniform(30, 600)), 2),
            }
        )
    itens = pd.DataFrame(itens)
    pagamentos = pd.DataFrame(pagamentos)

    # ---- casos de borda com resultado conhecido ----
    def pedido_borda(oid, status_, compra, entrega, estimada, cliente):
        return {
            "order_id": oid, "customer_id": cliente, "order_status": status_,
            "order_purchase_timestamp": pd.Timestamp(compra),
            "order_approved_at": pd.Timestamp(compra),
            "order_delivered_carrier_date": pd.Timestamp(compra),
            "order_delivered_customer_date": pd.Timestamp(entrega) if entrega else pd.NaT,
            "order_estimated_delivery_date": pd.Timestamp(estimada),
        }

    clientes_borda = clientes["customer_id"][n_pedidos:].tolist()
    extras = [
        pedido_borda("edge_cancelado", "canceled", "2018-03-01 10:00", None, "2018-03-10", clientes_borda[0]),
        pedido_borda("edge_sem_data", "delivered", "2018-03-01 10:00", None, "2018-03-10", clientes_borda[1]),
        pedido_borda("edge_atrasado", "delivered", "2018-03-01 10:00", "2018-03-13 15:00", "2018-03-10", clientes_borda[2]),
        pedido_borda("edge_mesmo_dia", "delivered", "2018-03-01 10:00", "2018-03-10 09:00", "2018-03-10", clientes_borda[3]),
        pedido_borda("edge_dois_itens", "delivered", "2018-03-02 11:00", "2018-03-08 12:00", "2018-03-15", clientes_borda[4]),
        pedido_borda("edge_dois_pagamentos", "delivered", "2018-03-02 11:00", "2018-03-08 12:00", "2018-03-15", clientes_borda[5]),
        pedido_borda("edge_sem_pagamento", "delivered", "2018-03-02 11:00", "2018-03-08 12:00", "2018-03-15", clientes_borda[6]),
    ]
    pedidos = pd.concat([pedidos, pd.DataFrame(extras)], ignore_index=True)

    def item(oid, seq, prod, vend, preco, frete):
        return {
            "order_id": oid, "order_item_id": seq, "product_id": prod, "seller_id": vend,
            "shipping_limit_date": "2018-03-03 10:00:00", "price": preco, "freight_value": frete,
        }

    itens = pd.concat(
        [
            itens,
            pd.DataFrame(
                [
                    item("edge_cancelado", 1, "prod_0001", "vend_001", 50.0, 5.0),
                    item("edge_sem_data", 1, "prod_0001", "vend_001", 50.0, 5.0),
                    item("edge_atrasado", 1, "prod_0002", "vend_002", 100.0, 10.0),
                    item("edge_mesmo_dia", 1, "prod_0002", "vend_002", 100.0, 10.0),
                    item("edge_dois_itens", 1, "prod_0003", "vend_003", 10.0, 5.0),
                    item("edge_dois_itens", 2, "prod_0004", "vend_004", 20.0, 6.0),
                    item("edge_dois_pagamentos", 1, "prod_0005", "vend_005", 80.0, 20.0),
                    item("edge_sem_pagamento", 1, "prod_0006", "vend_006", 30.0, 8.0),
                ]
            ),
        ],
        ignore_index=True,
    )
    pagamentos = pd.concat(
        [
            pagamentos,
            pd.DataFrame(
                [
                    {"order_id": "edge_atrasado", "payment_sequential": 1, "payment_type": "boleto", "payment_installments": 1, "payment_value": 110.0},
                    {"order_id": "edge_mesmo_dia", "payment_sequential": 1, "payment_type": "boleto", "payment_installments": 1, "payment_value": 110.0},
                    {"order_id": "edge_dois_itens", "payment_sequential": 1, "payment_type": "debit_card", "payment_installments": 1, "payment_value": 41.0},
                    {"order_id": "edge_dois_pagamentos", "payment_sequential": 1, "payment_type": "voucher", "payment_installments": 1, "payment_value": 10.0},
                    {"order_id": "edge_dois_pagamentos", "payment_sequential": 2, "payment_type": "credit_card", "payment_installments": 3, "payment_value": 90.0},
                ]
            ),
        ],
        ignore_index=True,
    )

    for nome, df in {
        "olist_orders_dataset.csv": pedidos,
        "olist_order_items_dataset.csv": itens,
        "olist_customers_dataset.csv": clientes,
        "olist_products_dataset.csv": produtos,
        "olist_sellers_dataset.csv": vendedores,
        "olist_order_payments_dataset.csv": pagamentos,
    }.items():
        df.to_csv(pasta / nome, index=False)
    return pasta
