"""Dashboard de apoio a decisão: Olist (marketplace brasileiro de e-commerce).

Lê os arquivos do modelo estrela gerados por etl/transformacao.py (pasta data/)
e apresenta indicadores, filtros e as visualizações de vendas, geografia,
logística e pagamentos.
"""
import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Dashboard Olist", page_icon="📦", layout="wide")

PASTA_DADOS = Path(os.environ.get("OLIST_DATA_DIR", Path(__file__).parent / "data"))
TABELAS = [
    "fato_pedidos", "dim_tempo", "dim_cliente", "dim_produto",
    "dim_vendedor", "dim_pagamento", "dim_entrega",
]
FAIXAS_PARCELAS = ["À vista (1x)", "2 a 5x", "6 a 10x", "Mais de 10x"]
COR = "#2563eb"
COR_ALERTA = "#dc2626"
MIN_PEDIDOS_UF = 50


# ----------------------------------------------------------------- utilidades
def brl(valor):
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl_compacto(valor):
    """Valor curto para caber no indicador (o valor completo fica na dica)."""
    if valor >= 1_000_000:
        return f"R$ {decimal(valor / 1_000_000, 2)} mi"
    if valor >= 1_000:
        return f"R$ {decimal(valor / 1_000, 1)} mil"
    return brl(valor)


def inteiro(valor):
    return f"{valor:,.0f}".replace(",", ".")


def decimal(valor, casas=1):
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def estilizar(fig, altura=380):
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=10), separators=",.")
    return fig


def justificativa(texto):
    st.caption(f"**Como apoia a decisão:** {texto}")


# ---------------------------------------------------------------------- dados
@st.cache_data(show_spinner="Carregando dados...")
def carregar_dados(pasta):
    pasta = Path(pasta)
    t = {nome: pd.read_parquet(pasta / f"{nome}.parquet") for nome in TABELAS}
    df = (
        t["fato_pedidos"]
        .merge(t["dim_tempo"], on="id_tempo", how="left")
        .merge(t["dim_cliente"][["id_cliente", "uf_cliente", "cidade_cliente"]], on="id_cliente", how="left")
        .merge(t["dim_produto"][["id_produto", "categoria"]], on="id_produto", how="left")
        .merge(t["dim_vendedor"][["id_vendedor", "uf_vendedor"]], on="id_vendedor", how="left")
        .merge(t["dim_pagamento"], on="id_pagamento", how="left")
        .merge(t["dim_entrega"], on="id_entrega", how="left")
    )
    df["categoria"] = df["categoria"].str.replace("_", " ").str.capitalize()
    return df


@st.cache_data
def carregar_tabela(nome, linhas=15):
    return pd.read_parquet(PASTA_DADOS / f"{nome}.parquet").head(linhas)


@st.cache_data
def carregar_qualidade():
    caminho = PASTA_DADOS / "qualidade_etl.json"
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return None


def agregar_pedidos(d):
    """Uma linha por pedido (indicadores de entrega e ticket são por pedido)."""
    return d.groupby("id_pedido", as_index=False).agg(
        receita=("receita", "sum"),
        prazo_entrega_dias=("prazo_entrega_dias", "first"),
        dias_atraso=("dias_atraso", "first"),
        prazo_outlier=("prazo_outlier", "first"),
        uf_cliente=("uf_cliente", "first"),
        tipo_pagamento=("tipo_pagamento", "first"),
        faixa_parcelas=("faixa_parcelas", "first"),
        ano_mes=("ano_mes", "first"),
    )


def calcular_kpis(d, pedidos):
    receita = float(d["receita"].sum())
    n_pedidos = int(len(pedidos))
    return {
        "receita": receita,
        "pedidos": n_pedidos,
        "itens": int(len(d)),
        "ticket": receita / n_pedidos if n_pedidos else 0.0,
        "prazo": float(pedidos["prazo_entrega_dias"].mean()) if n_pedidos else 0.0,
        "atraso": float((pedidos["dias_atraso"] > 0).mean() * 100) if n_pedidos else 0.0,
    }


