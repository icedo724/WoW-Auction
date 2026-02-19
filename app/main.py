import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

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
    section[data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #EEE; }
    h1, h2, h3, p, span, label { color: #1E1E1E !important; }
    span[data-baseweb="tag"] { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; color: #1E1E1E !important; }
    </style>
    """, unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
history_file = os.path.join(BASE_DIR, 'data', 'market_history.csv')
volume_file = os.path.join(BASE_DIR, 'data', 'market_volume.csv')

st.title("월드 오브 워크래프트 경제 지표")

view_mode = st.radio("분석 모드 선택", ["시세", "거래량"], horizontal=True)
target_file = history_file if "시세" in view_mode else volume_file
unit = "Gold" if "시세" in view_mode else "개"

if os.path.exists(target_file):
    df_wide = pd.read_csv(target_file, index_col=0)
    df_wide.index.name = None
    df_long = df_wide.reset_index().melt(id_vars='index', var_name='수집시각', value_name='value')
    df_long.rename(columns={'index': '품목명'}, inplace=True)
    df_long['수집시각'] = pd.to_datetime(df_long['수집시각'])

    # 상단 메트릭 (시세 데이터 기준 고정)
    if os.path.exists(history_file):
        df_p = pd.read_csv(history_file, index_col=0)
        latest_c = df_p.columns[-1]
        token_p = df_p.loc['WoW 토큰', latest_c] if 'WoW 토큰' in df_p.index else 0
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("🪙 현재 토큰 시세", f"{token_p:,.0f} G")
        with col2: st.metric("💸 1,000원당 가치", f"{(token_p/22000):,.0f} G")
        with col3: st.metric("📦 추적 품목", f"{len(df_wide)}개")

    st.divider()

    left, right = st.columns([1, 2.5])
    with left:
        st.subheader("🛠️ 필터")
        selected_items = st.multiselect("분석 품목", sorted(df_wide.index.unique()), default=['WoW 토큰'] if 'WoW 토큰' in df_wide.index else [])
        st.write(f"📋 **현재 {view_mode} 목록**")
        display_df = df_wide[[df_wide.columns[-1]]].sort_values(by=df_wide.columns[-1], ascending=False)
        display_df.columns = [f"현재 {view_mode} ({unit})"]
        st.dataframe(display_df, use_container_width=True)

    with right:
        st.subheader(f"📈 {view_mode} 변화 흐름")
        plot_df = df_long[df_long['품목명'].isin(selected_items)].dropna()
        if not plot_df.empty:
            fig = px.line(plot_df, x='수집시각', y='value', color='품목명', markers=True, line_shape='spline',
                          labels={'value': f'{view_mode} ({unit})', '수집시각': '시간'})
            fig.update_layout(template="plotly_white", hovermode="x unified",
                              xaxis=dict(type='date', tickformat="%m-%d %H:%M", nticks=10),
                              legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
else:
    st.error("데이터 파일이 없습니다.")