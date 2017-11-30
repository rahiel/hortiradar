from collections import Counter
from datetime import datetime, timedelta
from hashlib import md5
from types import FunctionType
from typing import Sequence
import random
import urllib.parse

import requests
import ujson as json
from celery import Celery
from flask import redirect
from redis import StrictRedis
from pattern.nl import sentiment

from hortiradar import Tweety, TOKEN, time_format
from hortiradar.database import stop_words, obscene_words, blacklist, get_db


db = get_db()
storiesdb = db.stories

broker_url = "amqp://guest@localhost:5672/hortiradar"
app = Celery("tasks", broker=broker_url)
app.conf.update(task_ignore_result=True, worker_prefetch_multiplier=2)

tweety = Tweety("http://127.0.0.1:8888", TOKEN)
redis = StrictRedis()

CACHE_TIME = 60 * 60


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
def cache(func, *args, cache_time=CACHE_TIME, force_refresh=False, path="", **kwargs):
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

def get_nsfw_prob(image_url: str):
    cache_time = 12 * 60**2
    key = "nsfw:%s" % image_url
    v = redis.get(key)
    if v is not None:
        redis.expire(key, cache_time)
        if v == b"415":
            return 0, 415
        else:
            return float(v), 200

    r = requests.post("http://localhost:6000", data={"url": image_url})
    if r.status_code == 200:
        redis.set(key, r.content, ex=cache_time)
        return float(r.content), r.status_code
    elif r.status_code == 415:   # Invalid image
        redis.set(key, b"415", ex=cache_time)
        return 0, r.status_code

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

    topkArray = []
    for entry in counts:
        if len(topkArray) < max_amount:
            if entry["keyword"] not in blacklist:
                topkArray.append({"label": entry["keyword"], "y": entry["count"] / total})
        else:
            break

    return topkArray

