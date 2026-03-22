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
    # 확장팩 타임라인 수직선 마킹
    # Plotly 신버전은 날짜 문자열 대신 밀리초 타임스탬프 필요
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


def render_tab(file_path, view_mode, unit):
    df_wide, df_long = load_data(file_path)
    latest_col = df_wide.columns[-1]

    left, right = st.columns([1, 2.5])

    with left:
        st.subheader("🛠️ 필터")

        # 기간 필터
        period_label = st.radio(
            "기간", list(PERIODS.keys()), horizontal=True, key=f"period_{view_mode}"
        )
        hours = PERIODS[period_label]
        if hours:
            cutoff = df_long['수집시각'].max() - pd.Timedelta(hours=hours)
            df_period = df_long[df_long['수집시각'] >= cutoff]
        else:
            df_period = df_long

        # 이벤트 로그 표시 토글
        show_events = st.checkbox("이벤트 로그 표시", value=True, key=f"events_{view_mode}")

        # 품목 선택
        selected_items = st.multiselect(
            "분석 품목",
            sorted(df_wide.index.unique()),
            default=['WoW 토큰'] if 'WoW 토큰' in df_wide.index else [],
            key=f"items_{view_mode}"
        )

        # 현재 시세/등록량 테이블
        st.write(f"📋 **현재 {view_mode} ({unit})**")
        display_df = df_wide[[latest_col]].sort_values(by=latest_col, ascending=False)
        display_df.columns = [view_mode]
        st.dataframe(display_df, use_container_width=True, height=300)

    with right:
        st.subheader(f"📈 {view_mode} 변화 흐름 — {period_label}")

        if not selected_items:
            st.info("👆 왼쪽에서 분석할 품목을 선택하세요.")
        else:
            plot_df = df_period[df_period['품목명'].isin(selected_items)].dropna()
            if plot_df.empty:
                st.warning("선택한 기간에 데이터가 없습니다.")
            else:
                # 3일(72 시점) 초과 시 마커 숨김
                show_markers = plot_df['수집시각'].nunique() <= 72

                fig = px.line(
                    plot_df, x='수집시각', y='value', color='품목명',
                    markers=show_markers, line_shape='spline',
                    labels={'value': f'{view_mode} ({unit})', '수집시각': '시간'}
                )
                fig.update_layout(
                    template="plotly_white", hovermode="x unified",
                    height=450,
                    xaxis=dict(type='date', tickformat="%m-%d %H:%M", nticks=10),
                    legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                x_min = plot_df['수집시각'].min()
                x_max = plot_df['수집시각'].max()
                if show_events:
                    add_event_lines(fig)
                # vline이 x축 범위를 확장하지 못하도록 데이터 범위로 고정
                fig.update_layout(xaxis_range=[x_min, x_max])
                st.plotly_chart(fig, use_container_width=True)


def render_patch_analysis(df_long):
    # 이벤트 및 비교 구간 선택
    event_labels = [e["label"] for e in EXPANSION_EVENTS]
    selected_label = st.radio("패치 이벤트", event_labels, horizontal=True, key="patch_event")
    event_date = pd.Timestamp(next(e["date"] for e in EXPANSION_EVENTS if e["label"] == selected_label))

    window_hours = {"24시간": 24, "48시간": 48, "7일": 168}[
        st.radio("비교 구간", ["24시간", "48시간", "7일"], horizontal=True, key="patch_window")
    ]

    before_avg = df_long[
        (df_long['수집시각'] >= event_date - pd.Timedelta(hours=window_hours)) &
        (df_long['수집시각'] <  event_date)
    ].groupby('품목명')['value'].mean()

    after_avg = df_long[
        (df_long['수집시각'] >= event_date) &
        (df_long['수집시각'] <  event_date + pd.Timedelta(hours=window_hours))
    ].groupby('품목명')['value'].mean()

    result = pd.DataFrame({'패치 전 평균 (G)': before_avg, '패치 후 평균 (G)': after_avg}).dropna()
    result['변화율 (%)'] = (
        (result['패치 후 평균 (G)'] - result['패치 전 평균 (G)']) / result['패치 전 평균 (G)'] * 100
    ).round(2)
    result = result.sort_values('변화율 (%)')

    fmt = {'패치 전 평균 (G)': '{:,.1f}', '패치 후 평균 (G)': '{:,.1f}', '변화율 (%)': '{:+.2f}%'}

    if result.empty:
        st.warning("해당 구간에 데이터가 없습니다.")
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
latest_col   = df_price.columns[-1]
token_price  = df_price.loc['WoW 토큰', latest_col] if 'WoW 토큰' in df_price.index else 0

# 전 시간 대비 토큰 시세 변화 (NaN 방어)
token_delta = None
if 'WoW 토큰' in df_price.index and len(df_price.columns) >= 2:
    token_prev = df_price.loc['WoW 토큰', df_price.columns[-2]]
    if pd.notna(token_prev) and pd.notna(token_price):
        token_delta = token_price - token_prev

# 타이틀 + 마지막 업데이트
st.title("월드 오브 워크래프트 경제 지표")
st.caption(f"마지막 업데이트: **{latest_col} KST** · 1시간 단위 자동 수집")

# 상단 메트릭
col1, col2, col3 = st.columns(3)
with col1:
    delta_str = f"{token_delta:+,.0f} G" if token_delta is not None else None
    st.metric("🪙 현재 토큰 시세", f"{token_price:,.0f} G", delta=delta_str)
with col2:
    st.metric("💸 1,000원당 가치", f"{token_price * 1_000 / WOW_TOKEN_KRW:,.0f} G")
with col3:
    st.metric("📦 추적 품목", f"{len(df_price)}개")

st.divider()

# 탭 전환
tab_price, tab_volume, tab_patch = st.tabs(["📊 시세", "📦 등록량", "🔍 패치 분석"])

with tab_price:
    render_tab(HISTORY_FILE, "시세", "Gold")

with tab_volume:
    if os.path.exists(VOLUME_FILE):
        render_tab(VOLUME_FILE, "등록량", "개")
    else:
        st.error("등록량 데이터 파일이 없습니다.")

with tab_patch:
    render_patch_analysis(df_price_long)

st.divider()
render_patch_log()
