from collections import Counter
from datetime import datetime, timedelta
from hashlib import md5
from types import FunctionType
from typing import Sequence
import random
import urllib.parse

import ujson as json
from celery import Celery
from flask import redirect
from redis import StrictRedis

from hortiradar import Tweety, TOKEN, time_format


broker_url = "amqp://guest@localhost:5672/hortiradar"
app = Celery("tasks", broker=broker_url)
app.conf.update(task_ignore_result=True, worker_prefetch_multiplier=2)

tweety = Tweety("http://127.0.0.1:8888", TOKEN)
redis = StrictRedis()

CACHE_TIME = 60 * 60

with open("../database/data/stoplist-nl.txt", "r") as f:
    stop_words = [w.strip() for w in f]
    stop_words = {w: 1 for w in stop_words}  # stop words to filter out in word cloud

with open("../database/data/obscene_words.txt", "r") as f:
    obscene_words = [w.strip() for w in f if not w.startswith("#")]
    obscene_words = {w: 1 for w in obscene_words}


def get_cache_key(func, *args, **kwargs):
    sort_dict = lambda d: sorted(d.items(), key=lambda x: x[0])
    arguments = []
    for a in args:
        if isinstance(a, dict):
            arguments.append(sort_dict(a))
        else:
            arguments.append(a)
    k = (
        func.__name__,
        str(arguments),
        str(sort_dict(kwargs))
    )
    return json.dumps("cache:" + ":".join(k))

# tweety methods return json string
# internal app functions return python dicts/lists
def cache(func, *args, cache_time=CACHE_TIME, force_refresh=False, path=None, **kwargs):
    loading_cache_time = 60 * 10
    key = get_cache_key(func, *args, **kwargs)
    v = redis.get(key)

    if v is not None and not force_refresh:
        return json.loads(v) if type(v) == bytes else v
    else:
        loading_id = "loading:" + md5(key.encode("utf-8")).hexdigest()
        if not force_refresh:
            loading = redis.get(loading_id)
            if not loading:
                redis.set(loading_id, b"loading", ex=loading_cache_time)
                cache_request.apply_async((func.__name__, args, kwargs, cache_time, key, loading_id), queue="web")
            return redirect("/hortiradar/loading/{}?redirect={}".format(loading_id.split(":", 1)[1], urllib.parse.quote(path)))
        else:
            redis.set(loading_id, b"loading", ex=loading_cache_time)
            response = func(*args, force_refresh=force_refresh, cache_time=cache_time, **kwargs)
            v = json.dumps(response) if type(response) != bytes else response
            redis.set(key, v, ex=cache_time)
            redis.set(loading_id, b"done", ex=loading_cache_time)
            return response if type(response) != bytes else json.loads(response)

@app.task
def cache_request(func, args, kwargs, cache_time, key, loading_id):
    fun = cache_request.funs[func]
    if fun in [process_top, process_details]:
        kwargs["force_refresh"] = True
    response = fun(*args, cache_time=cache_time, **kwargs)
    v = json.dumps(response) if type(response) != bytes else response
    redis.set(key, v, ex=cache_time)
    redis.set(loading_id, b"done", ex=cache_time)

@app.task
def mark_as_spam(ids: Sequence[str]):
    for id_str in ids:
        tweety.patch_tweet(id_str, data=json.dumps({"spam": 0.8}))

def floor_time(dt, *, hour=False, day=False):
    if hour:
        return dt - timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    elif day:
        return dt - timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    else:
        return Exception("Missing keyword argument")


def get_process_top_params(group):
    end = floor_time(datetime.utcnow(), hour=True)
    start = end + timedelta(days=-1)
    params = {
        "start": start.strftime(time_format), "end": end.strftime(time_format),
        "group": group
    }
    return params

def process_top(group, max_amount, params, force_refresh=False, cache_time=CACHE_TIME):
    counts = cache(tweety.get_keywords, force_refresh=force_refresh, cache_time=cache_time, **params)
    total = sum([entry["count"] for entry in counts])

    # tags in the first line are still in flowers.txt
    # tags in the second line are excluded but should be included again in the future
    # tags in 3rd line are removed from the word lists
    BLACKLIST = ["fhgt", "fhtf", "fhalv", "fhglazentulp", "fhgt2014", "fhgt2015", "aalsmeer", "westland", "fh2020", "bloemistenklok", "morgenvoordeklok", "fhstf", "floraholland", "fhmagazine", "floranext", "bos",
                 "aardappel", "bes", "citroen", "kool", "sla", "ui", "wortel", "phoenix", "acer", "jasmijn", "erica", "iris", "fruit", "roos", "palm", "rosa", "viola", "moederdag", "vrouwendag",
                 "munt", "vrucht", "mosterd", "sweetie", "scheut", "salak", "rapen"
    ]
    topkArray = []
    for entry in counts:
        if len(topkArray) < max_amount:
            if entry["keyword"] not in BLACKLIST:
                topkArray.append({"label": entry["keyword"], "y": entry["count"] / total})
        else:
            break

    return topkArray

