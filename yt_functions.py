from current_channel import get_accout, _channel_key
import dateutil.parser
import datetime
import requests
import json
import pytz
import re

delete_queue_base_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/deleteMultipleQueues?queues="

filter_ids_base_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/removeExistingIds?ids="

update_queue_outcome_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateCreateQueueOutcome"

get_youtube_apikey_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/getYouTubeApiKey"

update_youtube_apikey_url = "https://us-central1-vimeovids-ireri.cloudfunctions.net/updateYouTubeApiKey"


def get_api_key():
    f1 = open('api_key.txt', 'r')
    _current_api_key = f1.read()
    f1.close()
    return _current_api_key


def reset_api_key(code):
    f1 = open('api_key.txt', 'r')
    f2 = open('api_key.txt', 'w')
    _current_api_key = f1.read()
    print(_current_api_key)
    if code == 403:
        res = requests.get(get_youtube_apikey_url)
        api_key = res.json()
        _next_key = api_key["key"]
        print(_current_api_key != _next_key)
        if _current_api_key != _next_key:
            data = {
                "key": _current_api_key,
                "limited": True,
                "limitedAt": datetime.datetime.now().isoformat()
            }
            requests.post(update_youtube_apikey_url, data={
                "keyObject": json.dumps(data)})
        f2.write(_next_key)
    _verdict = f1.read()
    f1.close()
    f2.close()
    return _verdict


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

    print(url)

    res = requests.get(url)
    if res.status_code == 403:
        reset_api_key(403)
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
        reset_api_key(403)
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
        reset_api_key(403)
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

    _new_queue = {"exists": True}

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


