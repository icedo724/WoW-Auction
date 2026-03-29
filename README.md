# WoW 경매장 경제 지표 대시보드

**[대시보드](https://wowauction.streamlit.app/)**

## 데이터 수집

- **서버:** 대한민국(KR) 리테일(RETAIL) 공용 경매장
- **수집 방법:** Blizzard Battle.net API → GitHub Actions 매시 정각 자동 수집
- **수집 항목:** 아이템 최저 단가(Gold), 등록량, WoW 토큰 시세

---

## 기능

### 시세 추이
- 아이템별 시세(G) 시계열 차트
- 확장팩 출시·시즌 업데이트 이벤트 수직선 표시
- WoW 토큰 시세 흐름 차트

### 품목 발굴
- 등록량 기준 상위 아이템 테이블
- 아이템 분류 필터

### 패치 임팩트
- 이벤트 전후 48시간 가격 변화율 분석
- 급락·급등 상위 10개 품목 표시
- 품목명 키워드 검색

## 분석 리포트
[Notion](https://www.notion.so/miniminimin/32bfbcdaed288053bcfef33ce58e2d14?source=copy_link)