# --------------------------------------------------------------------- início
if not all((PASTA_DADOS / f"{n}.parquet").exists() for n in TABELAS):
    st.title("Dashboard Olist")
    st.error("Os arquivos de dados ainda não foram gerados na pasta `data/`.")
    st.markdown(
        "Execute o ETL para criar o modelo estrela e recarregue a página:\n\n"
        "```bash\npython etl/transformacao.py --origem olist_data --destino data\n```"
    )
    st.stop()

base = carregar_dados(str(PASTA_DADOS))

# --------------------------------------------------------------------- filtros
st.sidebar.header("Filtros")
data_min, data_max = base["data"].min().date(), base["data"].max().date()
periodo = st.sidebar.date_input(
    "Período da compra", value=(data_min, data_max), min_value=data_min, max_value=data_max
)
if isinstance(periodo, (tuple, list)):
    inicio = periodo[0]
    fim = periodo[1] if len(periodo) == 2 else periodo[0]
else:
    inicio = fim = periodo
ufs = st.sidebar.multiselect("Estado do cliente (UF)", sorted(base["uf_cliente"].dropna().unique()))
categorias = st.sidebar.multiselect("Categoria do produto", sorted(base["categoria"].dropna().unique()))
st.sidebar.caption("Sem seleção, todos os estados e categorias são considerados.")
st.sidebar.divider()
st.sidebar.caption(
    "Fonte: Brazilian E-Commerce Public Dataset by Olist (Kaggle), licença CC BY-NC-SA 4.0. "
    "Apenas pedidos entregues."
)

mascara = (base["data"] >= pd.Timestamp(inicio)) & (base["data"] < pd.Timestamp(fim) + pd.Timedelta(days=1))
if ufs:
    mascara &= base["uf_cliente"].isin(ufs)
if categorias:
    mascara &= base["categoria"].isin(categorias)
d = base[mascara]
filtros_ativos = bool(ufs or categorias or inicio != data_min or fim != data_max)

# -------------------------------------------------------------------- cabeçalho
st.title("📦 Dashboard de decisão: Olist")
st.markdown(
    "**Pergunta central:** onde estão as oportunidades de venda e os riscos de atraso na entrega "
    "do marketplace? Use os filtros ao lado para recortar período, estado e categoria."
)

if d.empty:
    st.warning("Nenhum pedido encontrado com os filtros atuais. Ajuste a seleção na barra lateral.")
    st.stop()

pedidos = agregar_pedidos(d)
kpi = calcular_kpis(d, pedidos)
geral = calcular_kpis(base, agregar_pedidos(base))


def diferenca(chave, formato, inverso=False):
    """Variação em relação ao total sem filtros (só aparece com filtro ativo)."""
    if not filtros_ativos:
        return None, "normal"
    delta = kpi[chave] - geral[chave]
    return formato(delta), ("inverse" if inverso else "normal")


c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Receita total", brl_compacto(kpi["receita"]), border=True,
          help=f"{brl(kpi['receita'])} (soma de preço + frete dos itens entregues no recorte).")
c2.metric("Pedidos", inteiro(kpi["pedidos"]), border=True,
          help=f"{inteiro(kpi['itens'])} itens vendidos.")
delta, cor = diferenca("ticket", lambda v: f"{'+' if v >= 0 else '-'}{brl(abs(v))} vs. geral")
c3.metric("Ticket médio", brl(kpi["ticket"]), delta=delta, delta_color=cor, border=True,
          help="Receita total dividida pelo número de pedidos.")
delta, cor = diferenca("prazo", lambda v: f"{'+' if v >= 0 else '-'}{decimal(abs(v))} dias vs. geral", inverso=True)
c4.metric("Prazo médio de entrega", f"{decimal(kpi['prazo'])} dias", delta=delta, delta_color=cor, border=True,
          help="Dias entre a compra e a entrega ao cliente, por pedido.")
delta, cor = diferenca("atraso", lambda v: f"{'+' if v >= 0 else '-'}{decimal(abs(v))} p.p. vs. geral", inverso=True)
c5.metric("Entregas atrasadas", f"{decimal(kpi['atraso'])}%", delta=delta, delta_color=cor, border=True,
          help="Pedidos entregues depois da data estimada.")

