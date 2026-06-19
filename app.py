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

LAYER_COLORS = {
    "투입한 자산": "#5DA5DA",
    "가격 상승분": "#FAA43A",
    "배당으로 늘어난 자산": "#60BD68",
}

AXIS_FONT = dict(family="Arial", size=15, color="#333")
TITLE_FONT = dict(family="Arial", size=20, color="#222")


def krw(x: float) -> str:
    return f"{x:,.0f}원"


def simulate(
    months: int,
    initial: float,
    monthly_contribution: float,
    price_growth: float,
    dividend_yield: float,
    handling: str,
    other_total_growth: float = 0.0,
) -> pd.DataFrame:
    g_price_m = (1 + price_growth) ** (1 / 12) - 1
    g_main_total_m = (1 + price_growth + dividend_yield) ** (1 / 12) - 1
    g_other_m = (1 + other_total_growth) ** (1 / 12) - 1

    principal_pool = initial
    dividend_pool = 0.0
    contributed = initial

    rows = []
    for m in range(1, months + 1):
        principal_pool *= 1 + g_price_m
        principal_pool += monthly_contribution
        contributed += monthly_contribution

        if m % 3 == 0:  # 분기 배당 지급 가정
            dividend_pool += principal_pool * (dividend_yield / 4)

        if handling == DIVIDEND_OPTIONS[0]:
            dividend_pool *= 1 + g_main_total_m
        elif handling == DIVIDEND_OPTIONS[1]:
            dividend_pool *= 1 + g_other_m
        # 현금 보유는 성장 없음

        capital_gain = principal_pool - contributed
        rows.append(
            {
                "month": m,
                "투입한 자산": contributed,
                "가격 상승분": capital_gain,
                "배당으로 늘어난 자산": dividend_pool,
                "총 자산": contributed + capital_gain + dividend_pool,
            }
        )
    return pd.DataFrame(rows)


def styled_layout(fig: go.Figure, title: str, y_title: str = "자산 (원)") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=TITLE_FONT),
        xaxis=dict(title="투자 기간 (년)", title_font=AXIS_FONT, tickfont=AXIS_FONT, ticksuffix="년", showgrid=True, gridcolor="#eee"),
        yaxis=dict(title=y_title, title_font=AXIS_FONT, tickfont=AXIS_FONT, tickformat=",", showgrid=True, gridcolor="#eee"),
        legend=dict(font=dict(size=13)),
        hovermode="x unified",
        plot_bgcolor="white",
    )
    return fig


st.title("💰 ETF 미래 자산 시뮬레이터")
st.caption("과거 평균 수익률을 가정으로, 적립·재투자 방식에 따라 미래 자산이 얼마나 될지 시뮬레이션합니다. 금액은 원화 기준이며 환율 변동은 고려하지 않습니다. (실제 미래 수익률을 보장하지 않습니다)")

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

        initial = st.number_input("초기 투자금 (원)", min_value=0, value=10_000_000, step=1_000_000)
        monthly_contribution = st.number_input("매월 적립금 (원)", min_value=0, value=300_000, step=50_000)
        years = st.slider("투자 기간 (년)", 1, 40, 20)

        handling = st.radio("배당금 처리 방식", DIVIDEND_OPTIONS)

        other_total_growth = 0.0
        if handling == DIVIDEND_OPTIONS[1]:
            other_choice = st.selectbox("배당을 투자할 다른 종목", list(DEFAULT_ASSUMPTIONS.keys()), key="other")
            od = DEFAULT_ASSUMPTIONS[other_choice]
            other_price_growth = st.number_input(
                "다른 종목 연평균 가격상승률 (%)", value=od["price_growth"], step=0.5, key="op"
            )
            other_dividend_yield = st.number_input(
                "다른 종목 연 배당율 (%)", value=od["dividend_yield"], step=0.1, key="od"
            )
            other_total_growth = (other_price_growth + other_dividend_yield) / 100

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
                other_total_growth=other_total_growth,
            )
            df["연차"] = df["month"] / 12

            fig = go.Figure()
            for layer in ["투입한 자산", "가격 상승분", "배당으로 늘어난 자산"]:
                fig.add_trace(
                    go.Scatter(
                        x=df["연차"],
                        y=df[layer],
                        name=layer,
                        mode="lines",
                        stackgroup="one",
                        line=dict(width=0.5, color=LAYER_COLORS[layer]),
                        fillcolor=LAYER_COLORS[layer],
                        hovertemplate="%{y:,.0f}원<extra>" + layer + "</extra>",
                    )
                )
            fig = styled_layout(fig, "자산 구성 변화")
            st.plotly_chart(fig, use_container_width=True)

            final = df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("최종 총 자산", krw(final["총 자산"]))
            c2.metric("총 납입금", krw(final["투입한 자산"]))
            c3.metric("순수익", krw(final["총 자산"] - final["투입한 자산"]))
        else:
            st.info("왼쪽에서 조건을 설정하고 '시뮬레이션 실행'을 눌러주세요.")

with tab2:
    st.subheader("여러 종목을 같은 조건으로 비교")
    c1, c2, c3 = st.columns(3)
    with c1:
        initial2 = st.number_input("초기 투자금 (원)", min_value=0, value=10_000_000, step=1_000_000, key="i2")
    with c2:
        monthly2 = st.number_input("매월 적립금 (원)", min_value=0, value=300_000, step=50_000, key="m2")
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
            df2["연차"] = df2["month"] / 12
            fig2.add_trace(
                go.Scatter(
                    x=df2["연차"],
                    y=df2["총 자산"],
                    name=t,
                    mode="lines",
                    line=dict(width=3),
                    hovertemplate="%{y:,.0f}원<extra>" + t + "</extra>",
                )
            )
            summary[t] = df2.iloc[-1]["총 자산"]

        fig2 = styled_layout(fig2, "종목별 자산 비교")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("최종 자산 비교")
        st.dataframe(
            pd.DataFrame({"종목": summary.keys(), "최종 자산": [krw(v) for v in summary.values()]}),
            use_container_width=True,
            hide_index=True,
        )
