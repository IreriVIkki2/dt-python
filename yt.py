from stopwords import stop_words
from pytube import YouTube
import dailymotion
import requests
import shutil
import json
import os
import re

_channel_key = "b2779280c0d27d97a9da"
removeVideoFromQueue = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeVideoFromQueue"

updateChannelUploadStatusUrl = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateChannelUploadStatus"


def updateChannelUploadStatus(channel_key, status):
    return requests.post(updateChannelUploadStatusUrl, data={"channelKey": channel_key, "uploadStatus": json.dumps(status)})


def handleRemoveVideoFromQueue(queue, video_id, channel_key, limits):
    return requests.post(removeVideoFromQueue, data={
        "queue": queue, "videoId": video_id, "channelKey": channel_key, "limits": json.dumps(_limits)})


def upload_to_dailymotion():

    # Delete any videos in the videos folder
    output_path = f'{os.getcwd()}/videos/'
    try:
        shutil.rmtree(output_path)
        os.mkdir(output_path)
    except Exception as e:
        os.mkdir(output_path)

    getDailyMotionAccount = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"

    account = requests.get(url=getDailyMotionAccount)
    account = account.json()
    print(account)

    _queue = account["queryId"]["current"]
    _max_video_length = account["limits"]["videoDuration"]
    _max_video_size = account["limits"]["videoSize"]
    _api_key = account["credentials"]["apiKey"]
    _api_secret = account["credentials"]["apiSecret"]
    _scope = ['manage_videos', "userinfo"]
    _info = {'username': account["credentials"]["userName"],
             'password': account["credentials"]["password"]}

    dm = dailymotion.Dailymotion()
    dm.set_grant_type(
        'password',
        api_key=_api_key,
        api_secret=_api_secret,
        scope=_scope,
        info=_info
    )

    def getVideo():
        getYouTubeVideo = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeVideo?channelKey={_channel_key}&maxLength={_max_video_length}"

        res = requests.get(url=getYouTubeVideo)
        res = res.json()

        if res["action"] == 200:
            return res["video"]

        elif res["action"] == 205:
            return getVideo()

        elif res["action"] == 420:
            return "wait"

    video = getVideo()
    print(video)

    if video == "wait":
        data = {
            "code": 420, "message": "Slowing down, limited upload minutes left", "videoId": None}
        return updateChannelUploadStatus(_channel_key, data)

    _thumbnail_url = video["thumbnail_url"]
    _description = video["description"]
    _video_id = video["videoId"]
    _video_length = video["length"]
    _title = video["title"]
    _tags = video["tags"]
    _video_size = 0

    if(_description == "null"):
        _description = _title

    try:
        # Get videos streams
        yt_download = YouTube(f"https://www.youtube.com/watch?v={_video_id}")

        # Download the youtube video
        stream = yt_download.streams.filter(
            progressive=True,
            file_extension='mp4'
        ).order_by(
            'resolution'
        ).desc().first()

        _video_size += stream.filesize

        if(_video_size > _max_video_size):
            data = {
                "code": 420, "message": "Slowing down, Video upload size remaining", "videoId": _video_id}
            return updateChannelUploadStatus(_channel_key, data)

        stream.download(
            output_path=output_path,
            filename=_video_id
        )
    except Exception as e:
        data = {
            "code": 500, "message": "Error: Downloading video failed", "videoId": _video_id}
        updateChannelUploadStatus(_channel_key, data)
        return handleRemoveVideoFromQueue(_queue, _video_id)

    try:
        url = dm.upload(f'{output_path}{_video_id}.mp4')
    except Exception as e:
        data = {
            "code": 500, "message": "Error: Uploading video failed", "videoId": _video_id}
        updateChannelUploadStatus(_channel_key, data)
        return handleRemoveVideoFromQueue(_queue, _video_id)

    rx = re.compile(r'[A-Za-z]+')
    tw = rx.findall(_title)
    title_tags = list(
        set([word for word in tw if word not in stop_words and len(word) > 2]))

    dw = rx.findall(_description)
    description_tags = list(set(
        [word for word in dw if word not in stop_words and len(word) > 2]))

    _player_next_video = dm.get('/videos', {
        'fields': 'id',
        'sort': 'recent',
        'owners': account["credentials"]["userName"]
    })['list'][0]['id']  # This is a video id

    _limits = {
        "videoDuration": _max_video_length - _video_length,
        "videoSize": _max_video_size - _video_size
    }

    try:
        dm.post('/me/videos',
                {
                    'url': url,
                    'title': _title,
                    'description': _description,
                    'player_next_video': _player_next_video,
                    'tags': list(set(title_tags + description_tags + _tags)),
                    'thumbnail_url': _thumbnail_url,
                    'published': 'true',
                    'channel': 'tv',
                })

        data = {
            "code": 200, "message": "Success: Video uploaded to dailymotion", "videoId": _video_id}

        updateChannelUploadStatus(_channel_key, data)
        handleRemoveVideoFromQueue(_queue, _video_id, _channel_key, _limits)

        return '[Video uploaded to dailymotion]'

    except Exception as e:
        data = {
            "code": 500, "message": "Error: Publishing video failed", "videoId": _video_id}
        updateChannelUploadStatus(_channel_key, data)
        handleRemoveVideoFromQueue(_queue, _video_id, _channel_key, _limits)
        return "[Error publishing video]"


# upload_to_dailymotion()