def process_details(prod, params, force_refresh=False, cache_time=CACHE_TIME):
    tweets = cache(tweety.get_keyword, prod, force_refresh=force_refresh, cache_time=CACHE_TIME, **params)

    tweetList = []
    unique_tweets = {}
    imagesList = []
    URLList = []
    word_cloud_dict = Counter()
    tsDict = Counter()
    mapLocations = []
    spam_list = []
    image_tweet_id = {}
    nodes = {}
    edges = []

    for tw in tweets:
        tweet = tw["tweet"]
        lemmas = [t["lemma"] for t in tw["tokens"]]
        texts = [t["text"].lower() for t in tw["tokens"]]  # unlemmatized words
        words = list(set(lemmas + texts))                  # to check for obscene words

        # check for spam
        if any(obscene_words.get(t) for t in words):
            spam_list.append(tweet["id_str"])
            continue

        tweetList.append(tweet["id_str"])
        word_cloud_dict.update(lemmas)

        text = " ".join(texts)
        if text not in unique_tweets:
            unique_tweets[text] = tweet["id_str"]

        dt = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        tsDict.update([(dt.year, dt.month, dt.day, dt.hour)])

        user_id_str = tweet["user"]["id_str"]
        if "retweeted_status" in tweet:
            rt_user_id_str = tweet["retweeted_status"]["user"]["id_str"]

            if rt_user_id_str not in nodes:
                nodes[rt_user_id_str] = tweet["retweeted_status"]["user"]["screen_name"]
            if user_id_str not in nodes:
                nodes[user_id_str] = tweet["user"]["screen_name"]

            edges.append({"source": rt_user_id_str, "target": user_id_str, "value": "retweet"})

        if "user_mentions" in tweet["entities"]:
            for obj in tweet["entities"]["user_mentions"]:
                if obj["id_str"] not in nodes:
                    nodes[obj["id_str"]] = obj["screen_name"]
                if user_id_str not in nodes:
                    nodes[user_id_str] = tweet["user"]["screen_name"]

                edges.append({"source": user_id_str, "target": obj["id_str"], "value": "mention"})

        if tweet["in_reply_to_user_id_str"]:
            if tweet["in_reply_to_user_id_str"] not in nodes:
                nodes[tweet["in_reply_to_user_id_str"]] = tweet["in_reply_to_screen_name"]
            if user_id_str not in nodes:
                nodes[user_id_str] = tweet["user"]["screen_name"]

            edges.append({"source": user_id_str, "target": tweet["in_reply_to_user_id_str"], "value": "reply"})

        try:
            for obj in tweet["entities"]["media"]:
                image_url = obj["media_url_https"]
                image_tweet_id[image_url] = tweet["id_str"]
                imagesList.append(image_url)
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

    word_cloud = []
    for (token, count) in word_cloud_dict.most_common():
        if token.lower() not in stop_words and "http" not in token and len(token) > 1:
            word_cloud.append({"text": token, "weight": count})

    # sentiment analysis on wordcloud
    polarity, subjectivity = sentiment(" ".join(word_cloud_dict.elements()))

    ts = []
    try:
        tsStart = sorted(tsDict)[0]
        tsEnd = sorted(tsDict)[-1]
        temp = datetime(tsStart[0], tsStart[1], tsStart[2], tsStart[3], 0, 0)
        while temp <= datetime(tsEnd[0], tsEnd[1], tsEnd[2], tsEnd[3], 0, 0):
            if (temp.year, temp.month, temp.day, temp.hour) in tsDict:
                ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": tsDict[(temp.year, temp.month, temp.day, temp.hour)]})
            else:
                ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": 0})

            temp += timedelta(hours=1)
    except IndexError:          # when there are 0 tweets
        pass

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
    nsfw_list = []
    for (url, count) in Counter(imagesList).most_common():
        if len(images) >= 16:
            break
        nsfw_prob, status = get_nsfw_prob(url)
        if status == 200 and nsfw_prob > 0.8:
            nsfw_list.append(image_tweet_id[url])
        elif status == 200:
            images.append({"link": url, "occ": count})
    mark_as_spam.apply_async((nsfw_list,), queue="web")

    urls = []
    for (url, count) in Counter(URLList).most_common():
        urls.append({"link": url, "occ": count})

    # limit number of nodes/edges
    edges = random.sample(edges, min(len(edges), 250))
    connected_nodes = set([e["source"] for e in edges] + [e["target"] for e in edges])

    graph = {"nodes": [], "edges": []}
    for node in connected_nodes:
        graph["nodes"].append({"id": nodes[node]})

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        graph["edges"].append({"source": nodes[source], "target": nodes[target], "value": edge["value"]})

    unique_ids = list(unique_tweets.values())
    tweets = random.sample(unique_ids, min(20, len(unique_ids)))

    data = {
        "tweets": tweets,
        "num_tweets": len(tweetList),
        "timeSeries": ts,
        "URLs": urls,
        "photos": images,
        "tagCloud": word_cloud,
        "locations": mapLocations,
        "centerloc": avLoc,
        "graph": graph,
        "polarity": polarity
    }
    return data

def load_stories(group, start, end):
    """Load active stories from redis and closed stories from DB. 
    Since active stories are story objects, they are processed to JSON from here for rendering in the website"""
    closed = storiesdb.find({"groups": group, "datetime": {"$gte": start, "$lt": end}})
    active = redis.get("s:{gr}".format(gr=group))

    if active:
        act = pickle.loads(active)
        active_out = [s.get_jsondict() for s in act]
    else:
        active_out = []

    if closed:
        closed_out = [s for s in closed]
    else:
        closed_out = []

    return active_out, closed_out

def process_stories(group, start, end, force_refresh=False, cache_time=CACHE_TIME):
    active,closed = load_stories(group, start, end)

    sorted_active = sorted(active, key=lambda x: len(x["tweets"]), reverse=True)
    sorted_closed = sorted(closed, key=lambda x: len(x["tweets"]), reverse=True)

    return sorted_active, sorted_closed


funs = {
    "process_details": process_details,
    "process_top": process_top,
    "process_stories": process_stories,
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