# leitura rápida (calculada com os filtros atuais)
mensal = d.groupby("ano_mes")["receita"].sum()
por_categoria = d.groupby("categoria")["receita"].sum().sort_values(ascending=False)
por_uf = d.groupby("uf_cliente")["receita"].sum().sort_values(ascending=False)
atraso_uf = pedidos.groupby("uf_cliente").agg(
    pedidos=("id_pedido", "count"), atraso=("dias_atraso", lambda s: (s > 0).mean() * 100)
)
atraso_uf = atraso_uf[atraso_uf["pedidos"] >= MIN_PEDIDOS_UF].sort_values("atraso", ascending=False)
leitura = [
    f"Maior receita mensal: **{mensal.idxmax()}** ({brl(mensal.max())}).",
    f"Categoria líder em receita: **{por_categoria.index[0]}** "
    f"({decimal(por_categoria.iloc[0] / kpi['receita'] * 100)}% do total).",
    f"Estado líder em receita: **{por_uf.index[0]}** ({decimal(por_uf.iloc[0] / kpi['receita'] * 100)}% do total).",
]
if not atraso_uf.empty:
    leitura.append(
        f"Maior taxa de atraso (estados com {MIN_PEDIDOS_UF}+ pedidos): **{atraso_uf.index[0]}** "
        f"({decimal(atraso_uf['atraso'].iloc[0])}% dos pedidos)."
    )
st.info("**Leitura rápida**\n\n" + "\n".join(f"- {linha}" for linha in leitura))

# ------------------------------------------------------------------------ abas
aba_vendas, aba_geo, aba_log, aba_pag, aba_dados = st.tabs(
    ["Vendas", "Geografia", "Logística", "Pagamentos", "Dados e transformações"]
)

with aba_vendas:
    st.subheader("Receita total por mês")
    mensal_df = mensal.reset_index().sort_values("ano_mes")
    fig = px.line(mensal_df, x="ano_mes", y="receita", markers=True,
                  labels={"ano_mes": "Mês", "receita": "Receita (R$)"},
                  color_discrete_sequence=[COR])
    fig.update_traces(hovertemplate="%{x}<br>R$ %{y:,.2f}<extra></extra>")
    st.plotly_chart(estilizar(fig))
    justificativa("mostra picos e quedas de vendas ao longo do tempo (datas comemorativas, por exemplo), "
                  "ajudando a planejar o estoque dos vendedores parceiros e o calendário de campanhas. "
                  "Os meses nas pontas da série têm poucos pedidos no dataset.")

    st.subheader("Top 10 categorias de produto")
    ordem = st.radio("Ordenar por", ["Receita", "Itens vendidos"], horizontal=True, key="ordem_cat")
    if ordem == "Receita":
        top = d.groupby("categoria")["receita"].sum().nlargest(10).sort_values().rename("valor")
        rotulo = "Receita (R$)"
    else:
        top = d.groupby("categoria").size().nlargest(10).sort_values().rename("valor")
        rotulo = "Itens vendidos"
    fig = px.bar(top.reset_index(), x="valor", y="categoria", orientation="h",
                 labels={"categoria": "", "valor": rotulo}, color_discrete_sequence=[COR])
    st.plotly_chart(estilizar(fig, 420))
    justificativa("aponta as categorias que mais movimentam a plataforma, orientando o recrutamento de novos "
                  "vendedores nessas categorias e o destaque delas em promoções e na página inicial.")

