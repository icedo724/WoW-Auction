import requests
import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STABLE_TARGETS = {
    122284: 'WoW 토큰',
    210932: '창연',
    221758: '더럽혀진 부싯깃 상자'
}


def get_token():
    cid_path = os.path.join(BASE_DIR, 'config', 'clientid.txt')
    sec_path = os.path.join(BASE_DIR, 'config', 'secret.txt')
    with open(cid_path, 'r') as f: client_id = f.read().strip()
    with open(sec_path, 'r') as f: client_secret = f.read().strip()
    r = requests.post("https://oauth.battle.net/token",
                      data={'grant_type': 'client_credentials'}, auth=(client_id, client_secret))
    return r.json().get('access_token')


def get_wow_token_price(token):
    url = "https://kr.api.blizzard.com/data/wow/token/index"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json().get('price') / 10000  # Gold 단위
    except:
        pass
    return None


def get_item_name(item_id, token):
    url = f"https://kr.api.blizzard.com/data/wow/item/{item_id}"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "static-kr", "locale": "ko_KR"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            name = r.json().get('name')
            return name.get('ko_KR') if isinstance(name, dict) else str(name)
    except:
        pass
    return f"ID_{item_id}"


def collect_master():
    token = get_token()
    now_col = datetime.now().strftime('%Y-%m-%d %H') + ":00"

    url = "https://kr.api.blizzard.com/data/wow/auctions/commodities"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        raw_data = response.json()['auctions']
        df_raw = pd.DataFrame(raw_data)
        df_raw['item_id'] = df_raw['item'].apply(lambda x: x['id'])

        raw_dir = os.path.join(BASE_DIR, 'data', 'raw')
        os.makedirs(raw_dir, exist_ok=True)
        df_raw.to_csv(os.path.join(raw_dir, f"snapshot_{datetime.now().strftime('%Y%m%d_%H')}.csv"), index=False,
                      encoding='utf-8-sig')

        top_20_ids = df_raw.groupby('item_id')['quantity'].sum().nlargest(20).index.tolist()
        dict_path = os.path.join(BASE_DIR, 'data', 'item_dict.csv')
        item_dict = pd.read_csv(dict_path, index_col='item_id')['item_name'].to_dict() if os.path.exists(
            dict_path) else STABLE_TARGETS.copy()

        for iid in top_20_ids:
            if iid not in item_dict:
                item_dict[iid] = get_item_name(iid, token)
        pd.DataFrame(list(item_dict.items()), columns=['item_id', 'item_name']).to_csv(dict_path, index=False,
                                                                                       encoding='utf-8-sig')

        current_prices = df_raw[df_raw['item_id'].isin(item_dict.keys())].groupby('item_id')['unit_price'].min() / 10000
        t_price = get_wow_token_price(token)
        if t_price: current_prices[122284] = t_price

        history_file = os.path.join(BASE_DIR, 'data', 'market_history.csv')
        if os.path.exists(history_file):
            df_history = pd.read_csv(history_file, index_col=0)
            if '창연(Bismuth)' in df_history.index: df_history = df_history.drop('창연(Bismuth)')
        else:
            df_history = pd.DataFrame()

        for iid, name in item_dict.items():
            price = current_prices.get(iid)
            if price is not None:
                df_history.loc[name, now_col] = price

        df_history.index.name = 'item_name'
        df_history = df_history.reindex(columns=sorted(df_history.columns))
        df_history.to_csv(history_file, encoding='utf-8-sig')

        print(f"✅ {now_col} 수집 완료")
        print(f"💰 현재 WoW 토큰 시세: {t_price} Gold")
    else:
        print("❌ API 호출 실패")


if __name__ == "__main__":
    collect_master()