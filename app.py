"""KOSPI200 vs 액티브 ETF 성과 비교 툴 — 메인 UI."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import PERIOD_OPTIONS, TICKERS, get_benchmark_key
from data_loader import load_price_data, slice_period
from metrics import compute_metrics, correlation_matrix, normalize

st.set_page_config(
    page_title="KOSPI200 vs 액티브 ETF 비교",
    page_icon="📈",
    layout="wide",
)

st.title("📈 KOSPI200 vs 액티브 ETF 성과 비교")
st.caption(
    "액티브 ETF가 기초지수(KOSPI200) 대비 실제로 초과수익을 내는지 비교합니다. "
    "일간 종가 기준이며 배당/분배금은 반영되지 않습니다."
)

# ---------------------------------------------------------------- 데이터 로드
with st.spinner("데이터를 불러오는 중입니다... (최초 실행 시 수십 초 걸릴 수 있습니다)"):
    try:
        prices_all = load_price_data()
    except Exception as e:
        st.error(f"데이터 로드에 실패했습니다: {e}")
        st.stop()

load_errors = prices_all.attrs.get("errors", {})
if load_errors:
    failed = ", ".join(TICKERS[k]["name"] for k in load_errors if k in TICKERS)
    st.warning(f"다음 종목은 데이터를 불러오지 못해 제외되었습니다: {failed}")

# ------------------------------------------------------------------ 사이드바
st.sidebar.header("설정")

period_label = st.sidebar.radio("기간 선택", list(PERIOD_OPTIONS.keys()), index=3)
period = PERIOD_OPTIONS[period_label]

st.sidebar.subheader("종목 표시/숨김")
available_keys = [k for k in TICKERS if k in prices_all.columns]
selected_keys = [
    k for k in available_keys
    if st.sidebar.checkbox(TICKERS[k]["name"], value=True, key=f"show_{k}")
]

if not selected_keys:
    st.info("사이드바에서 표시할 종목을 1개 이상 선택하세요.")
    st.stop()

benchmark_key = get_benchmark_key()

# ------------------------------------------------------------------ 기간 슬라이스
prices = slice_period(prices_all[selected_keys], period)
prices = prices.dropna(how="all")

if prices.dropna(how="all").empty or len(prices) < 2:
    st.warning("선택한 기간에 데이터가 없습니다. 다른 기간을 선택하세요.")
    st.stop()

name_map = {k: TICKERS[k]["name"] for k in selected_keys}
color_map = {TICKERS[k]["name"]: TICKERS[k]["color"] for k in selected_keys}

# ------------------------------------------------------------ 1) 정규화 수익률 차트
st.subheader(f"정규화 수익률 비교 ({period_label}, 시작점 = 100)")

normalized = normalize(prices).rename(columns=name_map)

fig = go.Figure()
for col in normalized.columns:
    s = normalized[col].dropna()
    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            name=col,
            line=dict(color=color_map.get(col), width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>" + col + ": %{y:.2f}<extra></extra>",
        )
    )
fig.add_hline(y=100, line_dash="dot", line_color="gray", opacity=0.5)
fig.update_layout(
    height=520,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    margin=dict(l=40, r=20, t=30, b=40),
    yaxis_title="지수화 수익률 (시작=100)",
    xaxis_title=None,
)
st.plotly_chart(fig, width="stretch")

st.caption(
    "각 종목은 자신의 데이터가 존재하는 첫 거래일을 100으로 정규화합니다. "
    "상장 초기 데이터가 없는 종목은 상장일부터 표시됩니다."
)

# ------------------------------------------------------------ 2) 성과 지표 테이블
st.subheader("성과 지표")

metrics_df = compute_metrics(prices, benchmark_key)
metrics_df.index = [name_map[k] for k in metrics_df.index]

pct_cols = ["기간수익률", "연환산수익률", "변동성(연)", "MDD", "알파(연)", "트래킹에러(연)"]
styled = metrics_df.style.format(
    {c: "{:.2%}" for c in pct_cols} | {"샤프지수": "{:.2f}"},
    na_rep="-",
).map(
    lambda v: "color: #d62728" if isinstance(v, float) and v < 0 else "color: #2ca02c",
    subset=["기간수익률", "연환산수익률", "알파(연)"],
)
st.dataframe(styled, width="stretch")

st.caption(
    f"알파(연) = 기준지수({TICKERS[benchmark_key]['name']})와 겹치는 구간의 연환산 수익률 차이. "
    "트래킹에러 = 일간 초과수익률 표준편차의 연환산. "
    "샤프지수는 연 3% 무위험 수익률 가정."
)

# ------------------------------------------------------------ 3) 상관관계 히트맵
st.subheader("일간 수익률 상관관계")

corr = correlation_matrix(prices).rename(index=name_map, columns=name_map)

heatmap = px.imshow(
    corr,
    text_auto=".2f",
    color_continuous_scale="RdBu_r",
    zmin=-1,
    zmax=1,
    aspect="auto",
)
heatmap.update_layout(
    height=480,
    margin=dict(l=40, r=20, t=30, b=40),
    coloraxis_colorbar=dict(title="상관계수"),
)
st.plotly_chart(heatmap, width="stretch")

st.caption("겹치는 거래일 구간의 일간 수익률로 계산한 피어슨 상관계수입니다.")

# ------------------------------------------------------------------ 푸터
last_date = prices.index.max().strftime("%Y-%m-%d")
st.markdown("---")
st.caption(
    f"데이터: KRX (FinanceDataReader) · 최종 거래일: {last_date} · "
    "일간 종가 기준, 배당/분배금 미반영 · 투자 판단의 책임은 본인에게 있습니다."
)
