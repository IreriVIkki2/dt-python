from current_channel import get_accout, _channel_key
import dateutil.parser
import datetime
import requests
import json
import time
import pytz
import re


filter_ids_base_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeExistingIds?ids="

update_queue_outcome_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateCreateQueueOutcome"


def get_api_key():
    f1 = open('api_key.txt', 'r')
    _current_api_key = f1.read()
    f1.close()
    print("get_api_key ==> _current_api_key", _current_api_key)
    if not _current_api_key:
        reset_api_key()
        return get_api_key()
    return _current_api_key


def reset_api_key():
    f1 = open('api_key.txt', 'r')
    _current_api_key = f1.read()
    f1.close()

    url = f"https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeApiKey"
    res = requests.get(url)
    api_key = res.json()
    _next_key = api_key["key"]

    
    if _current_api_key == _next_key:
        print("No more valid keys for now")
        exit()

    f = open('api_key.txt', 'w')
    f.write(_next_key)
    time.sleep(2)
    f.close()
    return _next_key


def video_age_in_minutes(_published_date):
    d1 = dateutil.parser.parse(_published_date).replace(tzinfo=None)
    d2 = datetime.datetime.now()
    d3 = d2-d1
    return divmod(d3.days * 86400 + d3.seconds, 60)[0]


def video_length_in_seconds(ar):
    if len(ar) > 3:
        return False
    elif len(ar) == 2:
        ar = [0] + ar
    elif len(ar) == 1:
        ar = [0, 0] + ar
    else:
        pass

    print(ar)
    return int(ar[0]) * 3600 + int(ar[1]) * 60 + int(ar[2])


def query_for_initial_suggestions(_video_id, _max_video_age):
    d1 = datetime.datetime.now()
    d2 = d1 - datetime.timedelta(minutes=int(_max_video_age))
    d3 = d2.replace(tzinfo=None).isoformat().split('.')[0]
    url = f"https://www.googleapis.com/youtube/v3/search?part=id&maxResults=50&publishedAfter={d3}Z&relatedToVideoId={_video_id}&type=video&key={get_api_key()}"

    res = requests.get(url)
    print(res, res.status_code)
    if res.status_code == 403:
        reset_api_key()
        return query_for_initial_suggestions(_video_id=_video_id, _max_video_age=_max_video_age)
    elif res.status_code is not 200:
        error = res.json()
        print(error["error"])
        return None
    else:
        videos = res.json()
        return [video["id"]["videoId"] for video in videos["items"]]


def get_valid_video_info(_video_id, account):
    _valid_video = {"code": 200}
    video_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails,snippet,statistics&id={_video_id}&key={get_api_key()}"

    res = requests.get(video_url)

    if res.status_code == 403:
        reset_api_key()
        return get_valid_video_info(_video_id, account)
    elif res.status_code is not 200:
        error = res.json()
        print(error["error"])
        return None
    else:
        res_json = res.json()
        video_info = res_json["items"][0]

    # current video info items
    snippet = video_info["snippet"]
    _published_date = snippet["publishedAt"]
    _video_age = video_age_in_minutes(_published_date)
    _channel_id = snippet["channelId"]
    _view_count = video_info["statistics"]["viewCount"]
    _video_vpm = int(int(_view_count) / _video_age)
    _duration = video_info["contentDetails"]["duration"]
    _time_array = [i for i in re.compile(
        "[A-Z]").split(_duration) if i is not '']
    _video_length = video_length_in_seconds(_time_array)
    _video_title = snippet["title"]
    _video_description = snippet["description"]
    _video_thumbnail = snippet["thumbnails"]["default"]["url"]
    try:
        _video_tags = snippet["videoTags"]
    except:
        _video_tags = []

    # account search options
    search_options = account["searchOptions"]
    _min_subscribers = search_options["minSubscribers"]
    _max_subscribers = search_options["maxSubscribers"]
    _max_video_age = search_options["videoAge"]
    _min_vpm = search_options["viewsPerMinute"]
    _video_length_array = list(search_options["maxVideoLength"].values())
    _max_video_length = video_length_in_seconds(_video_length_array)

    channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics,brandingSettings&id={_channel_id}&key={get_api_key()}"
    res = requests.get(channel_url)

    if res.status_code == 403:
        reset_api_key()
        return get_valid_video_info(_video_id, account)
    elif res.status_code is not 200:
        error = res.json()
        print(error["error"])
        return None
    else:
        res_json = res.json()
        channel_info = res_json["items"][0]

    _subscriber_count = int(channel_info["statistics"]["subscriberCount"])
    try:
        _channel_keywords_string = channel_info["brandingSettings"]["channel"]["keywords"]
    except:
        _channel_keywords_string = ""

    _channel_keywords = [i.strip() for i in re.compile(
        r'"(.*?)"').split(_channel_keywords_string) if i.strip() is not ""]

    if _subscriber_count < _min_subscribers or _subscriber_count > _max_subscribers:
        _valid_video["code"] = 101

    elif int(_video_age) > int(_max_video_age):
        _valid_video["code"] = 102

    elif int(_video_vpm) < int(_min_vpm):
        _valid_video["code"] = 103

    elif int(_video_length) > int(_max_video_length):
        _valid_video["code"] = 104

    else:
        _valid_video["videoId"] = _video_id
        _valid_video["vpm"] = _video_vpm
        _valid_video["title"] = _video_title
        _valid_video["description"] = _video_description
        _valid_video["tags"] = _video_tags + _channel_keywords
        _valid_video["thumbnail_url"] = _video_thumbnail
        _valid_video["length"] = _video_length

    return _valid_video


def create_queue():
    print('Initiated')
    account = get_accout()
    _next = account["queryId"]["next"]
    _current = account["queryId"]["current"]
    _max_video_age = account["searchOptions"]["videoAge"]

    _new_queue = {}

    if len(_next) is 0:
        _search_id = _current
    else:
        _search_id = _next[0]

    raw_video_ids = query_for_initial_suggestions(
        _video_id=_search_id, _max_video_age=_max_video_age)

    res = requests.get(f"{filter_ids_base_url}{','.join(raw_video_ids)}")
    res_json = res.json()
    _ids = res_json["finalIds"]

    if len(_next) is 0:
        _new_next = _ids[:10] if len(_ids) else raw_video_ids[:25]
    else:
        _new_next = _next

    for _id in _ids:
        _valid_video = get_valid_video_info(_id, account)
        code = _valid_video['code']
        if code is 101:
            print("Subscribers out of range")
        elif code is 102:
            print("Video is too old")
        elif code is 103:
            print("Video is not popular enough")
        elif code is 104:
            print("Video is too long")
        else:
            print(_valid_video)
            _new_queue[_id] = _valid_video
            _new_next.append(_id)

    _queryId = {
        "current": _new_next[0],
        "next": _new_next[1:]
    }

    data = {
        "oldQueueId": _current,
        "newQueueId": _search_id,
        "newQueueObject": _new_queue,
        "queryId": _queryId,
        "channelKey": _channel_key
    }

    print(data)

    requests.post(update_queue_outcome_url, data={"data": json.dumps(data)})
    return 200
