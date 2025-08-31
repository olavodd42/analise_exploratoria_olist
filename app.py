import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Dashboard Olist", page_icon="📦", layout="wide")

# =============== UTIL ===============
def br_money(x: float) -> str:
    if pd.isna(x): return "R$ 0,00"
    # Formato "R$ 1.234,56"
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def kpi_card(col, label, value):
    col.metric(label, value)

# =============== LOAD DATA ===============
@st.cache_data
def load_orders_pay_customers():
    orders    = pd.read_csv("data/olist_orders_dataset.csv")
    payments  = pd.read_csv("data/olist_order_payments_dataset.csv")
    customers = pd.read_csv("data/olist_customers_dataset.csv")

    # Somar pagamentos por pedido (valor total real)
    pay_agg = (payments.groupby("order_id", as_index=False)
               .agg(payment_value=("payment_value", "sum")))

    base = (orders
            .merge(pay_agg, on="order_id", how="left")
            .merge(customers[["customer_id","customer_unique_id","customer_city","customer_state"]],
                   on="customer_id", how="left"))

    # Datas
    date_cols = ["order_purchase_timestamp", "order_approved_at",
                 "order_delivered_carrier_date", "order_delivered_customer_date",
                 "order_estimated_delivery_date"]
    for c in date_cols:
        if c in base.columns:
            base[c] = pd.to_datetime(base[c], errors="coerce")

    return base

@st.cache_data
def load_items_products():
    try:
        items    = pd.read_csv("data/olist_order_items_dataset.csv")
        products = pd.read_csv("data/olist_products_dataset.csv")
        df_ip = items.merge(products, on="product_id", how="left")
        # Receita aproximada por item = price + freight_value
        df_ip["revenue_item"] = df_ip["price"].fillna(0) + df_ip["freight_value"].fillna(0)
        return df_ip
    except Exception:
        return None

@st.cache_data
def load_reviews():
    try:
        reviews = pd.read_csv("data/olist_order_reviews_dataset.csv")
        # Garantir tipos
        reviews["review_score"] = pd.to_numeric(reviews["review_score"], errors="coerce")
        reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"], errors="coerce")
        return reviews
    except Exception:
        return None

@st.cache_data
def load_rfm():
    # Caso você tenha exportado RFM em outputs/rfm_table.csv a partir do notebook
    try:
        rfm = pd.read_csv("outputs/rfm_table.csv")
        return rfm
    except Exception:
        return None

df = load_orders_pay_customers()
df_ip = load_items_products()
df_rev = load_reviews()
rfm = load_rfm()

