"""
패치 임팩트 콘솔 분석 스크립트

사용법:
  python scripts/analyze.py                         # 전체 이벤트, 48시간, 상위 10개
  python scripts/analyze.py --event 1 --window 168  # 시즌1 오픈, 7일 구간
  python scripts/analyze.py --search 빛의            # 특정 품목 검색
"""

import argparse
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE_DIR, 'data', 'market_history.csv')

EVENTS = [
    {"label": "한밤 정식 출시",        "date": "2026-03-03"},
    {"label": "시즌 1 · 루야살 오픈",  "date": "2026-03-19"},
]


def load_long():
    df_wide = pd.read_csv(HISTORY_FILE, index_col=0)
    index_col = df_wide.index.name or 'item_name'
    df_long = df_wide.reset_index().melt(id_vars=index_col, var_name='수집시각', value_name='value')
    df_long.rename(columns={index_col: '품목명'}, inplace=True)
    df_long['수집시각'] = pd.to_datetime(df_long['수집시각'])
    return df_long


def patch_impact(df_long, event_date, window_hours, min_count):
    before = df_long[
        (df_long['수집시각'] >= event_date - pd.Timedelta(hours=window_hours)) &
        (df_long['수집시각'] <  event_date)
    ].dropna(subset=['value'])

    after = df_long[
        (df_long['수집시각'] >= event_date) &
        (df_long['수집시각'] <  event_date + pd.Timedelta(hours=window_hours))
    ].dropna(subset=['value'])

    before_avg   = before.groupby('품목명')['value'].mean()
    before_count = before.groupby('품목명')['value'].count()
    after_avg    = after.groupby('품목명')['value'].mean()

    result = pd.DataFrame({
        '패치 전 평균 (G)': before_avg,
        '패치 후 평균 (G)': after_avg,
        '데이터 수':        before_count,
    }).dropna()

    result['변화율 (%)'] = (
        (result['패치 후 평균 (G)'] - result['패치 전 평균 (G)']) / result['패치 전 평균 (G)'] * 100
    ).round(2)

    return result[result['데이터 수'] >= min_count].sort_values('변화율 (%)')


def print_table(df, title, n=10):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")
    fmt = df[['패치 전 평균 (G)', '패치 후 평균 (G)', '변화율 (%)']].copy()
    fmt['패치 전 평균 (G)'] = fmt['패치 전 평균 (G)'].map('{:>10,.1f} G'.format)
    fmt['패치 후 평균 (G)'] = fmt['패치 후 평균 (G)'].map('{:>10,.1f} G'.format)
    fmt['변화율 (%)']       = fmt['변화율 (%)'].map('{:>+8.2f}%'.format)
    print(fmt.head(n).to_string())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--event',  type=int, default=0,   help='이벤트 번호 (0=한밤 출시, 1=시즌1 오픈)')
    parser.add_argument('--window', type=int, default=48,  help='비교 구간 (시간, 기본 48)')
    parser.add_argument('--top',    type=int, default=10,  help='출력 건수 (기본 10)')
    parser.add_argument('--min',    type=int, default=None,help='패치 전 최소 데이터 수 (기본 window//4)')
    parser.add_argument('--search', type=str, default=None,help='품목명 검색 키워드')
    args = parser.parse_args()

    event      = EVENTS[args.event]
    event_date = pd.Timestamp(event["date"])
    min_count  = args.min if args.min is not None else max(1, args.window // 4)

    print(f"\n이벤트  : {event['label']} ({event['date']})")
    print(f"비교구간: 전후 {args.window}시간 | 최소 데이터: {min_count}개")

    df_long = load_long()
    result  = patch_impact(df_long, event_date, args.window, min_count)

    if result.empty:
        print("\n조건을 만족하는 품목이 없습니다.")
        return

    if args.search:
        matched = result[result.index.str.contains(args.search, case=False, na=False)]
        print_table(matched, f'[검색] "{args.search}" 결과 (변화율 오름차순)', n=len(matched))
    else:
        print_table(result.head(args.top),            f'[급락] TOP {args.top}')
        print_table(result.tail(args.top).iloc[::-1], f'[급등] TOP {args.top}')

    print(f"\n총 {len(result)}개 품목 분석 완료\n")


if __name__ == "__main__":
    main()
