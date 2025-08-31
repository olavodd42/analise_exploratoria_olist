# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import altair as alt
import pydeck as pdk

# =============== UTIL ===============
def br_money(x: float) -> str:
    if pd.isna(x): return "R$ 0,00"
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def safe_div(a, b):
    return float(a) / float(b) if (pd.notna(a) and pd.notna(b) and float(b) != 0.0) else 0.0

def as_datetime(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

def remove_outliers(df, col, method="IQR", p=0.99):
    s = df[col].dropna()
    if len(s) == 0:
        return df
    if method == "IQR":
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        high = q3 + 1.5*iqr
        low  = q1 - 1.5*iqr
    else:  # percentil
        low, high = s.quantile(1-p), s.quantile(p)
    return df[(df[col].isna()) | ((df[col] >= low) & (df[col] <= high))]

# Centroides aproximados das UFs (lat, lon)
UF_CENTROIDS = {
    "AC": (-9.0238, -70.8120), "AL": (-9.5713, -36.7820), "AM": (-3.4168, -65.8561),
    "AP": ( 0.9016, -52.0023), "BA": (-12.5797, -41.7007), "CE": (-5.3265, -39.7150),
    "DF": (-15.7998, -47.8645), "ES": (-19.1834, -40.3089), "GO": (-15.8270, -49.8362),
    "MA": (-5.1187, -45.1070), "MG": (-18.5122, -44.5550), "MS": (-20.7722, -54.7852),
    "MT": (-12.6819, -55.6370), "PA": (-2.1970, -52.0048), "PB": (-7.1219, -36.7247),
    "PE": (-8.8137, -36.9541), "PI": (-7.7183, -42.7289), "PR": (-24.4842, -51.8149),
    "RJ": (-22.2763, -42.4194), "RN": (-5.7842, -36.6296), "RO": (-10.9340, -62.8278),
    "RR": ( 1.9981, -61.3266), "RS": (-30.0346, -53.0925), "SC": (-27.2423, -50.2189),
    "SE": (-10.5741, -37.3857), "SP": (-22.3510, -48.4942), "TO": (-10.1753, -48.2982),
}

# =============== LOAD DATA ===============
@st.cache_data
def load_orders_pay_customers():
    orders    = pd.read_csv("data/olist_orders_dataset.csv")
    payments  = pd.read_csv("data/olist_order_payments_dataset.csv")
    customers = pd.read_csv("data/olist_customers_dataset.csv")

    pay_agg = (payments.groupby("order_id", as_index=False)
               .agg(payment_value=("payment_value", "sum"),
                    payment_types=("payment_type", lambda x: list(x))))

    base = (orders
            .merge(pay_agg, on="order_id", how="left")
            .merge(customers[["customer_id","customer_unique_id","customer_city","customer_state"]],
                   on="customer_id", how="left"))

    date_cols = ["order_purchase_timestamp","order_approved_at",
                 "order_delivered_carrier_date","order_delivered_customer_date",
                 "order_estimated_delivery_date"]
    base = as_datetime(base, date_cols)
    return base

@st.cache_data
def load_items_products():
    try:
        items    = pd.read_csv("data/olist_order_items_dataset.csv")
        products = pd.read_csv("data/olist_products_dataset.csv")
        df_ip = items.merge(products, on="product_id", how="left")
        df_ip["revenue_item"] = df_ip["price"].fillna(0) + df_ip["freight_value"].fillna(0)
        return df_ip
    except Exception:
        return None

@st.cache_data
def load_reviews():
    try:
        reviews = pd.read_csv("data/olist_order_reviews_dataset.csv")
        reviews["review_score"] = pd.to_numeric(reviews["review_score"], errors="coerce")
        reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"], errors="coerce")
        return reviews
    except Exception:
        return None

@st.cache_data
def load_rfm():
    try:
        return pd.read_csv("outputs/rfm_table.csv")
    except Exception:
        return None

df    = load_orders_pay_customers()
df_ip = load_items_products()
df_rev= load_reviews()
rfm   = load_rfm()

st.set_page_config(layout="wide")
# =============== SIDEBAR (Filtros) ===============
st.sidebar.header("Filtros")
min_date = pd.to_datetime(df["order_purchase_timestamp"]).min()
max_date = pd.to_datetime(df["order_purchase_timestamp"]).max()
date_range = st.sidebar.date_input(
    "Período (data de compra)",
    value=(min_date.date() if pd.notna(min_date) else datetime(2016,1,1).date(),
           max_date.date() if pd.notna(max_date) else datetime(2018,12,31).date()),
)
start_date, end_date = (pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])) if isinstance(date_range, tuple) else (min_date, max_date)

