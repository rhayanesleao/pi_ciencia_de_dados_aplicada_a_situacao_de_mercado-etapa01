"""Testes do ETL (modelo estrela). Rodar com: pytest -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from etl import transformacao  # noqa: E402
from fixtures import gerar_csvs  # noqa: E402


@pytest.fixture(scope="module")
def saida(tmp_path_factory):
    base = tmp_path_factory.mktemp("olist")
    origem, destino = base / "csv", base / "parquet"
    gerar_csvs(origem, n_pedidos=300)
    relatorio = transformacao.executar(origem, destino)
    ler = lambda nome: pd.read_parquet(destino / f"{nome}.parquet")  # noqa: E731
    return {"relatorio": relatorio, "fato": ler("fato_pedidos"), "dim_pagamento": ler("dim_pagamento"),
            "dim_entrega": ler("dim_entrega"), "dim_tempo": ler("dim_tempo")}


def linhas(saida, pedido):
    return saida["fato"][saida["fato"]["id_pedido"] == pedido]


def test_somente_pedidos_entregues_com_data(saida):
    assert linhas(saida, "edge_cancelado").empty
    assert linhas(saida, "edge_sem_data").empty
    assert saida["relatorio"]["entregues_sem_data_de_entrega_removidos"] >= 1


def test_atraso_conta_por_dia_do_calendario(saida):
    atrasado = linhas(saida, "edge_atrasado").iloc[0]
    assert atrasado["dias_atraso"] == 3
    assert atrasado["prazo_entrega_dias"] == 12
    mesmo_dia = linhas(saida, "edge_mesmo_dia").iloc[0]
    assert mesmo_dia["dias_atraso"] == 0


def test_receita_e_grao_de_item(saida):
    dois = linhas(saida, "edge_dois_itens").sort_values("id_item")
    assert list(dois["receita"]) == [15.0, 26.0]
    assert len(dois) == 2


def test_pagamento_principal_nao_duplica_itens(saida):
    linha = linhas(saida, "edge_dois_pagamentos")
    assert len(linha) == 1
    dp = saida["dim_pagamento"].set_index("id_pagamento")
    registro = dp.loc[linha.iloc[0]["id_pagamento"]]
    assert registro["tipo_pagamento"] == "Cartão de crédito"
    assert registro["faixa_parcelas"] == "2 a 5x"


def test_pedido_sem_pagamento_recebe_chave_zero(saida):
    assert linhas(saida, "edge_sem_pagamento").iloc[0]["id_pagamento"] == 0


def test_integridade_referencial(saida):
    assert all(v == 0 for v in saida["relatorio"]["chaves_orfas"].values())


def test_fato_sem_duplicidade_de_chave(saida):
    assert not saida["fato"].duplicated(["id_pedido", "id_item"]).any()


def test_dim_entrega_cobre_todas_as_combinacoes(saida):
    assert len(saida["dim_entrega"]) == 8
    assert saida["fato"]["id_entrega"].notna().all()


def test_dim_tempo_calendario_continuo(saida):
    datas = saida["dim_tempo"]["data"]
    assert (datas.diff().dropna() == pd.Timedelta(days=1)).all()