data = {"oldQueueId": "JsBbBEsl9w4", "newQueueId": "G0-fkSaPlWg", "newQueueObject": {"6Pj9dAlGPLA": {"code": 200, "videoId": "6Pj9dAlGPLA", "vpm": 3, "title": "\u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb #1 || \u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6700\u9ad8\u306e\u77ac\u9593 || \u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6620\u753b || \u521d\u9663", "description": "\u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb #1 || \u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6700\u9ad8\u306e\u77ac\u9593 || \u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6620\u753b || \u521d\u9663\n\u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb #1\n| \u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6700\u9ad8\u306e\u77ac\u9593\n\u30b7\u30c9\u30cb\u30a2\u306e\u9a0e\u58eb  \u6620\u753b\n\u521d\u9663\nhttps://youtu.be/6Pj9dAlGPLA", "tags": ["\u0441\u0430\u043c\u043e\u0434\u0435\u043b\u043a\u0438"], "thumbnail_url": "https://i.ytimg.com/vi/6Pj9dAlGPLA/default.jpg", "length": 435}, "40_KQz-N_yg": {"code": 200, "videoId": "40_KQz-N_yg", "vpm": 1, "title": "\u30ad\u30b9\u30b7\u30b9 #6  || \u30ad\u30b9\u30b7\u30b9  \u6700\u9ad8\u306e\u77ac\u9593 || \u30ad\u30b9\u30b7\u30b9  \u6620\u753b || \u3044\u3061\u3001\u306b\u306e\u30013P!", "description": "\u30ad\u30b9\u30b7\u30b9 #6  || \u30ad\u30b9\u30b7\u30b9  \u6700\u9ad8\u306e\u77ac\u9593 || \u30ad\u30b9\u30b7\u30b9  \u6620\u753b || \u3044\u3061\u3001\u306b\u306e\u30013P!\n\u30ad\u30b9\u30b7\u30b9 #6 \n\u30ad\u30b9\u30b7\u30b9  \u6700\u9ad8\u306e\u77ac\u9593\n\u30ad\u30b9\u30b7\u30b9  \u6620\u753b\n\u3044\u3061\u3001\u306b\u306e\u30013P!\nhttps://youtu.be/40_KQz-N_yg", "tags": ["\u0441\u0430\u043c\u043e\u0434\u0435\u043b\u043a\u0438"], "thumbnail_url": "https://i.ytimg.com/vi/40_KQz-N_yg/default.jpg", "length": 398}, "sIPZUvxbtY4": {
    "code": 200, "videoId": "sIPZUvxbtY4", "vpm": 31, "title": "\u3010\u6f2b\u753b\u3011\u9ad8\u6821\u751f\u3002\u5f7c\u306e\u5b9f\u5bb6\u306b\u521d\u306e\u300e\u304a\u6cca\u307e\u308a\u30c7\u30fc\u30c8\uff01\u300f\u7236\u306f\u6575\u304b\u5473\u65b9\u304b\uff01\uff1f\u3010\u604b\u611banime\u3011", "description": "\u4e8c\u4eba\u3068\u3082\u9ad8\u6821\u751f\u3067\u4ed8\u304d\u5408\u3063\u3066\u9593\u3082\u306a\u3044\u9803\u3001\u52c7\u6c17\u3068\u521d\u3081\u3066\u304a\u6cca\u307e\u308a\u30c7\u30fc\u30c8\u3092\u3057\u305f\u3002\u3068\u8a00\u3063\u3066\u3082\u5f7c\u306e\u5b9f\u5bb6\u306a\u306e\u3060\u304c\uff65\uff65\uff65\u4e00\u5fdc\u304a\u6cca\u308a\u30c7\u30fc\u30c8\u3068\u306a\u308c\u3070\u3001\u591c\u306f\u30a8\u30c3\u25ef\u306a\u4e8b\u3092\u3059\u308b\u96f0\u56f2\u6c17\u306b\u306a\u308b\u3068\u601d\u3046\u3068\u4e0d\u5b89\u3068\u671f\u5f85\u304c\uff65\uff65\uff65\n\n********************************************************************\n\n\n\n\u5f53\u30c1\u30e3\u30f3\u30cd\u30eb\u3067\u306f\u3001\u30aa\u30ea\u30b8\u30ca\u30eb\u306e\u30b9\u30c8\u30fc\u30ea\u30fc\u3092\u52df\u96c6\u3057\u3001\n\u305d\u308c\u306b\u57fa\u3065\u3044\u3066\u72ec\u81ea\u306b\u30a2\u30cb\u30e1\u3092\u5236\u4f5c\u3057\u3001\u58f0\u512a\u3055\u3093\u306b\u58f0\u3092\u5439\u304d\u8fbc\u3093\u3067\u3082\u3089\u3063\u3066\u304a\u308a\u307e\u3059\u3002\n\u3000\u305d\u306e\u969b\u3001\u8457\u4f5c\u6a29\u3082\u8b72\u6e21\u3055\u308c\u3066\u304a\u308a\u307e\u3059\u306e\u3067\u3001\u3059\u3079\u3066\u306e\u8457\u4f5c\u6a29\u3082\u5f53\u30c1\u30e3\u30f3\u30cd\u30eb\u306b\u3042\u308a\u307e\u3059\u3002\n\n\n\n\u30c1\u30e3\u30f3\u30cd\u30eb\u767b\u9332\u304a\u9858\u3044\u3057\u307e\u3059\uff01\u2193\nhttp://urx.blue/3V8T\n\n\n\n\u4f5c\u753b\uff1a\u9ce9\u30d5\u30a1\u30a4\u30e4\u30fc\n\u58f0\u512a\uff1a\u4e2d\u5bae\u6c99\u5e0c\n\n\n\nBGM\nYouTube\u30aa\u30fc\u30c7\u30a3\u30aa\u30e9\u30a4\u30d6\u30e9\u30ea\n\n\n\n\n\n\n\n\n\uff03\u9ad8\u6821\u751f\u3000\uff03\u304a\u6cca\u307e\u308a\u30c7\u30fc\u30c8\u3000\uff03\u5f7c\u306e\u5b9f\u5bb6\u3000\uff03\u604b\u611banime", "tags": ["\u604b\u611b\u307e\u3093\u304c\u30a2\u30cb\u30e1BOX anime \u604b\u611b\u6f2b\u753b \u7b11\u3048\u308b \u604b\u611b\u30a2\u30cb\u30e1 \u304a\u3059\u3059\u3081 \u30b9\u30ab\u30c3\u3068 \u80f8\u30ad\u30e5\u30f3"], "thumbnail_url": "https://i.ytimg.com/vi/sIPZUvxbtY4/default.jpg", "length": 209}}, "queryId": {"current": "G0-fkSaPlWg", "next": ["6Pj9dAlGPLA", "40_KQz-N_yg", "sIPZUvxbtY4"]}, "channelKey": "43bbf9a837fd7f60809a"}

requests.post(update_queue_outcome_url, data={"data": json.dumps(data)})