ufs_all = sorted(df["customer_state"].dropna().unique().tolist())
ufs = st.sidebar.multiselect("Estados (UF)", ufs_all, default=ufs_all)

# Tipos de pagamento
try:
    payments_raw = pd.read_csv("data/olist_order_payments_dataset.csv")
    ptypes_all = sorted(payments_raw["payment_type"].dropna().unique().tolist())
except Exception:
    ptypes_all = []
ptypes = st.sidebar.multiselect("Tipos de pagamento", ptypes_all, default=ptypes_all)

# Outliers
st.sidebar.markdown("**Tratamento de outliers (payment_value)**")
rm_out = st.sidebar.checkbox("Remover outliers", value=False)
method = st.sidebar.radio("Método", ["IQR", "Percentil 99%"], horizontal=True)
min_ticket = st.sidebar.number_input("Valor mínimo do pedido (R$)", min_value=0.0, value=0.0, step=10.0)

# Aplicar filtros base
mask = (
    df["order_purchase_timestamp"].between(start_date, end_date) &
    df["customer_state"].isin(ufs) &
    (df["payment_value"].fillna(0) >= min_ticket)
)
df_f = df.loc[mask].copy()

# Filtrar por tipos de pagamento
if ptypes:
    df_f = df_f[df_f["payment_types"].apply(lambda lst: any(p in lst for p in ptypes) if isinstance(lst, list) else False)]

# Remover outliers se marcado
if rm_out and "payment_value" in df_f.columns:
    df_f = remove_outliers(df_f, "payment_value", method="IQR" if method=="IQR" else "PCTL", p=0.99)

# =============== HEADER & KPIs ===============
st.title("📊 Dashboard Olist — Análise de Marketing")

col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
total_pedidos = df_f["order_id"].nunique()
faturamento = df_f["payment_value"].sum()
ticket = safe_div(faturamento, total_pedidos)

if {"order_delivered_customer_date","order_estimated_delivery_date"}.issubset(df_f.columns):
    tmp = df_f.dropna(subset=["order_delivered_customer_date","order_estimated_delivery_date"])
    pct_prazo = (tmp["order_estimated_delivery_date"] >= tmp["order_delivered_customer_date"]).mean()*100 if len(tmp) else np.nan
else:
    pct_prazo = np.nan

col1.metric("Pedidos", f"{total_pedidos:,}".replace(",", "."))
col2.metric("Faturamento", br_money(faturamento))
col3.metric("Ticket Médio", br_money(ticket))
col4.metric("% Entregue no Prazo", f"{pct_prazo:.1f}%" if pd.notna(pct_prazo) else "—")

st.caption(f"Período: {start_date.date()} → {end_date.date()} | UFs: {', '.join(ufs) if ufs else '—'} | Pagamento: {', '.join(ptypes) if ptypes else 'todos'} | Outliers: {'removidos' if rm_out else 'mantidos'}")

# =============== ABAS ===============
tab_geo, tab_time, tab_cat, tab_sat, tab_rfm, tab_data = st.tabs(
    ["🌍 Geografia", "⏱ Tempo", "🛍 Categorias", "⭐ Satisfação", "🔎 RFM", "🗂 Dados & Downloads"]
)