def process_details(prod, params, force_refresh=False, cache_time=CACHE_TIME):
    tweets = cache(tweety.get_keyword, prod, force_refresh=force_refresh, cache_time=CACHE_TIME, **params)

    tweetList = []
    imagesList = []
    URLList = []
    wordCloudDict = Counter()
    tsDict = Counter()
    mapLocations = []
    spam_list = []
    nodes = {}
    edges = []

    for tw in tweets:
        tweet = tw["tweet"]
        lemmas = [t["lemma"] for t in tw["tokens"]]
        texts = [t["text"].lower() for t in tw["tokens"]]  # unlemmatized words
        words = list(set(lemmas + texts))                  # to check for obscene words

        if any(obscene_words.get(t) for t in words):
            spam_list.append(tweet["id_str"])
            continue

        tweetList.append(tweet["id_str"])
        wordCloudDict.update(lemmas)

        dt = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        tsDict.update([(dt.year, dt.month, dt.day, dt.hour)])

        if "retweeted_status" in tweet:
            rt_id_str = tweet["retweeted_status"]["user"]["id_str"]
            id_str = tweet["user"]["id_str"]

            if rt_id_str not in nodes:
                nodes[rt_id_str] = tweet["retweeted_status"]["user"]["screen_name"]
            if id_str not in nodes:
                nodes[id_str] = tweet["user"]["screen_name"]

            edges.append({"source": rt_id_str, "target": id_str, "value": "retweet"})

        if "user_mentions" in tweet["entities"]:
            for obj in tweet["entities"]["user_mentions"]:
                if obj["id_str"] not in nodes:
                    nodes[obj["id_str"]] = obj["screen_name"]
                if tweet["user"]["id_str"] not in nodes:
                    nodes[tweet["user"]["id_str"]] = tweet["user"]["screen_name"]

                edges.append({"source": tweet["user"]["id_str"], "target": obj["id_str"], "value": "mention"})

        if tweet["in_reply_to_user_id_str"]:
            if tweet["in_reply_to_user_id_str"] not in nodes:
                nodes[tweet["in_reply_to_user_id_str"]] = tweet["in_reply_to_screen_name"]
            if tweet["user"]["id_str"] not in nodes:
                nodes[tweet["user"]["id_str"]] = tweet["user"]["screen_name"]

            edges.append({"source": tweet["user"]["id_str"], "target": tweet["in_reply_to_user_id_str"], "value": "reply"})

        try:
            for obj in tweet["entities"]["media"]:
                imagesList.append(obj["media_url_https"])
        except KeyError:
            pass

        try:
            for obj in tweet["entities"]["urls"]:
                # using "expand" here synchronously will slow everything down tremendously
                url = obj["expanded_url"]
                if url is not None:
                    URLList.append(url)
        except KeyError:
            pass

        try:
            if tweet["coordinates"] is not None:
                if tweet["coordinates"]["type"] == "Point":
                    coords = tweet["coordinates"]["coordinates"]
                    mapLocations.append({"lng": coords[0], "lat": coords[1]})
        except KeyError:
            pass

    mark_as_spam.apply_async((spam_list,), queue="web")

    wordCloud = []
    for (token, count) in wordCloudDict.most_common():
        if token.lower() not in stop_words and "http" not in token and len(token) > 1:
            wordCloud.append({"text": token, "weight": count})

    ts = []
    tsStart = sorted(tsDict)[0]
    tsEnd = sorted(tsDict)[-1]
    temp = datetime(tsStart[0], tsStart[1], tsStart[2], tsStart[3], 0, 0)
    while temp <= datetime(tsEnd[0], tsEnd[1], tsEnd[2], tsEnd[3], 0, 0):
        if (temp.year, temp.month, temp.day, temp.hour) in tsDict:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": tsDict[(temp.year, temp.month, temp.day, temp.hour)]})
        else:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": 0})

        temp += timedelta(hours=1)

    lng = 0
    lat = 0
    if mapLocations:
        for loc in mapLocations:
            lng += loc["lng"]
            lat += loc["lat"]
            avLoc = {"lng": lng / len(mapLocations), "lat": lat / len(mapLocations)}
    else:
        avLoc = {"lng": 5, "lat": 52}

    images = []
    for (url, count) in Counter(imagesList).most_common():
        images.append({"link": url, "occ": count})

    urls = []
    for (url, count) in Counter(URLList).most_common():
        urls.append({"link": url, "occ": count})

    graph = {"nodes": [], "edges": []}
    for node in nodes:
        graph["nodes"].append({"id": nodes[node]})

    for edge in edges:
        graph["edges"].append({"source": nodes[edge["source"]], "target": nodes[edge["target"]], "value": edge["value"]})

    data = {
        "tweets": random.sample(tweetList[::-1], min(20, len(tweetList))),
        "num_tweets": len(tweetList),
        "timeSeries": ts,
        "URLs": urls,
        "photos": images,
        "tagCloud": wordCloud,
        "locations": mapLocations,
        "centerloc": avLoc,
        "graph": graph
    }
    return data


funs = {
    "process_details": process_details,
    "process_top": process_top,
}
for f in dir(tweety):
    attr = eval("tweety.{}".format(f))
    if isinstance(attr, FunctionType):
        funs[f] = attr
cache_request.funs = funs

def expand(url):
    """Expands URLs from URL shorteners."""
    import requests
    try:
        r = requests.head(url)
        while r.is_redirect and r.headers.get("location") is not None:
            url = r.headers["location"]
            r = requests.head(url)
        return r.url
    except:
        return url
