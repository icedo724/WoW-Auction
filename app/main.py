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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE_DIR, 'data', 'market_history.csv')
VOLUME_FILE  = os.path.join(BASE_DIR, 'data', 'market_volume.csv')

# 블리자드 한국 배틀넷 스토어 기준 WoW 토큰 원화 판매 가격
WOW_TOKEN_KRW = 22_000

# 한밤(Midnight) 확장팩 주요 타임라인
EXPANSION_EVENTS = [
    {"date": "2026-02-27", "label": "한밤 얼리 액세스", "color": "#F4A522", "dash": "dash"},
    {"date": "2026-03-02", "label": "한밤 정식 출시",   "color": "#E63946", "dash": "solid"},
]

# 기간 필터 옵션 (label → 시간 수)
PERIODS = {"24시간": 24, "7일": 168, "전체": None}


@st.cache_data(ttl=3600)
def load_csv(file_path):
    return pd.read_csv(file_path, index_col=0)


def to_long(df_wide):
    # wide format → long format 변환
    df_long = df_wide.reset_index().melt(id_vars='index', var_name='수집시각', value_name='value')
    df_long.rename(columns={'index': '품목명'}, inplace=True)
    df_long['수집시각'] = pd.to_datetime(df_long['수집시각'])
    return df_long


def add_event_lines(fig):
    # 확장팩 타임라인 수직선 마킹
    for event in EXPANSION_EVENTS:
        fig.add_vline(
            x=event["date"],
            line_dash=event["dash"],
            line_color=event["color"],
            line_width=2,
            annotation_text=event["label"],
            annotation_position="top left",
            annotation_font_color=event["color"],
            annotation_font_size=12,
        )


def render_tab(df_wide, view_mode, unit):
    df_long = to_long(df_wide)
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
        st.dataframe(display_df, use_container_width=True)

    with right:
        st.subheader(f"📈 {view_mode} 변화 흐름 — {period_label}")

        if not selected_items:
            st.info("👆 왼쪽에서 분석할 품목을 선택하세요.")
        else:
            plot_df = df_period[df_period['품목명'].isin(selected_items)].dropna()
            if plot_df.empty:
                st.warning("선택한 기간에 데이터가 없습니다.")
            else:
                # 데이터 포인트가 많으면 마커 숨김 (72개 = 3일치 기준)
                show_markers = plot_df['수집시각'].nunique() <= 72

                fig = px.line(
                    plot_df, x='수집시각', y='value', color='품목명',
                    markers=show_markers, line_shape='spline',
                    labels={'value': f'{view_mode} ({unit})', '수집시각': '시간'}
                )
                fig.update_layout(
                    template="plotly_white", hovermode="x unified",
                    xaxis=dict(type='date', tickformat="%m-%d %H:%M", nticks=10),
                    legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                add_event_lines(fig)
                st.plotly_chart(fig, use_container_width=True)


# ── 메인 ────────────────────────────────────────────────────────────────────

if not os.path.exists(HISTORY_FILE):
    st.error("데이터 파일이 없습니다.")
    st.stop()

df_price  = load_csv(HISTORY_FILE)
df_volume = load_csv(VOLUME_FILE) if os.path.exists(VOLUME_FILE) else None

latest_col = df_price.columns[-1]
token_price = df_price.loc['WoW 토큰', latest_col] if 'WoW 토큰' in df_price.index else 0

# 전 시간 대비 토큰 시세 변화
if 'WoW 토큰' in df_price.index and len(df_price.columns) >= 2:
    token_prev  = df_price.loc['WoW 토큰', df_price.columns[-2]]
    token_delta = token_price - token_prev
else:
    token_delta = None

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
tab_price, tab_volume = st.tabs(["📊 시세", "📦 등록량"])

with tab_price:
    render_tab(df_price, "시세", "Gold")

with tab_volume:
    if df_volume is not None:
        render_tab(df_volume, "등록량", "개")
    else:
        st.error("등록량 데이터 파일이 없습니다.")
