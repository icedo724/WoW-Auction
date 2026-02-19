import requests
import pandas as pd
import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STABLE_TARGETS = {
    122284: 'WoW 토큰',
    210932: '창연',
    221758: '더럽혀진 부싯깃 상자'
}

def get_token():
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
            raise Exception("인증 정보를 찾을 수 없습니다.")
    r = requests.post("https://oauth.battle.net/token", data={'grant_type': 'client_credentials'},
                      auth=(client_id, client_secret))
    return r.json().get('access_token')


def get_wow_token_price(token):
    url = "https://kr.api.blizzard.com/data/wow/token/index"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            return r.json().get('price') / 10000
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
    now_kst = datetime.now(KST)
    now_col = now_kst.strftime('%Y-%m-%d %H') + ":00"

    url = "https://kr.api.blizzard.com/data/wow/auctions/commodities"
    headers = {"Authorization": f"Bearer {token}", "Battlenet-Namespace": "dynamic-kr"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        raw_data = response.json()['auctions']
        df_raw = pd.DataFrame(raw_data)
        df_raw['item_id'] = df_raw['item'].apply(lambda x: x['id'])

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
        current_volumes = df_raw[df_raw['item_id'].isin(item_dict.keys())].groupby('item_id')['quantity'].sum()

        t_price = get_wow_token_price(token)
        if t_price: current_prices[122284] = t_price

        def update_csv(file_name, data_map, value_dict):
            file_path = os.path.join(BASE_DIR, 'data', file_name)
            df = pd.read_csv(file_path, index_col=0) if os.path.exists(file_path) else pd.DataFrame()
            for iid, name in data_map.items():
                val = value_dict.get(iid)
                if val is not None: df.loc[name, now_col] = val
            df.index.name = 'item_name'
            df = df.reindex(columns=sorted(df.columns))
            df.to_csv(file_path, encoding='utf-8-sig')

        update_csv('market_history.csv', item_dict, current_prices)
        update_csv('market_volume.csv', item_dict, current_volumes)


if __name__ == "__main__":
    collect_master()