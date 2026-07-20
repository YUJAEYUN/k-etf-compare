"""성과지표 계산 로직.

모든 계산은 일간 종가 기준. 각 종목은 자신의 유효 데이터 구간
(상장 이후)만 사용해 계산하며, 알파/트래킹에러는 기준지수와
겹치는 구간에서만 계산한다.
"""

import numpy as np
import pandas as pd

from config import RISK_FREE_RATE, TRADING_DAYS_PER_YEAR


def normalize(df: pd.DataFrame, base: float = 100.0) -> pd.DataFrame:
    """각 컬럼을 자신의 첫 유효값 기준 base 로 정규화."""
    out = {}
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            out[col] = df[col]
        else:
            out[col] = df[col] / s.iloc[0] * base
    return pd.DataFrame(out, index=df.index)


def daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """일간 수익률 (상장 이전 NaN 구간은 그대로 NaN)."""
    return df.pct_change(fill_method=None)


def _annualize_return(total_return: float, n_days: int) -> float:
    """기간 수익률을 연환산. 1년 미만 구간도 동일 공식 적용."""
    if n_days <= 0:
        return np.nan
    return (1 + total_return) ** (TRADING_DAYS_PER_YEAR / n_days) - 1


def max_drawdown(prices: pd.Series) -> float:
    """최대낙폭(MDD). 음수로 반환 (예: -0.23)."""
    s = prices.dropna()
    if len(s) < 2:
        return np.nan
    dd = s / s.cummax() - 1
    return dd.min()


def compute_metrics(prices: pd.DataFrame, benchmark_key: str) -> pd.DataFrame:
    """종목별 성과지표 테이블 생성.

    반환 컬럼: 기간수익률, 연환산수익률, 변동성(연), 샤프지수, MDD,
              알파(초과수익률), 트래킹에러
    """
    rets = daily_returns(prices)
    bench_ret = rets[benchmark_key] if benchmark_key in rets.columns else None
    bench_prices = prices[benchmark_key].dropna() if benchmark_key in prices.columns else None

    rows = {}
    for col in prices.columns:
        s = prices[col].dropna()
        r = rets[col].dropna()
        if len(s) < 2:
            rows[col] = {k: np.nan for k in [
                "기간수익률", "연환산수익률", "변동성(연)", "샤프지수",
                "MDD", "알파(연)", "트래킹에러(연)"]}
            continue

        n_days = len(r)
        total_ret = s.iloc[-1] / s.iloc[0] - 1
        ann_ret = _annualize_return(total_ret, n_days)
        vol = r.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        sharpe = (ann_ret - RISK_FREE_RATE) / vol if vol > 0 else np.nan
        mdd = max_drawdown(s)

        alpha = np.nan
        te = np.nan
        if bench_ret is not None and col != benchmark_key:
            # 두 시계열이 모두 존재하는 구간에서만 계산
            pair = pd.concat([r, bench_ret], axis=1, join="inner").dropna()
            if len(pair) >= 2:
                excess = pair.iloc[:, 0] - pair.iloc[:, 1]
                # 같은 구간의 누적수익률 차이를 연환산한 알파
                fund_total = (1 + pair.iloc[:, 0]).prod() - 1
                bm_total = (1 + pair.iloc[:, 1]).prod() - 1
                n = len(pair)
                alpha = _annualize_return(fund_total, n) - _annualize_return(bm_total, n)
                te = excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

        rows[col] = {
            "기간수익률": total_ret,
            "연환산수익률": ann_ret,
            "변동성(연)": vol,
            "샤프지수": sharpe,
            "MDD": mdd,
            "알파(연)": alpha,
            "트래킹에러(연)": te,
        }

    return pd.DataFrame(rows).T


def correlation_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """종목 간 일간 수익률 상관계수 행렬 (pairwise, 겹치는 구간 기준)."""
    return daily_returns(prices).corr()
