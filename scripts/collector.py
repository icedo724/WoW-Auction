import requests
import pandas as pd
import os
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 항상 추적할 고정 아이템 (top_20 진입 여부와 무관)
STABLE_TARGETS = {
    122284: 'WoW 토큰',
    210932: '창연',
    221758: '더럽혀진 부싯깃 상자'
}


def get_token():
    # 환경변수 우선, 없으면 로컬 config 파일에서 로드
    client_id = os.getenv('WOW_CLIENT_ID')
    client_secret = os.getenv('WOW_CLIENT_SECRET')
    if not client_id or not client_secret:
        try:
            cid_path = os.path.join(BASE_DIR, 'config', 'clientid.txt')
            sec_path = os.path.join(BASE_DIR, 'config', 'secret.txt')
            with open(cid_path, 'r') as f:
                client_id = f.read().strip()
            with open(sec_path, 'r') as f:
                client_secret = f.read().strip()
        except FileNotFoundError:
            raise RuntimeError("인증 정보를 찾을 수 없습니다. 환경변수 또는 config 파일을 확인하세요.")

    r = requests.post(
        "https://oauth.battle.net/token",
        data={'grant_type': 'client_credentials'},
        auth=(client_id, client_secret),
        timeout=10
    )
    r.raise_for_status()

    access_token = r.json().get('access_token')
    if not access_token:
        raise RuntimeError(f"access_token 발급 실패. 응답: {r.text}")
    return access_token


def get_wow_token_price(token):
    # WoW 토큰 시세 조회 (경매장과 별개인 전용 API 사용)
    url = "https://kr.api.blizzard.com/data/wow/token/index"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()['price'] / 10000
    except Exception as e:
        logger.warning(f"WoW 토큰 시세 조회 실패: {e}")
        return None


def get_item_info(item_id, token):
    # 아이템 한국어 이름 및 대분류(item_class) 조회
    url = f"https://kr.api.blizzard.com/data/wow/item/{item_id}"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "static-kr", "locale": "ko_KR"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        name = data.get('name')
        name = name.get('ko_KR') if isinstance(name, dict) else str(name)
        cls = data.get('item_class', {}).get('name', '')
        item_class = cls.get('ko_KR') if isinstance(cls, dict) else str(cls)
        return name, item_class
    except Exception as e:
        logger.warning(f"아이템 정보 조회 실패 (id={item_id}): {e}")
        return f"ID_{item_id}", ''


def update_csv(file_name, item_dict, value_dict, now_col):
    # CSV에 현재 시각 열 추가 및 저장
    file_path = os.path.join(BASE_DIR, 'data', file_name)
    df = pd.read_csv(file_path, index_col=0) if os.path.exists(file_path) else pd.DataFrame()
    for iid, name in item_dict.items():
        val = value_dict.get(iid)
        if val is not None:
            df.loc[name, now_col] = val
    df.index.name = 'item_name'
    df = df.reindex(columns=sorted(df.columns))
    df.to_csv(file_path, encoding='utf-8-sig')


def collect_master():
    token = get_token()
    now_kst = datetime.now(KST)
    now_col = now_kst.strftime('%Y-%m-%d %H') + ":00"
    logger.info(f"수집 시작: {now_col}")

    # 경매장 commodity 데이터 조회 (서버 전체 통합 시세)
    url = "https://kr.api.blizzard.com/data/wow/auctions/commodities"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        logger.error(f"경매장 API 실패: HTTP {response.status_code} / {response.text[:200]}")
        return

    try:
        raw_data = response.json()['auctions']
    except (KeyError, ValueError) as e:
        logger.error(f"API 응답 파싱 실패: {e}")
        return

    df_raw = pd.DataFrame(raw_data)

    try:
        df_raw['item_id'] = df_raw['item'].apply(lambda x: x['id'])
    except (KeyError, TypeError) as e:
        logger.error(f"item_id 추출 실패: {e}")
        return

    # 등록량 기준 상위 20개 아이템 ID 추출 (신규 아이템 발굴용)
    top_20_ids = df_raw.groupby('item_id')['quantity'].sum().nlargest(20).index.tolist()

    dict_path = os.path.join(BASE_DIR, 'data', 'item_dict.csv')
    if os.path.exists(dict_path):
        df_dict = pd.read_csv(dict_path, index_col='item_id')
        item_dict       = df_dict['item_name'].to_dict()
        item_class_dict = df_dict['item_class'].to_dict() if 'item_class' in df_dict.columns else {}
    else:
        item_dict       = STABLE_TARGETS.copy()
        item_class_dict = {}

    # 신규 아이템 추가
    for iid in top_20_ids:
        if iid not in item_dict:
            name, item_class = get_item_info(iid, token)
            item_dict[iid]       = name
            item_class_dict[iid] = item_class

    # item_class 누락 아이템 백필 (컬럼 신규 추가 시 1회 실행)
    for iid in item_dict:
        if iid not in item_class_dict:
            _, item_class = get_item_info(iid, token)
            item_class_dict[iid] = item_class

    pd.DataFrame({
        'item_id':    list(item_dict.keys()),
        'item_name':  list(item_dict.values()),
        'item_class': [item_class_dict.get(iid, '') for iid in item_dict],
    }).to_csv(dict_path, index=False, encoding='utf-8-sig')

    # unit_price 단위: copper (1G = 10,000 copper) → Gold 변환
    # quantity: 경매장 현재 등록 수량 (거래 완료량 아님, 공급량 지표)
    tracked = df_raw[df_raw['item_id'].isin(item_dict.keys())]
    current_prices = tracked.groupby('item_id')['unit_price'].min() / 10000
    current_volumes = tracked.groupby('item_id')['quantity'].sum()

    # WoW 토큰은 commodity 경매장 외 전용 시스템으로 거래 → 별도 조회
    t_price = get_wow_token_price(token)
    if t_price:
        current_prices[122284] = t_price

    update_csv('market_history.csv', item_dict, current_prices, now_col)
    update_csv('market_volume.csv', item_dict, current_volumes, now_col)
    logger.info(f"수집 완료: {len(item_dict)}개 아이템")


if __name__ == "__main__":
    collect_master()
