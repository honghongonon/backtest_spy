import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ETF 미래 자산 시뮬레이터", layout="wide")

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_portfolio.json")


def load_saved_state() -> dict:
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(data: dict) -> None:
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

PORTFOLIO_COLORS = ["#5DA5DA", "#FAA43A", "#60BD68", "#F17CB0", "#B2912F", "#B276B2", "#DECF3F", "#F15854"]

tab1, tab2, tab3 = st.tabs(["📊 단일 시나리오", "⚖️ 종목 비교", "📦 내 자산 구성"])

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

POOL_DIVIDEND_OPTIONS = ["각자 종목에 재투자", "한 곳에 몰아서 투자", "현금으로 보유 (재투자 안 함)"]
POOL_COLOR = "#FFD166"


def simulate_breakdown(months: int, initial: float, monthly_contribution: float, price_growth: float, dividend_yield: float, reinvest_self: bool) -> pd.DataFrame:
    g_price_m = (1 + price_growth) ** (1 / 12) - 1
    g_total_m = (1 + price_growth + dividend_yield) ** (1 / 12) - 1

    principal_pool = initial
    contributed = initial
    self_div_pool = 0.0

    rows = [{"month": 0, "투입한 자산": initial, "가격 상승분": 0.0, "배당현금": 0.0, "자기배당축적": 0.0}]
    for m in range(1, months + 1):
        principal_pool *= 1 + g_price_m
        principal_pool += monthly_contribution
        contributed += monthly_contribution

        div_cash = principal_pool * (dividend_yield / 4) if m % 3 == 0 else 0.0
        if reinvest_self:
            self_div_pool = self_div_pool * (1 + g_total_m) + div_cash

        rows.append(
            {
                "month": m,
                "투입한 자산": contributed,
                "가격 상승분": principal_pool - contributed,
                "배당현금": div_cash,
                "자기배당축적": self_div_pool,
            }
        )
    return pd.DataFrame(rows)


