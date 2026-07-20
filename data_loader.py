"""FinanceDataReader 기반 데이터 수집/캐싱.

- 지수/ETF 모두 fdr.DataReader 로 조회 (로그인 불필요)
- 일간 종가 기준, 거래일 인덱스로 정렬
- 상장 초기 등 데이터가 없는 구간은 NaN 으로 남기고,
  중간 결측치만 forward fill 처리 (상장 이전 구간까지 채우지 않음)
"""

from datetime import datetime

import FinanceDataReader as fdr
import pandas as pd
import streamlit as st

from config import DATA_START_DATE, TICKERS


def _fetch_close_series(code: str, start: str, end: str) -> pd.Series:
    """단일 종목의 일간 종가 시리즈를 조회."""
    df = fdr.DataReader(code, start, end)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    close = df["Close"].astype(float)
    close.index = pd.to_datetime(close.index)
    # 거래정지 등으로 종가가 0으로 내려오는 행 제거
    close = close[close > 0]
    return close.sort_index()


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def load_price_data(end_date: str | None = None) -> pd.DataFrame:
    """config.TICKERS 전 종목의 종가를 하나의 DataFrame 으로 반환.

    컬럼: TICKERS 의 키, 인덱스: 거래일(DatetimeIndex).
    각 종목의 상장 이후 구간에서만 forward fill 을 적용한다.
    """
    end = end_date or datetime.now().strftime("%Y%m%d")

    series = {}
    errors = {}
    for key, info in TICKERS.items():
        try:
            s = _fetch_close_series(info["code"], DATA_START_DATE, end)
            if not s.empty:
                series[key] = s
            else:
                errors[key] = "데이터 없음"
        except Exception as e:  # 네트워크/KRX 오류 시 해당 종목만 제외
            errors[key] = str(e)

    if not series:
        raise RuntimeError(f"데이터를 하나도 불러오지 못했습니다: {errors}")

    df = pd.DataFrame(series).sort_index()

    # 거래일 합집합 기준으로 정렬된 상태에서, 각 컬럼은 자신의 첫 유효값 이후만 ffill.
    # (pandas ffill 은 선행 NaN 은 채우지 않으므로 상장 이전 구간은 NaN 유지)
    df = df.ffill()

    df.attrs["errors"] = errors
    return df


def slice_period(df: pd.DataFrame, period: str | int) -> pd.DataFrame:
    """기간 옵션에 따라 DataFrame 을 잘라서 반환.

    period: 개월 수(int), "ytd", "all"
    """
    if df.empty or period == "all":
        return df

    last_date = df.index.max()
    if period == "ytd":
        start = pd.Timestamp(year=last_date.year, month=1, day=1)
    else:
        start = last_date - pd.DateOffset(months=int(period))

    return df.loc[df.index >= start]
