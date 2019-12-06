import requests

_channel_key = ""

get_youtube_apikey_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeApiKey"


def get_api_key():
    res = requests.get(get_youtube_apikey_url)
    api_key = res.json()
    return api_key["key"]


def get_accout():
    url = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"
    res = requests.get(url)
    print(res)
    account = res.json()
    return account


api_key = get_api_key()
account = get_accout()
