import requests

_channel_key = "1bce832abe239aaf80a3"


def get_accout():
    url = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"
    res = requests.get(url)
    print(res)
    account = res.json()
    return account

# git pull https://github.com/IreriVIkki2/dt-python.git