# =============== SIDEBAR (Filtros) ===============
st.sidebar.header("Filtros")
# Intervalo de datas
min_date = pd.to_datetime(df["order_purchase_timestamp"]).min()
max_date = pd.to_datetime(df["order_purchase_timestamp"]).max()
date_range = st.sidebar.date_input(
    "Período (data de compra)",
    value=(min_date.date() if pd.notna(min_date) else datetime(2016,1,1).date(),
           max_date.date() if pd.notna(max_date) else datetime(2018,12,31).date()),
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start_date, end_date = min_date, max_date

# Filtro por UF
ufs_all = sorted(df["customer_state"].dropna().unique().tolist())
ufs = st.sidebar.multiselect("Estados (UF)", ufs_all, default=ufs_all)

# Aplicar filtros
mask = (
    (df["order_purchase_timestamp"].between(start_date, end_date)) &
    (df["customer_state"].isin(ufs))
)
df_f = df.loc[mask].copy()

# =============== HEADER & KPIs ===============
st.title("📊 Dashboard Olist — Análise de Marketing")

col1, col2, col3, col4 = st.columns(4)
total_pedidos = df_f["order_id"].nunique()
faturamento = df_f["payment_value"].sum()
ticket = faturamento / total_pedidos if total_pedidos > 0 else 0
# % entregues no prazo (estimado >= entregue)
if {"order_delivered_customer_date","order_estimated_delivery_date"}.issubset(df_f.columns):
    tmp = df_f.dropna(subset=["order_delivered_customer_date","order_estimated_delivery_date"]).copy()
    pct_prazo = (tmp["order_estimated_delivery_date"] >= tmp["order_delivered_customer_date"]).mean()*100 if len(tmp) else np.nan
else:
    pct_prazo = np.nan

kpi_card(col1, "Pedidos", f"{total_pedidos:,}".replace(",", "."))
kpi_card(col2, "Faturamento", br_money(faturamento))
kpi_card(col3, "Ticket Médio", br_money(ticket))
kpi_card(col4, "% Entregue no Prazo", f"{pct_prazo:.1f}%" if pd.notna(pct_prazo) else "—")

st.caption(f"Período: {start_date.date()} → {end_date.date()} | UFs: {', '.join(ufs) if ufs else '—'}")

# =============== ABAS ===============
tab_geo, tab_time, tab_cat, tab_sat, tab_rfm, tab_data = st.tabs(
    ["🌍 Geografia", "⏱ Tempo", "🛍 Categorias", "⭐ Satisfação", "🔎 RFM", "🗂 Dados & Downloads"]
)

# ---- GEOGRAFIA ----
with tab_geo:
    st.subheader("Ticket médio por UF")
    if "customer_state" in df_f.columns:
        ticket_uf = (df_f.groupby("customer_state", as_index=False)
                     .agg(pedidos=("order_id","nunique"),
                          faturamento=("payment_value","sum")))
        ticket_uf["ticket_medio"] = ticket_uf["faturamento"] / ticket_uf["pedidos"]
        ticket_uf = ticket_uf.sort_values("ticket_medio", ascending=False)

        st.dataframe(ticket_uf.assign(
            faturamento=lambda d: d["faturamento"].map(br_money),
            ticket_medio=lambda d: d["ticket_medio"].map(br_money)
        ))

        st.bar_chart(ticket_uf.set_index("customer_state")["ticket_medio"])
    else:
        st.warning("Coluna `customer_state` indisponível no DataFrame filtrado.")

# ---- TEMPO ----
with tab_time:
    st.subheader("Evolução de pedidos e faturamento (mensal)")
    if "order_purchase_timestamp" in df_f.columns:
        df_f["year_month"] = df_f["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
        by_month = df_f.groupby("year_month").agg(
            pedidos=("order_id","nunique"),
            faturamento=("payment_value","sum")
        ).reset_index()

        c1, c2 = st.columns(2)
        with c1:
            st.line_chart(by_month.set_index("year_month")["pedidos"])
        with c2:
            st.line_chart(by_month.set_index("year_month")["faturamento"])
        st.dataframe(by_month.assign(
            faturamento=lambda d: d["faturamento"].map(br_money)
        ))
    else:
        st.warning("Sem coluna de data de compra para análise temporal.")

# ---- CATEGORIAS ----
with tab_cat:
    st.subheader("Top categorias por faturamento aproximado")
    if df_ip is not None:
        # Juntar com pedidos filtrados (para respeitar data/UF)
        ords_keep = df_f[["order_id"]].drop_duplicates()
        ip_f = df_ip.merge(ords_keep, on="order_id", how="inner")

        fat_cat = (ip_f.groupby("product_category_name", as_index=False)
                   .agg(faturamento=("revenue_item","sum"),
                        pedidos=("order_id","nunique")))
        fat_cat = fat_cat.sort_values("faturamento", ascending=False)
        top = st.slider("Top N categorias", 5, 25, 15)
        top_cat = fat_cat.head(top)

        st.bar_chart(top_cat.set_index("product_category_name")["faturamento"])
        st.dataframe(top_cat.assign(
            faturamento=lambda d: d["faturamento"].map(br_money)
        ))
    else:
        st.info("Para ver categorias, coloque `olist_order_items_dataset.csv` e `olist_products_dataset.csv` em `data/`.")

# ---- SATISFAÇÃO ----
with tab_sat:
    st.subheader("Atraso de entrega × Nota de review")
    if df_rev is not None:
        # Preparar atraso de entrega a partir de df (filtrado)
        cols_needed = {"order_id","order_delivered_customer_date","order_estimated_delivery_date"}
        if cols_needed.issubset(df_f.columns):
            tmp = df_f[list(cols_needed)].copy()
            tmp = tmp.merge(df_rev[["order_id","review_score"]], on="order_id", how="left")
            tmp = tmp.dropna(subset=["order_delivered_customer_date","order_estimated_delivery_date","review_score"])
            tmp["delay_days"] = (tmp["order_delivered_customer_date"] - tmp["order_estimated_delivery_date"]).dt.days

            rel = (tmp.groupby("review_score", as_index=False)
                   .agg(qtd=("order_id","count"),
                        delay_medio=("delay_days","mean")))
            st.dataframe(rel)

            # Histogramas simples com Streamlit (sem seaborn)
            st.write("Distribuição do atraso (dias)")
            st.bar_chart(tmp["delay_days"].value_counts().sort_index())

            st.write("Quantidade por nota de review")
            st.bar_chart(tmp["review_score"].value_counts().sort_index())
        else:
            st.warning("Não há colunas de entrega/estimativa no DataFrame filtrado.")
    else:
        st.info("Para satisfação, coloque `olist_order_reviews_dataset.csv` em `data/`.")

# ---- RFM ----
with tab_rfm:
    st.subheader("Segmentação RFM")
    if rfm is not None and not rfm.empty:
        # Aceita qualquer esquema, mas tenta achar colunas padrão:
        seg_col = "Segment" if "Segment" in rfm.columns else None
        if seg_col:
            counts = rfm[seg_col].value_counts().sort_values(ascending=False)
            st.bar_chart(counts)
        st.dataframe(rfm.head(50))
        st.download_button("Baixar RFM (CSV)", rfm.to_csv(index=False).encode("utf-8"), "rfm_table.csv", "text/csv")
    else:
        st.info("Exporte a tabela RFM do notebook para `outputs/rfm_table.csv` para habilitar esta aba.")

# ---- DADOS & DOWNLOADS ----
with tab_data:
    st.subheader("Dados filtrados")
    st.dataframe(df_f.head(200))
    st.download_button("Baixar base filtrada (CSV)", df_f.to_csv(index=False).encode("utf-8"), "base_filtrada.csv", "text/csv")

    if df_ip is not None:
        st.subheader("Order Items + Products (amostra)")
        st.dataframe(df_ip.head(200))
