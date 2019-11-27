from datetime import datetime, timedelta
from current_channel import _channel_key
from stopwords import stop_words
from pytube import YouTube
import dateutil.parser
import dailymotion
import requests
import shutil
import pytz
import time
import json
import os
import re

removeVideoFromQueue = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeVideoFromQueue"

updateChannelUploadStatusUrl = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateChannelUploadStatus"


def updateChannelUploadStatus(channel_key, status):
    return requests.post(updateChannelUploadStatusUrl, data={"channelKey": channel_key, "uploadStatus": json.dumps(status)})


def handleRemoveVideoFromQueue(queue, video_id, channel_key, limits):
    return requests.post(removeVideoFromQueue, data={
        "queue": queue, "videoId": video_id, "channelKey": channel_key, "limits": json.dumps(limits)})


def upload_to_dailymotion():

    # Delete any videos in the videos folder
    output_path = f'{os.getcwd()}/videos/'

    getDailyMotionAccount = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={_channel_key}"

    account = requests.get(url=getDailyMotionAccount)
    account = account.json()
    print('[ChannelAccount info]        ', account, '\n')

    _is_limited = account['uploadStatus']['isLimited']
    _limited_at = account['uploadStatus']['limitedAt']

    if _is_limited:
        _now = datetime.now(pytz.timezone('Africa/Nairobi'))
        print(_now)
        if _now-timedelta(hours=24) <= dateutil.parser.parse(account['uploadStatus']['limitedAt']) <= _now:
            data = {
                "code": 420, "message": "Chilling: waiting on upload limit to be lifted", "videoId": None, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            return updateChannelUploadStatus(_channel_key, data)
        else:
            data = {
                "code": 500, "message": "Here We Go!: upload limit lifted", "videoId": None, "isLimited": False, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)

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

    time.sleep(2)

    def getVideo():
        getYouTubeVideo = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeVideo?channelKey={_channel_key}&maxLength={_max_video_length}"

        res = requests.get(url=getYouTubeVideo)
        res = res.json()
        print('[YouTube Video       ]', res, '\n')

        if res["action"] == 200:
            return res["video"]

        elif res["action"] == 205:
            time.sleep(100)
            return getVideo()

        elif res["action"] == 420:
            return "wait"

    video = getVideo()

    time.sleep(2)

    if video == "wait":
        data = {
            "code": 420, "message": "Slowing down, limited upload minutes left", "videoId": None, "isLimited": _is_limited, "limitedAt": _limited_at}
        print('[Status --        ]', data, '\n')
        return updateChannelUploadStatus(_channel_key, data)

    _thumbnail_url = video["thumbnail_url"]
    _description = video["description"]
    _video_id = video["videoId"]
    _video_length = video["length"]
    _title = video["title"]
    _tags = video["tags"]

    def download_video():
        for x in range(5):
            time.sleep(20)
            try:
                shutil.rmtree(output_path)
                os.mkdir(output_path)
            except Exception as e:
                download_video()

            try:
                # Get videos streams
                yt_download = YouTube(
                    f"https://www.youtube.com/watch?v={_video_id}")

                # Download the youtube video
                streams = yt_download.streams.filter(
                    progressive=True,
                    file_extension='mp4'
                ).order_by(
                    'resolution'
                ).desc()

                stream = streams[x]

                _video_size = stream.filesize

                if(_video_size > _max_video_size):
                    data = {
                        "code": 420, "message": "Slowing down, Video upload size remaining", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                    print('[Status --        ]', data, '\n')
                    return updateChannelUploadStatus(_channel_key, data)

                stream.download(
                    output_path=output_path,
                    filename=_video_id
                )

                return _video_size
            except Exception as e:
                print(e + '\n')
                data = {
                    "code": 303, "message": f"Error: downloading video failed, retrying count {x}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                print('[Status --        ]', data, '\n')
                updateChannelUploadStatus(_channel_key, data)
                if "This video is unavailable" in e.message:
                    return handleRemoveVideoFromQueue(
                        _queue, _video_id, channel_key=None, limits={})
        else:
            data = {
                "code": 400, "message": "Error: downloading video failed", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            handleRemoveVideoFromQueue(
                _queue, _video_id, channel_key=None, limits={})
            updateChannelUploadStatus(_channel_key, data)
            time.sleep(5)
            return upload_to_dailymotion()

    _video_size = download_video()
    print('[Video Downloaded successfully   ]', '\n')

    try:
        url = dm.upload(f'{output_path}{_video_id}.mp4')
    except Exception as e:
        print(e)
        data = {
            "code": 500, "message": "Error: Uploading video failed", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
        updateChannelUploadStatus(_channel_key, data)
        print('[Status --        ]', data, '\n')
        return handleRemoveVideoFromQueue(_queue, _video_id, channel_key=None, limits={})

    time.sleep(2)
    print('[Video Uploaded successfully   ]', '\n')

    rx = re.compile(r'[A-Za-z]+')
    tw = rx.findall(_title)
    title_tags = list(
        set([word for word in tw if word.lower() not in stop_words and len(word) > 2]))

    dw = rx.findall(_description)
    description_tags = list(set(
        [word for word in dw if word.lower() not in stop_words and len(word) > 2]))

    _player_next_video = dm.get('/videos', {
        'fields': 'id',
        'sort': 'recent',
        'owners': account["credentials"]["userName"]
    })['list'][0]['id']  # This is a video id

    _limits = {
        "videoDuration": _max_video_length - _video_length,
        "videoSize": _max_video_size - _video_size
    }

    final_tags = list(set([tag for tag in list(
        _tags + title_tags + description_tags) if tag.lower() not in stop_words and len(tag) > 2]))

    try:
        dm.post('/me/videos',
                {
                    'url': url,
                    'title': _title,
                    'description': _description,
                    'player_next_video': _player_next_video,
                    'tags': ','.join(final_tags[:35]),
                    'thumbnail_url': _thumbnail_url,
                    'published': 'true',
                    'channel': 'tv',
                })

        data = {
            "code": 200, "message": "Success: Video uploaded to dailymotion", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
        print('[Status --        ]', data, '\n')
        updateChannelUploadStatus(_channel_key, data)
        handleRemoveVideoFromQueue(_queue, _video_id, _channel_key, _limits)

        return '[Video uploaded to dailymotion]'

    except Exception as e:
        if 'access_forbidden: You reached your upload rate limit' in e.message:
            data = {
                "code": 420, "message": f"Error: Publishing video failed =>  Reason: {e}", "videoId": _video_id, "isLimited": True,
                "limitedAt": f"{datetime.now(pytz.timezone('Africa/Nairobi'))}"}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
        else:
            data = {
                "code": 400, "message": f"Error: Publishing video failed =>  Reason: {e}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
            handleRemoveVideoFromQueue(
                _queue, _video_id, _channel_key, _limits)

        return "[Error publishing video]"


upload_to_dailymotion()
