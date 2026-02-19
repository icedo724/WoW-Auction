import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(page_title="WoW 2026 한밤 경제 대시보드", layout="wide")

st.markdown("""
    <style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ffcc00;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
history_file = os.path.join(BASE_DIR, 'data', 'market_history.csv')

midnight_date = datetime(2026, 3, 2)
days_left = (midnight_date - datetime.now()).days
st.sidebar.header("⚔️ 확장팩 정보")
st.sidebar.metric("한밤 출시", f"D-{days_left}일")
st.sidebar.info("매시간 정각에 자동으로 시세를 수집합니다.")

st.title("🏹 WoW 2026 실시간 거래소")

if os.path.exists(history_file):
    # 데이터 로드
    df_wide = pd.read_csv(history_file, index_col='item_name')
    df_long = df_wide.reset_index().melt(id_vars='item_name', var_name='timestamp', value_name='price')
    df_long['timestamp'] = pd.to_datetime(df_long['timestamp'])

    latest_col = df_wide.columns[-1]
    prev_col = df_wide.columns[-2] if len(df_wide.columns) > 1 else latest_col

    token_price = df_wide.loc['WoW 토큰', latest_col] if 'WoW 토큰' in df_wide.index else 0
    token_diff = token_price - df_wide.loc['WoW 토큰', prev_col] if 'WoW 토큰' in df_wide.index else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🪙 현재 토큰 시세", f"{token_price:,.0f} G", f"{token_diff:,.0f} G")
    with col2:
        gold_per_won = (token_price / 22000) if token_price > 0 else 0
        st.metric("💸 1,000원당 가치", f"{gold_per_won:,.0f} G")
    with col3:
        tracked_count = len(df_wide)
        st.metric("📦 추적 품목 수", f"{tracked_count}개")
    with col4:
        if len(df_wide.columns) > 1:
            change = ((df_wide[latest_col] - df_wide[prev_col]) / df_wide[prev_col] * 100).fillna(0)
            top_riser = change.idxmax()
            st.metric("🔥 최대 상승 (전시점 대비)", top_riser, f"{change.max():.1f}%")

    st.divider()

    left_col, right_col = st.columns([1, 3])

    with left_col:
        st.subheader("🔍 필터 설정")
        all_items = sorted(df_wide.index.unique())
        default_items = [i for i in ['WoW 토큰', '창연', '더럽혀진 부싯깃 상자'] if i in all_items]
        selected_items = st.multiselect("추적할 아이템", all_items, default=default_items)

        st.write("---")
        st.write("**최신 데이터 테이블**")
        st.dataframe(df_wide[latest_col].sort_values(ascending=False), use_container_width=True)

    with right_col:
        plot_df = df_long[df_long['item_name'].isin(selected_items)].dropna()
        if not plot_df.empty:
            fig = px.line(plot_df, x='timestamp', y='price', color='item_name',
                          markers=True, line_shape='spline',
                          title="📊 아이템별 시세 흐름")
            fig.update_layout(
                hovermode="x unified",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_title="가격 (Gold)",
                xaxis_title=""
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("아이템을 선택해 주세요.")

else:
    st.error("데이터 파일(`market_history.csv`)을 찾을 수 없습니다. 수집기를 먼저 가동해 주세요!")