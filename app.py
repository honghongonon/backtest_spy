import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ETF 미래 자산 시뮬레이터", layout="wide")

# 과거 평균치를 바탕으로 한 기본 가정값 (사용자가 직접 수정 가능)
DEFAULT_ASSUMPTIONS = {
    "SPY (S&P500)": {"price_growth": 8.5, "dividend_yield": 1.3},
    "QQQ (나스닥100)": {"price_growth": 15.0, "dividend_yield": 0.6},
    "SCHD (배당성장)": {"price_growth": 7.0, "dividend_yield": 3.5},
}

DIVIDEND_OPTIONS = ["같은 종목에 재투자", "다른 종목에 투자", "현금으로 보유 (재투자 안 함)"]


def simulate(
    months: int,
    initial: float,
    monthly_contribution: float,
    price_growth: float,
    dividend_yield: float,
    handling: str,
    other_price_growth: float = 0.0,
    other_dividend_yield: float = 0.0,
) -> pd.DataFrame:
    g_main_m = (1 + price_growth) ** (1 / 12) - 1
    g_other_m = (1 + other_price_growth + other_dividend_yield) ** (1 / 12) - 1

    main_value = initial
    other_value = 0.0
    cash = 0.0
    contributed = initial

    rows = []
    for m in range(1, months + 1):
        main_value *= 1 + g_main_m
        main_value += monthly_contribution
        contributed += monthly_contribution

        if m % 3 == 0:  # 분기 배당 지급 가정
            dividend = main_value * (dividend_yield / 4)
            if handling == DIVIDEND_OPTIONS[0]:
                main_value += dividend
            elif handling == DIVIDEND_OPTIONS[1]:
                other_value += dividend
            else:
                cash += dividend

        if handling == DIVIDEND_OPTIONS[1]:
            other_value *= 1 + g_other_m

        rows.append(
            {
                "month": m,
                "메인 자산": main_value,
                "다른 종목 투자분": other_value,
                "현금(배당)": cash,
                "총 자산": main_value + other_value + cash,
                "총 납입금": contributed,
            }
        )
    return pd.DataFrame(rows)


st.title("💰 ETF 미래 자산 시뮬레이터")
st.caption("과거 평균 수익률을 가정으로, 적립·재투자 방식에 따라 미래 자산이 얼마나 될지 시뮬레이션합니다. (실제 미래 수익률을 보장하지 않습니다)")

tab1, tab2 = st.tabs(["📊 단일 시나리오", "⚖️ 종목 비교"])

with tab1:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("설정")
        ticker_choice = st.selectbox("메인 종목", list(DEFAULT_ASSUMPTIONS.keys()) + ["직접 입력"])
        if ticker_choice == "직접 입력":
            price_growth = st.number_input("연평균 가격상승률 (%)", value=8.0, step=0.5)
            dividend_yield = st.number_input("연 배당율 (%)", value=2.0, step=0.1)
        else:
            d = DEFAULT_ASSUMPTIONS[ticker_choice]
            price_growth = st.number_input("연평균 가격상승률 (%)", value=d["price_growth"], step=0.5)
            dividend_yield = st.number_input("연 배당율 (%)", value=d["dividend_yield"], step=0.1)

        initial = st.number_input("초기 투자금 ($)", min_value=0, value=10000, step=500)
        monthly_contribution = st.number_input("매월 적립금 ($)", min_value=0, value=300, step=50)
        years = st.slider("투자 기간 (년)", 1, 40, 20)

        handling = st.radio("배당금 처리 방식", DIVIDEND_OPTIONS)

        other_price_growth = 0.0
        other_dividend_yield = 0.0
        if handling == DIVIDEND_OPTIONS[1]:
            other_choice = st.selectbox("배당을 투자할 다른 종목", list(DEFAULT_ASSUMPTIONS.keys()), key="other")
            od = DEFAULT_ASSUMPTIONS[other_choice]
            other_price_growth = st.number_input(
                "다른 종목 연평균 가격상승률 (%)", value=od["price_growth"], step=0.5, key="op"
            )
            other_dividend_yield = st.number_input(
                "다른 종목 연 배당율 (%)", value=od["dividend_yield"], step=0.1, key="od"
            )

        run1 = st.button("시뮬레이션 실행", type="primary", key="run1")

    with col2:
        if run1:
            df = simulate(
                months=years * 12,
                initial=initial,
                monthly_contribution=monthly_contribution,
                price_growth=price_growth / 100,
                dividend_yield=dividend_yield / 100,
                handling=handling,
                other_price_growth=other_price_growth / 100,
                other_dividend_yield=other_dividend_yield / 100,
            )

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["month"] / 12, y=df["총 자산"], name="총 자산", mode="lines"))
            fig.add_trace(go.Scatter(x=df["month"] / 12, y=df["총 납입금"], name="총 납입금", mode="lines", line=dict(dash="dash")))
            fig.update_layout(title="자산 변화", xaxis_title="투자 기간 (년)", yaxis_title="금액 ($)", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            final = df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("최종 총 자산", f"${final['총 자산']:,.0f}")
            c2.metric("총 납입금", f"${final['총 납입금']:,.0f}")
            c3.metric("순수익", f"${final['총 자산'] - final['총 납입금']:,.0f}")
        else:
            st.info("왼쪽에서 조건을 설정하고 '시뮬레이션 실행'을 눌러주세요.")

with tab2:
    st.subheader("여러 종목을 같은 조건으로 비교")
    c1, c2, c3 = st.columns(3)
    with c1:
        initial2 = st.number_input("초기 투자금 ($)", min_value=0, value=10000, step=500, key="i2")
    with c2:
        monthly2 = st.number_input("매월 적립금 ($)", min_value=0, value=300, step=50, key="m2")
    with c3:
        years2 = st.slider("투자 기간 (년)", 1, 40, 20, key="y2")

    reinvest2 = st.checkbox("배당 재투자", value=True, key="r2")
    tickers2 = st.multiselect("비교할 종목", list(DEFAULT_ASSUMPTIONS.keys()), default=list(DEFAULT_ASSUMPTIONS.keys()))

    run2 = st.button("비교 실행", type="primary", key="run2")

    if run2 and tickers2:
        fig2 = go.Figure()
        summary = {}
        for t in tickers2:
            d = DEFAULT_ASSUMPTIONS[t]
            df2 = simulate(
                months=years2 * 12,
                initial=initial2,
                monthly_contribution=monthly2,
                price_growth=d["price_growth"] / 100,
                dividend_yield=d["dividend_yield"] / 100,
                handling=DIVIDEND_OPTIONS[0] if reinvest2 else DIVIDEND_OPTIONS[2],
            )
            fig2.add_trace(go.Scatter(x=df2["month"] / 12, y=df2["총 자산"], name=t, mode="lines"))
            summary[t] = df2.iloc[-1]["총 자산"]

        fig2.update_layout(title="종목별 자산 비교", xaxis_title="투자 기간 (년)", yaxis_title="총 자산 ($)", hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("최종 자산 비교")
        st.dataframe(
            pd.DataFrame({"종목": summary.keys(), "최종 자산": [f"${v:,.0f}" for v in summary.values()]}),
            use_container_width=True,
            hide_index=True,
        )
