# WoW 경매장 경제 지표 대시보드

> **"게임을 몰라도 — 데이터가 스스로 가리키는 주요 아이템"**
>
> 도메인 지식 없이 공개 API 데이터만으로 시장 핵심 품목을 식별하고, 패치 이벤트가 경제에 미치는 영향을 정량화하는 분석 프로젝트입니다.

대시보드: https://wowauction.streamlit.app/

---

## 프로젝트 개요

월드 오브 워크래프트 한국 서버 경매장은 수천 개 아이템이 수요·공급에 따라 실시간으로 가격이 형성되는 시장입니다. 2026년 3월 출시된 **한밤(Midnight) 확장팩**을 기점으로 신규 아이템 대거 등장, 시즌 1 레이드 오픈 등 외부 충격이 연속 발생했으며, 이러한 이벤트가 경제에 미치는 영향을 데이터로 추적합니다.

### 분석 목표

1. **품목 발굴** — 도메인 지식 없이 시세·등록량·변동성 지표만으로 경제적으로 유의미한 아이템 식별
2. **패치 임팩트 정량화** — 확장팩 출시 및 레이드 오픈 전후 가격 변화율 측정
3. **WoW 토큰 분석** — 골드 가치의 원화 환산 및 시세 흐름 패턴 파악

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| 데이터 수집 | Blizzard Battle.net REST API (Commodities AH, Token Index) |
| 수집 자동화 | GitHub Actions (1시간 주기 cron, pip 캐시) |
| 데이터 처리 | Python · Pandas |
| 시각화 | Streamlit · Plotly Express |
| 배포 | Streamlit Community Cloud |

---

## 데이터 파이프라인

```
GitHub Actions (매시 정각)
    └─ scripts/collector.py
        ├─ OAuth 토큰 발급 (client_credentials)
        ├─ Commodities API → 경매장 전체 등록 데이터
        │   ├─ 등록량 기준 상위 20개 아이템 자동 발굴
        │   ├─ 최저 단가(unit_price) → Gold 변환 (÷10,000 copper)
        │   └─ 등록량(quantity) 합산 → 공급량 지표
        ├─ Token Index API → WoW 토큰 전용 시세
        └─ data/market_history.csv, market_volume.csv 누적 저장
```

**수집 데이터 성격 주의**: 경매장 API가 제공하는 `quantity`는 현재 등록된 수량(공급량)이며, 실제 거래 완료량이 아닙니다. 분석 시 "유통 활성도"의 간접 지표로 해석합니다.

---

## 대시보드 구성

### 📊 시세 흐름
- 기간 필터(24h / 3d / 7d / 전체) + 품목 멀티셀렉트
- 확장팩 주요 이벤트 수직선 오버레이 (이벤트 로그 토글)
- 데이터 포인트 수에 따라 마커 자동 on/off

### 📌 품목 발굴
도메인 지식 없이 세 가지 데이터 지표로 주요 아이템 식별

| 서브탭 | 지표 | 해석 |
|---|---|---|
| 💰 시세 기준 | 기간 평균 시세 | 경제적 가치가 높은 희소 재료 |
| 📦 등록량 기준 | 평균 등록량 + 등록량 CV | 꾸준히 소비되는 핵심 소모 재료 |
| 📈 변동성 기준 | 가격 변동계수(CV = σ/μ) | 패치·이벤트에 민감하게 반응하는 아이템 |

하단 "빠른 조회"로 관심 품목의 전체 시세 흐름을 즉시 확인 가능.

### 🔍 패치 임팩트
- 이벤트 선택: 한밤 정식 출시 / 시즌 1 · 루야살 오픈
- 비교 구간: 24h / 48h / 7d
- 패치 전후 평균 가격 변화율 계산 → 급등/급락 TOP 10
- "패치 전 최소 데이터 수" 슬라이더로 신규 아이템 노이즈 제거

---

## 분석 한계 및 해석 주의사항

- 공급량(등록량)은 측정 가능하나 **수요량(실거래량)은 API 미제공**
- 신규 아이템은 패치 전 데이터가 없어 변화율이 극단값으로 산출될 수 있음 → 슬라이더로 필터링
- WoW 토큰 시세는 블리자드가 전용 알고리즘으로 조정하므로 순수 시장 가격이 아님

---

## 로컬 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 인증 정보 설정 (방법 1: 환경변수)
export WOW_CLIENT_ID=your_client_id
export WOW_CLIENT_SECRET=your_client_secret

# 인증 정보 설정 (방법 2: 로컬 파일)
# config/clientid.txt, config/secret.txt 에 저장

# 데이터 수집
python scripts/collector.py

# 대시보드 실행
streamlit run app/main.py
```

---

## 디렉토리 구조

```
wow/
├── app/
│   └── main.py          # Streamlit 대시보드
├── scripts/
│   └── collector.py     # Blizzard API 데이터 수집기
├── data/
│   ├── market_history.csv   # 아이템별 시세 이력 (wide format)
│   ├── market_volume.csv    # 아이템별 등록량 이력 (wide format)
│   ├── item_dict.csv        # 아이템 ID-이름 매핑
│   └── patch_log.csv        # 확장팩 주요 이벤트 로그
├── .github/workflows/
│   └── data_collection.yml  # GitHub Actions 자동 수집 워크플로우
└── requirements.txt
```
