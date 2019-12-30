from current_channel import get_accout, _channel_key
from datetime import datetime, timedelta
from yt_functions import create_queue
from stopwords import stop_words
from pytube import YouTube
import dateutil.parser
import dailymotion
import requests
import shutil
import pytz
import time
import stat
import json
import os
import re


output_path = f'{os.getcwd()}/videos/'

removeVideoFromQueue = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeVideoFromQueue"

updateChannelUploadStatusUrl = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateChannelUploadStatus"


def updateChannelUploadStatus(channel_key, status):
    requests.post(updateChannelUploadStatusUrl, data={
                  "channelKey": channel_key, "uploadStatus": json.dumps(status)})
    time.sleep(4)
    return "updateChannelUploadStatus"


def handleRemoveVideoFromQueue(queue, video_id):
    requests.post(removeVideoFromQueue, data={
        "queue": queue, "videoId": video_id, "channelKey": None, "limits": json.dumps({})})
    time.sleep(4)
    return "handleRemoveVideoFromQueue"


def get_video(_max_video_length):
    getYouTubeVideo = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeVideo?channelKey={_channel_key}&maxLength={_max_video_length}"

    res = requests.get(url=getYouTubeVideo)
    print(res.status_code)
    if res.status_code == 429:
        time.sleep(120)
        return get_video(_max_video_length)

    try:
        res_json = res.json()
    except Exception as e:
        create_queue()
        time.sleep(20)
        return get_video(_max_video_length)

    print('\n', '[Video found]', res_json, '\n')
    action = res_json["action"]

    if action == 205:
        create_queue()
        time.sleep(20)
        return get_video(_max_video_length)

    if action == 200:
        return res_json["video"]

    elif action == 420:
        return action


