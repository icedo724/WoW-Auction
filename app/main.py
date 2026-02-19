import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
st.set_page_config(page_title="WoW 2026 경제 지표", layout="wide")

midnight_release = datetime(2026, 3, 2)
d_day = (midnight_release - datetime.now()).days
st.sidebar.metric("⚔️ Midnight 확장팩 출시", f"D-{d_day}")

st.title("🏹 WoW 2026 실시간 시장 분석")

history_file = os.path.join(BASE_DIR, 'data', 'market_history.csv')

if os.path.exists(history_file):
    df_wide = pd.read_csv(history_file, index_col='item_name')
    df_long = df_wide.reset_index().melt(id_vars='item_name', var_name='timestamp', value_name='price_gold')
    df_long['timestamp'] = pd.to_datetime(df_long['timestamp'])

    items = sorted(df_long['item_name'].unique())
    selected = st.multiselect("분석 대상 선택", items, default=items[:3])

    plot_df = df_long[df_long['item_name'].isin(selected)].dropna()
    if not plot_df.empty:
        fig = px.line(plot_df, x='timestamp', y='price_gold', color='item_name', markers=True)
        fig.update_layout(yaxis_title="가격 (Gold)", xaxis_title="수집 시점")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 최근 시세 변동 현황")
    st.dataframe(df_wide.iloc[:, -5:], use_container_width=True)
else:
    st.info("데이터가 아직 없습니다. 수집기를 먼저 실행해 주세요.")