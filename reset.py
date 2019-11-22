from current_channel import _channel_key
import requests

resetChannelLimitsUrl = "https://us-central1-vimeovids-ireri.cloudfunctions.net/resetChannelLimits"


def resetChannelLimits(channel_key):
    requests.post(resetChannelLimitsUrl, data={"channelKey": channel_key})
    return '[Channel has been reset, upload can resume]'


resetChannelLimits(_channel_key)
