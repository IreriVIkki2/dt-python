import requests

_channel_key = ""


def get_accout():
    url = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"
    res = requests.get(url)
    print(res)
    account = res.json()
    return account


get_accout = get_accout()