# ---- GEOGRAFIA ----
with tab_geo:
    st.subheader("Ticket médio por UF (tabela + mapa)")

    if "customer_state" in df_f.columns and total_pedidos > 0:
        ticket_uf = (df_f.groupby("customer_state", as_index=False)
                     .agg(pedidos=("order_id","nunique"),
                          faturamento=("payment_value","sum")))
        ticket_uf["ticket_medio"] = ticket_uf["faturamento"] / ticket_uf["pedidos"]

        st.dataframe(ticket_uf.sort_values("ticket_medio", ascending=False).assign(
            faturamento=lambda d: d["faturamento"].map(br_money),
            ticket_medio=lambda d: d["ticket_medio"].map(br_money)
        ))

        # --- monta DF para o mapa a partir dos centróides já definidos ---
        rows = []
        for _, r in ticket_uf.iterrows():
            uf = r["customer_state"]
            if pd.notna(r["ticket_medio"]) and uf in UF_CENTROIDS:
                lat, lon = UF_CENTROIDS[uf]
                rows.append({"uf": uf, "lat": float(lat), "lon": float(lon),
                             "ticket_medio": float(r["ticket_medio"]),
                             "pedidos": int(r["pedidos"])})
        mapdf = pd.DataFrame(rows)

        if not mapdf.empty:
            # escala min–max para diferenciar tamanhos
            tmin, tmax = mapdf["ticket_medio"].min(), mapdf["ticket_medio"].max()
            span = (tmax - tmin) if (tmax - tmin) > 0 else 1.0
            norm = (mapdf["ticket_medio"] - tmin) / span

            # raios mais visíveis
            R_MIN, R_MAX = 10000, 120000  # 10–120 km
            mapdf["radius"] = (R_MIN + (R_MAX - R_MIN) * norm).astype(float)
            # cor com contraste
            def lerp(a,b,t): return int(a + (b-a)*float(t))
            mapdf["color"] = norm.apply(lambda v: [lerp(60,20,v), lerp(200,100,v), lerp(255,180,v), 220])

            # --- camada de tiles do OpenStreetMap (não exige API key) ---
            osm = pdk.Layer(
                "TileLayer",
                data="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
                min_zoom=0, max_zoom=19, tile_size=256,
                opacity=1.0
            )

            # sua camada de pontos
            points = pdk.Layer(
                "ScatterplotLayer",
                data=mapdf,
                get_position='[lon, lat]',
                get_radius="radius",
                get_fill_color="color",
                pickable=True,
                stroked=False
            )

            view_state = pdk.ViewState(latitude=-14.2, longitude=-51.9, zoom=3.5)

            deck = pdk.Deck(
                map_provider="carto",        # <<< basemap grátis
                map_style="light",           # "light" | "dark" | "voyager"
                initial_view_state=view_state,
                layers=[points],             # sua ScatterplotLayer
                tooltip={"text": "{uf}\nTicket: R$ {ticket_medio}\nPedidos: {pedidos}"}
            )

            st.pydeck_chart(deck, use_container_width=True)

        else:
            st.info("Sem dados suficientes para o mapa (verifique filtros).")
    else:
        st.info("Base filtrada sem `customer_state` ou sem pedidos no período.")


