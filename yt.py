from stopwords import stop_words
from pytube import YouTube
import dailymotion
import requests
import shutil
import os
import re


def upload_to_dailymotion():

    # Delete any videos in the videos folder
    output_path = f'{os.getcwd()}/videos/'
    try:
        shutil.rmtree(output_path)
        os.mkdir(output_path)
    except Exception as e:
        os.mkdir(output_path)

    channel_key = "b2779280c0d27d97a9da"

    removeVideoFromQueue = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeVideoFromQueue"

    getDailyMotionAccount = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getDailyMotionAccount?channelKey={channel_key}"

    account = requests.get(url=getDailyMotionAccount)
    account = account.json()

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

    dm_account_info = dm.get(
        '/me', {'fields': 'id,username,screenname,limits'})

    print(dm_account_info["limits"])

    def getVideo():
        max_video_length = dm_account_info["limits"]["video_duration"]
        getYouTubeVideo = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeVideo?channelKey={channel_key}&maxLength={max_video_length}"

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
        return '[Execution stopped] waiting for limit to raise'

    _thumbnail_url = video["thumbnail_url"]
    _description = video["description"]
    _video_id = video["videoId"]
    _length = video["length"]
    _title = video["title"]
    _tags = video["tags"]

    def handleRemoveVideoFromQueue():
        requests.post(removeVideoFromQueue, data={
                      "queue": account["queryId"]["current"], "videoId": _video_id})

    try:
        # Get videos streams
        yt_download = YouTube(f"https://www.youtube.com/watch?v={_video_id}")

        # Download the youtube video
        yt_download.streams.filter(
            progressive=True,
            file_extension='mp4'
        ).order_by(
            'resolution'
        ).desc().first().download(
            output_path=output_path,
            filename=_video_id
        )
    except Exception as e:
        return handleRemoveVideoFromQueue()

    try:
        url = dm.upload(f'{output_path}{_video_id}.mp4')
    except Exception as e:
        return handleRemoveVideoFromQueue()

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

        handleRemoveVideoFromQueue()
        return '[Video uploaded to dailymotion]'

    except Exception as e:
        return handleRemoveVideoFromQueue()


print(upload_to_dailymotion())
