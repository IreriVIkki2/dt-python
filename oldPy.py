import requests
import os
import re
import shutil
from pyyoutube import Api
from dotenv import load_dotenv
from pytube import YouTube
import dailymotion
from stopwords import stop_words
load_dotenv()


# Delete any videos in the videos folder
output_path = f'{os.getcwd()}/videos/'
try:
    shutil.rmtree(output_path)
    os.mkdir(output_path)
except Exception as e:
    os.mkdir(output_path)

yt_api = Api(api_key=os.getenv("YOUTUBE_API_KEY"))
updateDownloadedVideos = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateDownloadedVideos"


getYouTubeVideoId = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeVideoId"

_params = {"playlistId": "PLFBqiCq3wiIG9dVwemUdpVb5mS7Jdr-sl"}


""" 
    # Login to dailymotion with the
    # required scopes
"""

_api_key = "b2779280c0d27d97a9da"
_api_secret = "1efad316faca754a3c7d2d66063b861d41f2e4fe"
_scope = ['manage_videos']
_info = {'username': "lyngrant83",
         'password': "@Sasawa2"}

dm = dailymotion.Dailymotion()
dm.set_grant_type(
    'password',
    api_key=_api_key,
    api_secret=_api_secret,
    scope=_scope,
    info=_info
)


r = requests.get(url=getYouTubeVideoId, params=_params)
video = r.json()
_video_id = list(video.keys())[0]

print(list(video.values())[0].isPublished)

# try:
#     # Get videos streams
#     yt_download = YouTube(f"https://www.youtube.com/watch?v={_video_id}")

#     # Download the youtube video
#     yt_download.streams.filter(
#         progressive=True,
#         file_extension='mp4'
#     ).order_by(
#         'resolution'
#     ).desc().first().download(
#         output_path=output_path,
#         filename=_video_id
#     )
# except Exception as e:
#     requests.post(updateDownloadedVideos, data=)

# try:
#     url = dm.upload(f'{output_path}{_video_id}.mp4')
# except Exception as e:
#     raise e


# video_info = yt_api.get_video_by_id(video_id=_video_id, return_json=True)[
#     0]['snippet']

# try:
#     tags = video_info['tags']
# except Exception as e:
#     tags = []

# rx = re.compile(r'[A-Za-z]+')
# tw = rx.findall(video_info['title'])
# title_tags = list(
#     set([word for word in tw if word not in stop_words and len(word) > 2]))

# dw = rx.findall(video_info['description'])
# description_tags = list(set(
#     [word for word in dw if word not in stop_words and len(word) > 2]))

# _title = video_info['title']
# _description = video_info['description']
# _player_next_video = dm.get('/videos', {
#     'fields': 'id',
#     'sort': 'recent',
#     'owners': 'lyngrant83'
# })['list'][0]['id']  # This is a video id
# _tags = list(set(title_tags + description_tags + tags)),
# _thumbnail_url = list(video_info['thumbnails'].values())[-1]['url']

# try:
#     dm.post('/me/videos',
#             {
#                 'url': url,
#                 'title': _title,
#                 'description': _description,
#                 'player_next_video': _player_next_video,
#                 'tags': _tags,
#                 'thumbnail_url': _thumbnail_url,
#                 'published': 'true',
#                 'channel': 'news',
#             })

# except Exception as e:
#     raise e