def upload_to_dailymotion():
    account = get_accout()
    print(account)

    _is_limited = account['uploadStatus']['isLimited']
    _limited_at = account['uploadStatus']['limitedAt']

    if _is_limited:
        _now = datetime.now(pytz.timezone('Africa/Nairobi'))
        if _now-timedelta(hours=24) <= dateutil.parser.parse(account['uploadStatus']['limitedAt']) <= _now:
            data = {
                "code": 420, "message": "Chilling: waiting on upload limit to be lifted", "videoId": None, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            time.sleep(4)
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

    if os.path.isdir(output_path):
        shutil.rmtree(output_path)

    os.mkdir(output_path)

    video = get_video(_max_video_length)

    print("stop me now", video, video["video"])

    if video == 420:
        data = {
            "code": 420, "message": "Slowing down, limited upload minutes left", "videoId": None, "isLimited": _is_limited, "limitedAt": _limited_at}
        print('[Status --        ]', data, '\n')
        return updateChannelUploadStatus(_channel_key, data)

    _description = video["description"]
    _video_id = video["videoId"]
    _video_length = video["length"]
    _title = video["title"]
    _tags = video["tags"]

    # handleRemoveVideoFromQueue(_queue, _video_id)

    def download_video():
        for x in range(5):

            try:
                # Get videos streams
                print('getting video object')
                yt = YouTube(
                    f"https://www.youtube.com/watch?v={_video_id}")

            except:
                data = {
                    "code": 400, "message": "Error: Video unavailabe", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                print('[Status --        ]', data, '\n')
                updateChannelUploadStatus(_channel_key, data)
                time.sleep(4)
                return upload_to_dailymotion()

            try:
                # Download the youtube video
                print('getting streams')
             
                streams = yt.streams.all()

                final_streams = []

                for stream in streams:
                    res_1 = re.findall(r'res="\d+', f"{stream}")
                    if len(res_1) is 0:
                        continue
                    res = int(re.findall(r'\d+', res_1[0])[0])
                    mime = re.findall(r'mime_type="video/\w+', f"{stream}")
                    final_streams.append({
                        "stream":stream,
                        "res":  res,
                        "mime": mime[0].split('mime_type="video/')[-1]
                    })


                final_streams = sorted(final_streams, key = lambda i: ( -i['res'], i['mime']))

                for i in final_streams:
                    print(i['stream'], i['mime'], i['res'], '\n')

                streams = [i['stream'] for i in final_streams]

                if len(streams) is 0:
                    data = {
                        "code": 420, "message": "No downloadable streams found for this video", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                    print('[Status --        ]', data, '\n')
                    updateChannelUploadStatus(_channel_key, data)
                    time.sleep(4)
                    return upload_to_dailymotion()

                if x+1 is len(streams):
                    data = {
                        "code": 420, "message": "Unable to download this video", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                    print('[Status --        ]', data, '\n')
                    updateChannelUploadStatus(_channel_key, data)
                    time.sleep(4)
                    return upload_to_dailymotion()

                print(streams, '\n')

                stream = streams[x]

                print(stream, '\n')

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
                print(e, '\n')
                data = {
                    "code": 303, "message": f"Error: downloading video failed, retrying count {x}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
                print('[Status --        ]', data, '\n')
                updateChannelUploadStatus(_channel_key, data)
                return upload_to_dailymotion()

        else:
            data = {
                "code": 400, "message": "Error: downloading video failed", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
            return upload_to_dailymotion()

    _video_size = download_video()

    _file_path = f'{output_path}{_video_id}.mp4'
    print("\n Video downloaded successfully\n" if os.path.isfile(
        _file_path) else "\nError Downloading video\n")

    time.sleep(5)
    if not os.path.isfile(_file_path):
        data = {
            "code": 420, "message": "Video was not downloaded, retrying with anther video", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
        print('[Status --        ]', data, '\n')
        updateChannelUploadStatus(_channel_key, data)
        return upload_to_dailymotion()

    print(_file_path, '\n')

    try:
        url = dm.upload(_file_path)
    except Exception as e:
        print(e)
        data = {
            "code": 500, "message": f"Error: Uploading video failed => Reason {e}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
        updateChannelUploadStatus(_channel_key, data)
        return upload_to_dailymotion()

    print('[Video Uploaded successfully   ]', '\n')

    rx = re.compile(r'[A-Za-z]+')
    tw = rx.findall(_title)
    title_tags = list(
        set([word for word in tw if word.lower() not in stop_words and len(word) > 2]))

    dw = rx.findall(_description)
    description_tags = list(set(
        [word for word in dw if word.lower() not in stop_words and len(word) > 2]))

    _limits = {
        "videoDuration": _max_video_length - _video_length,
        "videoSize": _max_video_size - _video_size
    }

    final_tags = list(set([tag for tag in list(
        _tags + title_tags + description_tags) if tag.lower() not in stop_words and len(tag) > 2]))

    dm_post_obj = {
        'url': url,
        'title': _title,
        'description': _description,
        'tags': ','.join(final_tags[:35]),
        'published': 'true',
        'channel': 'fun',
    }

    try:
        _player_next_video = dm.get('/videos', {
            'fields': 'id',
            'sort': 'recent',
            'owners': account["credentials"]["userName"]
        })['list'][0]['id']  # This is a video id
        dm_post_obj['player_next_video'] = _player_next_video
    except:
        pass

    try:
        dm.post('/me/videos', dm_post_obj)
        data = {
            "code": 200, "message": "Success: Video uploaded to dailymotion", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
        print('[Status --        ]', data, '\n')
        updateChannelUploadStatus(_channel_key, data)
        time.sleep(2)
        print('[Video uploaded to dailymotion]')
        exit()

    except Exception as e:
        print(e.message)
        if 'access_forbidden: You reached your upload rate limit' in e.message:
            data = {
                "code": 420, "message": f"Error: Publishing video failed =>  Reason: {e.message}", "videoId": _video_id, "isLimited": True,
                "limitedAt": f"{datetime.now(pytz.timezone('Africa/Nairobi'))}"}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
            exit()
        elif 'video has exceeded maximum duration allowed' in e.message:
            data = {
                "code": 400, "message": f"Error: Publishing video failed =>  Reason: {e.message}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
            time.sleep(4)
            return upload_to_dailymotion()
        else:
            data = {
                "code": 400, "message": f"Error: Publishing video failed =>  Reason: {e}", "videoId": _video_id, "isLimited": _is_limited, "limitedAt": _limited_at}
            print('[Status --        ]', data, '\n')
            updateChannelUploadStatus(_channel_key, data)
            time.sleep(4)
            print("[Error publishing video]")
            return upload_to_dailymotion()


upload_to_dailymotion()