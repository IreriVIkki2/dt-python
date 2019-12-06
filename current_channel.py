import requests

_channel_key = "b035404431ad14acd02c"


def get_accout():
    url = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"
    res = requests.get(url)
    print(res)
    account = res.json()
    return account