with tab3:
    st.subheader("지금 갖고 있는 자산 구성을 입력하면, 미래엔 어떻게 될까?")
    st.caption(
        "종목별로 지금 보유한 금액을 입력하세요. 입력하는 즉시 아래 결과가 바로 갱신됩니다. 표 아래 '+' 를 누르면 행을 추가할 수 있어요 "
        "(예: 비트코인처럼 목록에 없는 종목도 이름과 예상 연평균 수익률/배당율을 직접 적으면 같이 계산됩니다. 배당이 없으면 0으로 두세요)."
    )

    saved = load_saved_state()

    default_rows = pd.DataFrame(
        saved.get("holdings")
        or {
            "종목": list(DEFAULT_ASSUMPTIONS.keys()),
            "현재 보유금액(원)": [0, 0, 0],
            "연평균 가격상승률(%)": [d["price_growth"] for d in DEFAULT_ASSUMPTIONS.values()],
            "연 배당율(%)": [d["dividend_yield"] for d in DEFAULT_ASSUMPTIONS.values()],
        }
    )

    holdings = st.data_editor(
        default_rows,
        num_rows="dynamic",
        use_container_width=False,
        column_config={
            "종목": st.column_config.TextColumn(width="medium"),
            "현재 보유금액(원)": st.column_config.NumberColumn(width="medium", format="%,d"),
            "연평균 가격상승률(%)": st.column_config.NumberColumn(width="small", format="%.1f"),
            "연 배당율(%)": st.column_config.NumberColumn(width="small", format="%.1f"),
        },
        key="holdings_editor",
    )

    c1, c2 = st.columns(2)
    with c1:
        years3 = st.slider("투자 기간 (년)", 1, 40, saved.get("years3", 20), key="y3")
    with c2:
        monthly3 = st.number_input(
            "매월 추가 적립금 (원, 보유 비중대로 분배)",
            min_value=0,
            value=saved.get("monthly3", 0),
            step=50_000,
            key="m3",
        )

    pool_index = (
        POOL_DIVIDEND_OPTIONS.index(saved["pool_handling"])
        if saved.get("pool_handling") in POOL_DIVIDEND_OPTIONS
        else 0
    )
    pool_handling = st.radio("배당금 처리 방식", POOL_DIVIDEND_OPTIONS, horizontal=True, index=pool_index, key="pool3")

    dest_name = None
    dest_total_growth = 0.0
    if pool_handling == POOL_DIVIDEND_OPTIONS[1]:
        dest_options = [n for n in holdings["종목"].dropna().tolist() if str(n).strip()]
        if dest_options:
            dest_index = dest_options.index(saved["dest_name"]) if saved.get("dest_name") in dest_options else 0
            dest_name = st.selectbox("배당을 몰아서 투자할 종목", dest_options, index=dest_index, key="dest3")
            dest_row = holdings[holdings["종목"] == dest_name].iloc[0]
            dest_total_growth = (dest_row["연평균 가격상승률(%)"] + dest_row["연 배당율(%)"]) / 100

    save_state(
        {
            "holdings": holdings.to_dict("records"),
            "years3": years3,
            "monthly3": monthly3,
            "pool_handling": pool_handling,
            "dest_name": dest_name,
        }
    )

    valid = holdings[holdings["종목"].notna() & (holdings["종목"].astype(str).str.strip() != "")].copy()
    valid[["현재 보유금액(원)", "연평균 가격상승률(%)", "연 배당율(%)"]] = valid[
        ["현재 보유금액(원)", "연평균 가격상승률(%)", "연 배당율(%)"]
    ].fillna(0)
    total_current = valid["현재 보유금액(원)"].sum()

    if valid.empty or total_current <= 0:
        st.info("위 표에 보유 금액을 입력하면 결과가 바로 나타나요.")
    else:
        months = years3 * 12
        reinvest_self = pool_handling == POOL_DIVIDEND_OPTIONS[0]

        holding_layers = {}
        dividend_cash_total = pd.Series(0.0, index=range(months + 1))
        for _, row in valid.iterrows():
            weight = row["현재 보유금액(원)"] / total_current
            df_b = simulate_breakdown(
                months=months,
                initial=row["현재 보유금액(원)"],
                monthly_contribution=monthly3 * weight,
                price_growth=row["연평균 가격상승률(%)"] / 100,
                dividend_yield=row["연 배당율(%)"] / 100,
                reinvest_self=reinvest_self,
            )
            holding_layers[row["종목"]] = df_b["투입한 자산"] + df_b["가격 상승분"] + df_b["자기배당축적"]
            if not reinvest_self:
                dividend_cash_total += df_b["배당현금"]

        pooled_div = pd.Series(0.0, index=range(months + 1))
        if pool_handling == POOL_DIVIDEND_OPTIONS[1] and dest_name:
            g_dest_m = (1 + dest_total_growth) ** (1 / 12) - 1
            pool = 0.0
            for m in range(1, months + 1):
                pool = pool * (1 + g_dest_m) + dividend_cash_total[m]
                pooled_div[m] = pool
        elif pool_handling == POOL_DIVIDEND_OPTIONS[2]:
            pool = 0.0
            for m in range(1, months + 1):
                pool += dividend_cash_total[m]
                pooled_div[m] = pool

        years_axis = [m / 12 for m in range(months + 1)]
        fig3 = go.Figure()
        for i, (name, series) in enumerate(holding_layers.items()):
            color = PORTFOLIO_COLORS[i % len(PORTFOLIO_COLORS)]
            fig3.add_trace(
                go.Scatter(
                    x=years_axis,
                    y=series,
                    name=name,
                    mode="lines",
                    stackgroup="one",
                    line=dict(width=0.5, color=color),
                    fillcolor=color,
                    hovertemplate="%{y:,.0f}원<extra>" + name + "</extra>",
                )
            )

        pool_label = None
        if pool_handling == POOL_DIVIDEND_OPTIONS[1] and dest_name:
            pool_label = f"배당 몰아넣기 → {dest_name}"
        elif pool_handling == POOL_DIVIDEND_OPTIONS[2]:
            pool_label = "배당 (현금 보유)"

        if pool_label:
            fig3.add_trace(
                go.Scatter(
                    x=years_axis,
                    y=pooled_div,
                    name=pool_label,
                    mode="lines",
                    stackgroup="one",
                    line=dict(width=0.5, color=POOL_COLOR),
                    fillcolor=POOL_COLOR,
                    hovertemplate="%{y:,.0f}원<extra>" + pool_label + "</extra>",
                )
            )

        fig3 = styled_layout(fig3, "보유 자산 구성의 미래 변화")
        st.plotly_chart(fig3, use_container_width=True)

        total_series = sum(holding_layers.values()) + pooled_div
        c1, c2 = st.columns(2)
        c1.metric("현재 총 자산", krw(total_series.iloc[0]))
        c2.metric(f"{years3}년 후 예상 총 자산", krw(total_series.iloc[-1]))

        st.subheader("연차별 자산 변화 (표)")
        yearly_table = {"연차": list(range(years3 + 1))}
        for name, series in holding_layers.items():
            yearly_table[name] = [krw(series[y * 12]) for y in range(years3 + 1)]
        if pool_label:
            yearly_table[pool_label] = [krw(pooled_div[y * 12]) for y in range(years3 + 1)]
        yearly_table["총 자산"] = [krw(total_series[y * 12]) for y in range(years3 + 1)]
        st.dataframe(pd.DataFrame(yearly_table), use_container_width=False, hide_index=True)
