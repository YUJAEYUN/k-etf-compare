"""종목코드/티커 설정.

ETF를 교체하거나 추가하려면 이 파일의 TICKERS 딕셔너리만 수정하면 됩니다.
- code: FinanceDataReader.DataReader 에 넘길 심볼. 지수는 "KS200"처럼 문자열 코드,
  종목/ETF는 6자리 종목코드를 사용합니다.
- benchmark: True 인 항목이 초과수익률(알파)/트래킹에러 계산의 기준이 됩니다. (정확히 1개)
"""

# 데이터 조회 시작일 (가장 오래된 ETF 상장일보다 넉넉히 이전으로)
DATA_START_DATE = "20200101"

TICKERS = {
    "KOSPI200": {
        "code": "KS200",         # FinanceDataReader 지수코드: 코스피 200
        "name": "KOSPI200",
        "benchmark": True,
        "color": "#636EFA",
    },
    "TIGER_AI_KOREA_GROWTH": {
        "code": "365040",
        "name": "TIGER AI코리아그로스액티브",
        "benchmark": False,
        "color": "#EF553B",
    },
    # 아래 3종은 KOSPI200(또는 KOSPI)을 비교지수로 하는 인기 액티브 ETF.
    # 교체 시 code/name만 바꾸면 됩니다.
    "KODEX_K_INNOVATION": {
        "code": "373490",
        "name": "KODEX K-이노베이션액티브",
        "benchmark": False,
        "color": "#00CC96",
    },
    "TIMEFOLIO_KSTOCK": {
        "code": "385710",
        "name": "TIMEFOLIO Kstock액티브",
        "benchmark": False,
        "color": "#AB63FA",
    },
    "ASSETPLUS_KOREA_PLATFORM": {
        "code": "407820",
        "name": "에셋플러스 코리아플랫폼액티브",
        "benchmark": False,
        "color": "#FFA15A",
    },
}

# 기간 선택 옵션 (라벨 -> 개월 수, None 은 특수 처리)
PERIOD_OPTIONS = {
    "1개월": 1,
    "3개월": 3,
    "6개월": 6,
    "1년": 12,
    "YTD": "ytd",
    "전체": "all",
}

# 연환산 상수 (한국 주식시장 연간 거래일 수)
TRADING_DAYS_PER_YEAR = 252

# 샤프지수 계산용 무위험 수익률 (연율, 예: 0.03 = 3%)
RISK_FREE_RATE = 0.03


def get_benchmark_key() -> str:
    """benchmark=True 로 지정된 종목의 키를 반환."""
    for key, info in TICKERS.items():
        if info.get("benchmark"):
            return key
    raise ValueError("config.TICKERS 에 benchmark=True 인 항목이 없습니다.")
