from base import _channel_key, _base_url
import requests

resetChannelLimitsUrl = f"{_base_url}/resetChannelLimits"


def resetChannelLimits(channel_key):
    requests.post(resetChannelLimitsUrl, data={"channelKey": channel_key})
    return '[Channel has been reset, upload can resume]'


resetChannelLimits(_channel_key)