with aba_geo:
    st.subheader("Top 10 estados por receita")
    top_uf = d.groupby("uf_cliente")["receita"].sum().nlargest(10).reset_index()
    top_uf["participação"] = top_uf["receita"] / kpi["receita"] * 100
    fig = px.bar(top_uf, x="uf_cliente", y="receita", text=top_uf["participação"].map(lambda v: f"{decimal(v)}%"),
                 labels={"uf_cliente": "Estado (UF)", "receita": "Receita (R$)"}, color_discrete_sequence=[COR])
    fig.update_traces(textposition="outside")
    st.plotly_chart(estilizar(fig))
    justificativa("mostra a concentração geográfica das vendas, apoiando decisões de expansão de centros de "
                  "distribuição e de campanhas regionais nos estados de maior potencial.")

    st.subheader("Vendas por estado do vendedor")
    vend_uf = d.groupby("uf_vendedor")["receita"].sum().nlargest(10).reset_index()
    fig = px.bar(vend_uf, x="uf_vendedor", y="receita",
                 labels={"uf_vendedor": "Estado do vendedor (UF)", "receita": "Receita (R$)"},
                 color_discrete_sequence=[COR])
    st.plotly_chart(estilizar(fig, 320))
    justificativa("compara de onde saem os produtos com para onde eles vão. A distância entre os dois "
                  "ajuda a localizar gargalos de frete e prazo.")

with aba_log:
    st.subheader("Distribuição do prazo de entrega")
    sem_outliers = pedidos[~pedidos["prazo_outlier"]]
    fig = px.histogram(sem_outliers, x="prazo_entrega_dias", nbins=30,
                       labels={"prazo_entrega_dias": "Dias entre compra e entrega"},
                       color_discrete_sequence=[COR])
    fig.update_layout(yaxis_title="Número de pedidos")
    fig.add_vline(x=kpi["prazo"], line_dash="dash", line_color=COR_ALERTA,
                  annotation_text=f"média de todos os pedidos: {decimal(kpi['prazo'])} dias")
    st.plotly_chart(estilizar(fig))
    justificativa("a entrega é um dos principais fatores de satisfação em e-commerce. O gráfico apoia a "
                  "negociação com transportadoras, a escolha de centros de distribuição e a definição de "
                  "prazos estimados mais realistas. O gráfico exclui os 2% de prazos mais longos (valores atípicos), "
                  "mas a linha tracejada mostra a média de todos os pedidos.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Atraso por mês")
        atraso_mes = (
            pedidos.groupby("ano_mes")["dias_atraso"].apply(lambda s: (s > 0).mean() * 100).reset_index()
            .rename(columns={"dias_atraso": "atraso"}).sort_values("ano_mes")
        )
        fig = px.line(atraso_mes, x="ano_mes", y="atraso", markers=True,
                      labels={"ano_mes": "Mês", "atraso": "% de pedidos atrasados"},
                      color_discrete_sequence=[COR_ALERTA])
        st.plotly_chart(estilizar(fig, 340))
        justificativa("mostra em quais meses a operação logística piora, normalmente nos picos de demanda.")
    with col_b:
        st.subheader(f"Atraso por estado (mín. {MIN_PEDIDOS_UF} pedidos)")
        if atraso_uf.empty:
            st.info("Poucos pedidos por estado no recorte atual.")
        else:
            piores = atraso_uf.head(10).reset_index().sort_values("atraso")
            fig = px.bar(piores, x="atraso", y="uf_cliente", orientation="h",
                         labels={"atraso": "% de pedidos atrasados", "uf_cliente": "Estado (UF)"},
                         color_discrete_sequence=[COR_ALERTA])
            st.plotly_chart(estilizar(fig, 340))
            justificativa("indica onde agir primeiro para reduzir atrasos, por exemplo renegociando frete "
                          "ou ajustando o prazo exibido ao cliente.")