# ---- TEMPO ----
with tab_time:
    st.subheader("Evolução mensal — pedidos, faturamento e por tipo de pagamento")

    if "order_purchase_timestamp" in df_f.columns and total_pedidos > 0:
        tmp = df_f.copy()
        tmp["year_month"] = tmp["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()

        by_m = tmp.groupby("year_month", as_index=False).agg(
            pedidos=("order_id","nunique"),
            faturamento=("payment_value","sum"),
        )
        by_m["ticket"] = by_m["faturamento"] / by_m["pedidos"]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.line_chart(by_m.set_index("year_month")["pedidos"])
        with c2:
            st.line_chart(by_m.set_index("year_month")["faturamento"])
        with c3:
            st.line_chart(by_m.set_index("year_month")["ticket"])

        st.dataframe(by_m.assign(faturamento=lambda d: d["faturamento"].map(br_money),
                                 ticket=lambda d: d["ticket"].map(br_money)))

        # Quebra por tipo de pagamento (stacked)
        st.markdown("**Faturamento por tipo de pagamento (mensal)**")
        if "payment_types" in tmp.columns:
            # explode lista de payment_types
            exp = tmp[["order_id","year_month","payment_value","payment_types"]].explode("payment_types")
            exp = exp.dropna(subset=["payment_types"])
            by_pay = exp.groupby(["year_month","payment_types"], as_index=False).agg(
                faturamento=("payment_value","sum")
            )
            chart = (
                alt.Chart(by_pay)
                .mark_area(opacity=0.6)
                .encode(
                    x="year_month:T",
                    y="faturamento:Q",
                    color="payment_types:N",
                    tooltip=["year_month:T","payment_types:N","faturamento:Q"]
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("`payment_types` não disponível na base filtrada.")
    else:
        st.info("Sem dados temporais suficientes para esta aba.")

# ---- CATEGORIAS ----
with tab_cat:
    st.subheader("Top categorias por faturamento aproximado")
    if df_ip is not None and "order_id" in df_f.columns:
        keep_orders = df_f[["order_id"]].drop_duplicates()
        ip_f = df_ip.merge(keep_orders, on="order_id", how="inner")

        fat_cat = (ip_f.groupby("product_category_name", as_index=False)
                   .agg(faturamento=("revenue_item","sum"),
                        pedidos=("order_id","nunique")))
        fat_cat = fat_cat.sort_values("faturamento", ascending=False)

        top_n = st.slider("Top N", 5, 30, 15)
        metric = st.radio("Métrica", ["faturamento","pedidos"], horizontal=True)
        top_view = fat_cat.head(top_n)

        st.bar_chart(top_view.set_index("product_category_name")[metric])
        st.dataframe(top_view.assign(faturamento=lambda d: d["faturamento"].map(br_money)))
        st.download_button("⬇️ Baixar ranking categorias (CSV)",
                           fat_cat.to_csv(index=False).encode("utf-8"),
                           "categorias_faturamento.csv", "text/csv")
    else:
        st.info("Inclua `olist_order_items_dataset.csv` e `olist_products_dataset.csv` em `data/`.")

# ---- SATISFAÇÃO ----
with tab_sat:
    st.subheader("Atraso de entrega × Nota de review")
    need_cols = {"order_id","order_delivered_customer_date","order_estimated_delivery_date"}
    if df_rev is not None and need_cols.issubset(df_f.columns):
        tmp = df_f[list(need_cols)].merge(df_rev[["order_id","review_score"]], on="order_id", how="left")
        tmp = tmp.dropna(subset=["order_delivered_customer_date","order_estimated_delivery_date"])
        tmp["delay_days"] = (tmp["order_delivered_customer_date"] - tmp["order_estimated_delivery_date"]).dt.days

        rel = (tmp.dropna(subset=["review_score"])
               .groupby("review_score", as_index=False)
               .agg(qtd=("order_id","count"),
                    delay_medio=("delay_days","mean"),
                    atraso_pct=("delay_days", lambda s: (s>0).mean()*100)))
        rel = rel.sort_values("review_score")

        c1, c2 = st.columns(2)
        with c1: st.bar_chart(rel.set_index("review_score")["qtd"])
        with c2: st.bar_chart(rel.set_index("review_score")["delay_medio"])
        st.dataframe(rel.assign(delay_medio=lambda d: d["delay_medio"].round(2),
                                atraso_pct=lambda d: d["atraso_pct"].round(1)))
        st.download_button("⬇️ Baixar atraso × review (CSV)", rel.to_csv(index=False).encode("utf-8"),
                           "atraso_x_review.csv", "text/csv")
    else:
        st.info("Inclua `olist_order_reviews_dataset.csv` em `data/` e garanta colunas de entrega/estimativa.")

# ---- RFM ----
with tab_rfm:
    st.subheader("Segmentação RFM")
    if rfm is not None and not rfm.empty:
        if "Segment" in rfm.columns:
            counts = rfm["Segment"].value_counts().sort_values(ascending=False)
            st.bar_chart(counts)
        top_money = rfm.sort_values("Monetary", ascending=False).head(15) if "Monetary" in rfm.columns else rfm.head(15)
        st.dataframe(top_money)
        st.download_button("⬇️ Baixar RFM (CSV)", rfm.to_csv(index=False).encode("utf-8"),
                           "rfm_table.csv", "text/csv")
    else:
        st.info("Exporte `outputs/rfm_table.csv` no notebook para habilitar esta aba.")

# ---- DADOS & DOWNLOADS ----
with tab_data:
    st.subheader("Dados filtrados (amostra)")
    st.dataframe(df_f.head(300))
    st.download_button("⬇️ Baixar base filtrada (CSV)", df_f.to_csv(index=False).encode("utf-8"),
                       "base_filtrada.csv", "text/csv")

    if df_ip is not None:
        st.subheader("Order Items + Products (amostra)")
        st.dataframe(df_ip.head(200))
