import requests
from base import _channel_key, _base_url

def get_accout():
    url = f"{_base_url}/getDailyMotionAccount?channelKey={_channel_key}"
    res = requests.get(url)
    print(res)
    account = res.json()
    return account

# git pull https://github.com/IreriVIkki2/dt-python.git