with aba_pag:
    st.subheader("Formas de pagamento (por pedido)")
    formas = pedidos["tipo_pagamento"].value_counts().reset_index()
    formas.columns = ["tipo_pagamento", "pedidos"]
    formas["participação"] = formas["pedidos"] / formas["pedidos"].sum() * 100
    fig = px.bar(formas, x="tipo_pagamento", y="pedidos",
                 text=formas["participação"].map(lambda v: f"{decimal(v)}%"),
                 labels={"tipo_pagamento": "Forma de pagamento", "pedidos": "Número de pedidos"},
                 color_discrete_sequence=[COR])
    fig.update_traces(textposition="outside")
    st.plotly_chart(estilizar(fig))
    justificativa("mostra a preferência de pagamento do cliente brasileiro (cartão de crédito x boleto, "
                  "por exemplo), orientando a prioridade no checkout e a negociação de taxas com adquirentes. "
                  "Quando o pedido tem mais de um pagamento, vale o de maior valor.")

    st.subheader("Parcelamento nos pedidos pagos com cartão de crédito")
    cartao = pedidos[pedidos["tipo_pagamento"] == "Cartão de crédito"]
    if cartao.empty:
        st.info("Nenhum pedido com cartão de crédito no recorte atual.")
    else:
        parcelas = cartao["faixa_parcelas"].value_counts().reindex(FAIXAS_PARCELAS).fillna(0).reset_index()
        parcelas.columns = ["faixa_parcelas", "pedidos"]
        fig = px.bar(parcelas, x="faixa_parcelas", y="pedidos",
                     labels={"faixa_parcelas": "Parcelas", "pedidos": "Número de pedidos"},
                     color_discrete_sequence=[COR])
        st.plotly_chart(estilizar(fig, 320))
        justificativa("revela o quanto o parcelamento sustenta as vendas, base para campanhas de "
                      "parcelamento sem juros e para o planejamento de fluxo de caixa dos vendedores.")

with aba_dados:
    st.subheader("Como os dados foram transformados")
    st.markdown(
        "Os 6 arquivos CSV da Olist (pedidos, itens, clientes, produtos, vendedores e pagamentos) passam por "
        "um ETL em Python (`etl/transformacao.py`) que filtra pedidos entregues, trata nulos, deriva "
        "métricas (receita, prazo de entrega, dias de atraso) e organiza tudo em um **modelo estrela**: "
        "uma tabela-fato no grão de item de pedido e seis dimensões."
    )
    st.graphviz_chart(
        """
        digraph estrela {
          rankdir=LR; nodesep=0.35;
          node [shape=box, style="rounded,filled", fillcolor="#e0e7ff", color="#6366f1", fontname="Helvetica"];
          fato [label="fato_pedidos\\n(item de pedido)", fillcolor="#c7d2fe", fontsize=14];
          dim_tempo -> fato; dim_cliente -> fato; dim_produto -> fato;
          dim_vendedor -> fato; dim_pagamento -> fato; dim_entrega -> fato;
        }
        """
    )
    qualidade = carregar_qualidade()
    if qualidade:
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            st.markdown("**Linhas por tabela**")
            st.dataframe(
                pd.DataFrame(qualidade["linhas_por_tabela"].items(), columns=["tabela", "linhas"]),
                hide_index=True,
            )
        with col_q2:
            st.markdown("**Checagens de qualidade do ETL**")
            checagens = {
                "Pedidos no arquivo original": qualidade["pedidos_total"],
                "Pedidos entregues": qualidade["pedidos_entregues"],
                "Entregues sem data de entrega (removidos)": qualidade["entregues_sem_data_de_entrega_removidos"],
                "Pedidos na tabela-fato": qualidade["pedidos_na_fato"],
                "Pedidos sem pagamento registrado": qualidade["pedidos_sem_pagamento"],
                "Produtos sem categoria": qualidade["produtos_sem_categoria"],
                "Itens marcados como prazo atípico (acima do P98)": qualidade["itens_marcados_outlier_prazo"],
                "Chaves órfãs na fato (esperado 0)": sum(qualidade["chaves_orfas"].values()),
            }
            st.dataframe(
                pd.DataFrame({"checagem": checagens.keys(), "valor": [inteiro(v) for v in checagens.values()]}),
                hide_index=True,
            )
        st.caption(f"ETL executado em {qualidade['gerado_em']}.")
    st.markdown("**Amostra da tabela-fato**")
    st.dataframe(carregar_tabela("fato_pedidos"), hide_index=True)
    st.download_button(
        "Baixar pedidos do recorte atual (CSV)",
        data=pedidos.to_csv(index=False).encode("utf-8"),
        file_name="pedidos_recorte.csv",
        mime="text/csv",
    )
