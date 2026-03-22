import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="와우경제", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; color: #1E1E1E; }
    [data-testid="stMetric"] {
        background-color: #FFFFFF; padding: 20px; border-radius: 12px;
        border: 1px solid #E6E9EF; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] { color: #555555 !important; font-weight: bold; }
    [data-testid="stMetricValue"] { color: #1E1E1E !important; font-size: 1.8rem !important; }
    h1, h2, h3, p, span, label { color: #1E1E1E !important; }
    span[data-baseweb="tag"] { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; color: #1E1E1E !important; }
    </style>
    """, unsafe_allow_html=True)

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE   = os.path.join(BASE_DIR, 'data', 'market_history.csv')
VOLUME_FILE    = os.path.join(BASE_DIR, 'data', 'market_volume.csv')
PATCH_LOG_FILE = os.path.join(BASE_DIR, 'data', 'patch_log.csv')

# 블리자드 한국 배틀넷 스토어 기준 WoW 토큰 원화 판매 가격
WOW_TOKEN_KRW = 22_000

# 한밤(Midnight) 확장팩 주요 타임라인 (차트 수직선)
EXPANSION_EVENTS = [
    {"date": "2026-03-03", "label": "한밤 정식 출시",        "color": "#E63946", "dash": "solid"},
    {"date": "2026-03-19", "label": "시즌 1 · 루야살 오픈", "color": "#4C9BE8", "dash": "dot"},
]

CATEGORY_COLOR = {
    "출시":   "#E63946",
    "레이드": "#4C9BE8",
    "핫픽스": "#888888",
    "밸런스": "#F4A522",
}

PERIODS = {"24시간": 24, "3일": 72, "7일": 168, "전체": None}


@st.cache_data(ttl=3600)
def load_data(file_path):
    # wide/long 동시 변환 후 캐시
    df_wide = pd.read_csv(file_path, index_col=0)
    df_wide.index.name = None
    df_long = df_wide.reset_index().melt(id_vars='index', var_name='수집시각', value_name='value')
    df_long.rename(columns={'index': '품목명'}, inplace=True)
    df_long['수집시각'] = pd.to_datetime(df_long['수집시각'])
    return df_wide, df_long


@st.cache_data(ttl=3600)
def load_patch_log():
    df = pd.read_csv(PATCH_LOG_FILE)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    return df


def add_event_lines(fig):
    # 확장팩 타임라인 수직선 마킹 (Plotly 신버전: 밀리초 타임스탬프 사용)
    for event in EXPANSION_EVENTS:
        x_ms = pd.Timestamp(event["date"]).value // 10 ** 6
        fig.add_vline(
            x=x_ms,
            line_dash=event["dash"],
            line_color=event["color"],
            line_width=2,
            annotation_text=event["label"],
            annotation_position="top left",
            annotation_font_color=event["color"],
            annotation_font_size=12,
        )


def render_patch_log():
    if not os.path.exists(PATCH_LOG_FILE):
        return
    df = load_patch_log()
    with st.expander("📅 한밤(Midnight) 패치 로그", expanded=True):
        for _, row in df.iterrows():
            color = CATEGORY_COLOR.get(row['category'], "#888888")
            st.markdown(
                f"`{row['date']}`　"
                f"<span style='background:{color};color:#fff;padding:2px 8px;"
                f"border-radius:4px;font-size:0.75rem'>{row['category']}</span>　"
                f"{row['title']}",
                unsafe_allow_html=True
            )


def render_price_tab(df_wide, df_long):
    latest_col = df_wide.columns[-1]
    left, right = st.columns([1, 2.5])

    with left:
        st.subheader("🛠️ 필터")

        period_label = st.radio("기간", list(PERIODS.keys()), horizontal=True, key="period_price")
        hours = PERIODS[period_label]
        if hours:
            cutoff = df_long['수집시각'].max() - pd.Timedelta(hours=hours)
            df_period = df_long[df_long['수집시각'] >= cutoff]
        else:
            df_period = df_long

        show_events = st.checkbox("이벤트 로그 표시", value=True, key="events_price")

        selected_items = st.multiselect(
            "분석 품목",
            sorted(df_wide.index.unique()),
            default=['WoW 토큰'] if 'WoW 토큰' in df_wide.index else [],
            key="items_price"
        )

        st.write("📋 **현재 시세 (Gold)**")
        display_df = df_wide[[latest_col]].sort_values(by=latest_col, ascending=False)
        display_df.columns = ["시세"]
        st.dataframe(display_df, use_container_width=True, height=300)

    with right:
        st.subheader(f"📈 시세 변화 흐름 — {period_label}")
        if not selected_items:
            st.info("👆 왼쪽에서 분석할 품목을 선택하세요.")
        else:
            plot_df = df_period[df_period['품목명'].isin(selected_items)].dropna()
            if plot_df.empty:
                st.warning("선택한 기간에 데이터가 없습니다.")
            else:
                show_markers = plot_df['수집시각'].nunique() <= 72
                fig = px.line(
                    plot_df, x='수집시각', y='value', color='품목명',
                    markers=show_markers, line_shape='spline',
                    labels={'value': '시세 (Gold)', '수집시각': '시간'}
                )
                fig.update_layout(
                    template="plotly_white", hovermode="x unified", height=450,
                    xaxis=dict(type='date', tickformat="%m-%d %H:%M", nticks=10),
                    legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                x_min, x_max = plot_df['수집시각'].min(), plot_df['수집시각'].max()
                if show_events:
                    add_event_lines(fig)
                fig.update_layout(xaxis_range=[x_min, x_max])
                st.plotly_chart(fig, use_container_width=True)


def render_market_discovery(df_wide, df_long, df_vol_wide):
    st.caption("게임을 몰라도 — 데이터가 스스로 가리키는 주요 아이템")

    mean_price = df_wide.mean(axis=1)
    std_price  = df_wide.std(axis=1)
    cv         = (std_price / mean_price).replace([float('inf'), -float('inf')], pd.NA).dropna()

    tab_a, tab_b, tab_c = st.tabs(["💰 시세 기준", "📦 등록량 기준", "📈 변동성 기준"])

    with tab_a:
        st.markdown("**평균 시세 상위 품목** — 경제적 가치가 높은 아이템")
        st.caption("시세가 높다 = 수요 대비 공급이 적은 희소 재료일 가능성")
        stats_a = pd.DataFrame({
            '평균 시세 (G)': mean_price.round(1),
            '최고가 (G)':    df_wide.max(axis=1).round(1),
            '최저가 (G)':    df_wide.min(axis=1).round(1),
        }).sort_values('평균 시세 (G)', ascending=False).head(20)
        st.dataframe(stats_a.style.format('{:,.1f}'), use_container_width=True, height=420)

    with tab_b:
        if df_vol_wide is None:
            st.error("등록량 데이터가 없습니다.")
        else:
            st.markdown("**평균 등록량 상위 품목** — 시장에서 가장 활발히 유통되는 아이템")
            st.caption("등록량이 많고 안정적 = 꾸준히 소비되는 핵심 소모 재료일 가능성")
            vol_mean = df_vol_wide.mean(axis=1)
            vol_cv   = (df_vol_wide.std(axis=1) / vol_mean).replace([float('inf'), -float('inf')], pd.NA)
            stats_b = pd.DataFrame({
                '평균 등록량':     vol_mean.round(0),
                '등록량 변동계수': vol_cv.round(3),
                '최대 등록량':     df_vol_wide.max(axis=1).round(0),
            }).sort_values('평균 등록량', ascending=False).head(20)
            fmt_b = {'평균 등록량': '{:,.0f}', '등록량 변동계수': '{:.3f}', '최대 등록량': '{:,.0f}'}
            st.dataframe(stats_b.style.format(fmt_b), use_container_width=True, height=420)

    with tab_c:
        st.markdown("**가격 변동계수 상위 품목** — 시장 충격에 민감하게 반응하는 아이템")
        st.caption("변동계수(CV) = 표준편차 / 평균. 높을수록 패치·이벤트의 영향을 크게 받음")
        stats_c = pd.DataFrame({
            '변동계수 (CV)': cv.round(3),
            '평균 시세 (G)': mean_price.round(1),
            '표준편차 (G)': std_price.round(1),
        }).sort_values('변동계수 (CV)', ascending=False).head(20)
        fmt_c = {'변동계수 (CV)': '{:.3f}', '평균 시세 (G)': '{:,.1f}', '표준편차 (G)': '{:,.1f}'}
        st.dataframe(stats_c.style.format(fmt_c), use_container_width=True, height=420)

    # 발굴 품목 시세 빠른 조회
    st.divider()
    st.markdown("**🔎 품목 시세 빠른 조회**")
    st.caption("위 표에서 관심 품목을 발견했다면 여기서 시세 흐름을 바로 확인하세요.")
    selected = st.selectbox("품목 선택", sorted(df_wide.index.unique()), key="discovery_item")
    if selected:
        plot_df = df_long[df_long['품목명'] == selected].dropna()
        fig = px.line(
            plot_df, x='수집시각', y='value',
            labels={'value': '시세 (Gold)', '수집시각': '시간'},
            line_shape='spline'
        )
        fig.update_layout(
            template="plotly_white", hovermode="x unified", height=350,
            xaxis=dict(type='date', tickformat="%m-%d", nticks=10)
        )
        add_event_lines(fig)
        fig.update_layout(xaxis_range=[plot_df['수집시각'].min(), plot_df['수집시각'].max()])
        st.plotly_chart(fig, use_container_width=True)


def render_patch_analysis(df_long):
    event_labels = [e["label"] for e in EXPANSION_EVENTS]
    selected_label = st.radio("패치 이벤트", event_labels, horizontal=True, key="patch_event")
    event_date = pd.Timestamp(next(e["date"] for e in EXPANSION_EVENTS if e["label"] == selected_label))

    window_hours = {"24시간": 24, "48시간": 48, "7일": 168}[
        st.radio("비교 구간", ["24시간", "48시간", "7일"], horizontal=True, key="patch_window")
    ]

    before_df = df_long[
        (df_long['수집시각'] >= event_date - pd.Timedelta(hours=window_hours)) &
        (df_long['수집시각'] <  event_date)
    ].dropna(subset=['value'])

    after_df = df_long[
        (df_long['수집시각'] >= event_date) &
        (df_long['수집시각'] <  event_date + pd.Timedelta(hours=window_hours))
    ].dropna(subset=['value'])

    before_avg   = before_df.groupby('품목명')['value'].mean()
    before_count = before_df.groupby('품목명')['value'].count()
    after_avg    = after_df.groupby('품목명')['value'].mean()

    result = pd.DataFrame({
        '패치 전 평균 (G)': before_avg,
        '패치 후 평균 (G)': after_avg,
        '패치 전 데이터 수': before_count,
    }).dropna()

    result['변화율 (%)'] = (
        (result['패치 후 평균 (G)'] - result['패치 전 평균 (G)']) / result['패치 전 평균 (G)'] * 100
    ).round(2)

    min_count = st.slider(
        "패치 전 최소 데이터 수",
        min_value=1, max_value=int(window_hours), value=max(1, window_hours // 4),
        help="이 값 미만인 품목은 패치 전 데이터가 부족한 신규 아이템으로 간주하여 제외합니다."
    )
    result = result[result['패치 전 데이터 수'] >= min_count].sort_values('변화율 (%)')

    fmt = {
        '패치 전 평균 (G)': '{:,.1f}',
        '패치 후 평균 (G)': '{:,.1f}',
        '패치 전 데이터 수': '{:.0f}',
        '변화율 (%)': '{:+.2f}%',
    }

    if result.empty:
        st.warning("조건을 만족하는 품목이 없습니다. 최소 데이터 수를 낮춰보세요.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**📉 급락 TOP 10** — {selected_label} 전후 {window_hours}시간")
        st.dataframe(result.head(10).style.format(fmt), use_container_width=True)
    with col2:
        st.markdown(f"**📈 급등 TOP 10** — {selected_label} 전후 {window_hours}시간")
        st.dataframe(result.tail(10).iloc[::-1].style.format(fmt), use_container_width=True)

    with st.expander("📋 전체 품목 변화율"):
        st.dataframe(result.style.format(fmt), use_container_width=True)


# ── 메인 ────────────────────────────────────────────────────────────────────

if not os.path.exists(HISTORY_FILE):
    st.error("데이터 파일이 없습니다.")
    st.stop()

df_price, df_price_long = load_data(HISTORY_FILE)
df_vol_wide = load_data(VOLUME_FILE)[0] if os.path.exists(VOLUME_FILE) else None

latest_col  = df_price.columns[-1]
token_price = df_price.loc['WoW 토큰', latest_col] if 'WoW 토큰' in df_price.index else 0

# 전 시간 대비 토큰 시세 변화 (NaN 방어)
token_delta = None
if 'WoW 토큰' in df_price.index and len(df_price.columns) >= 2:
    token_prev = df_price.loc['WoW 토큰', df_price.columns[-2]]
    if pd.notna(token_prev) and pd.notna(token_price):
        token_delta = token_price - token_prev

st.title("월드 오브 워크래프트 경제 지표")
st.caption(f"마지막 업데이트: **{latest_col} KST** · 1시간 단위 자동 수집")

col1, col2, col3 = st.columns(3)
with col1:
    delta_str = f"{token_delta:+,.0f} G" if token_delta is not None else None
    st.metric("🪙 현재 토큰 시세", f"{token_price:,.0f} G", delta=delta_str)
with col2:
    st.metric("💸 1,000원당 가치", f"{token_price * 1_000 / WOW_TOKEN_KRW:,.0f} G")
with col3:
    st.metric("📦 추적 품목", f"{len(df_price)}개")

st.divider()

tab_price, tab_discovery, tab_patch = st.tabs(["📊 시세 흐름", "📌 품목 발굴", "🔍 패치 임팩트"])

with tab_price:
    render_price_tab(df_price, df_price_long)

with tab_discovery:
    render_market_discovery(df_price, df_price_long, df_vol_wide)

with tab_patch:
    render_patch_analysis(df_price_long)

st.divider()
render_patch_log()
