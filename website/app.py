# -*- coding: utf-8 -*-
from __future__ import division
from collections import Counter
from datetime import datetime, timedelta
from time import sleep

from flask import Flask, Response, render_template, request
from redis import StrictRedis
import requests
import ujson as json

from hortiradar import tokenizeRawTweetText, Tweety, TOKEN


app = Flask(__name__)

local = "http://127.0.0.1:8000"
qray = "http://bigtu.q-ray.nl"
tweety = Tweety(qray, TOKEN)

r = StrictRedis()

CACHE_TIME = 60 * 60

# tweety methods return json string
# internal app functions return python dicts/lists
def cache(func, *args, **kwargs):
    force_refresh = kwargs.pop("force_refresh", None) or False
    cache_time = kwargs.pop("cache_time", None) or CACHE_TIME
    key = (
        func.__name__,
        str(args),
        str(sorted(kwargs.items(), key=lambda x: x[0]))
    )
    key = json.dumps(':'.join(key))
    v = r.get(key)
    if v is not None and not force_refresh:
        return json.loads(v) if type(v) == str else v
    elif v == "loading":
        # TODO: do this properly
        sleep(0.5)
        kwargs["force_refresh"] = force_refresh
        kwargs["cache_time"] = cache_time
        return cache(func, *args, **kwargs)
    else:
        r.set(key, "loading", ex=10 * 60)
        response = func(*args, force_refresh=force_refresh, cache_time=cache_time, **kwargs)
        v = json.dumps(response) if type(response) != str else response
        r.set(key, v, ex=cache_time)
        return response if type(response) != str else json.loads(response)


# ############ TEST MARIJN
# def cache(func, *args, **kwargs):
#     response = func(*args, **kwargs)
#     return json.loads(response)
# #############

def jsonify(**kwargs):
    return Response(json.dumps(kwargs), status=200, mimetype="application/json")

def round_time(dt):
    return dt + timedelta(minutes=-dt.minute, seconds=-dt.second, microseconds=-dt.microsecond)

def expand(url):
    """Expands URLs from URL shorteners."""
    try:
        r = requests.head(url)
        while r.is_redirect and r.headers.get("location") is not None:
            url = r.headers["location"]
            r = requests.head(url)
        return r.url
    except:
        return url

@app.route('/')
def index():
    return render_template('top10.html')

@app.route("/_add_top_k/<group>")
def show_top_fruits(group):
    """Visualize a top k result file"""
    max_amount = request.args.get('k', 10, type=int)
    data = cache(process_top_fruits, group, max_amount)
    return jsonify(result=data)

def process_top_fruits(group, max_amount, force_refresh=False, cache_time=CACHE_TIME):
    end = round_time(datetime.utcnow())
    start = end + timedelta(days=-1)
    params = {
        "start": start.strftime(API_time_format), "end": end.strftime(API_time_format),
        "group": group
    }
    counts = cache(tweety.get_keywords, force_refresh=force_refresh, cache_time=cache_time, **params)

    total = sum([entry["count"] for entry in counts])

    topkArray = []
    for i, entry in enumerate(counts):
        if i < max_amount:
            topkArray.append({"label": entry["keyword"], "y": entry["count"] / total})
        else:
            break

    return topkArray

@app.route('/details.html')
def details():
    return render_template('details.html')

@app.route('/_get_details')
def show_details():
    """

    Visualize the details of a top k product
    product:    Product for which the details page should be constructed
    interval:   Interval in seconds for which tweets should be extracted through API

    """
    prod = request.args.get('product', '', type=str)
    interval = request.args.get('interval', 60 * 60 * 24 * 7, type=int)
    end = request.args.get('end', None, type=str)
    if end:
        end = datetime.strptime(end, "%Y-%m-%d %H:%M") + timedelta(hours=1)
    else:
        end = round_time(datetime.utcnow())
    start = end + timedelta(seconds=-interval)
    params = {"start": start.strftime(API_time_format), "end": end.strftime(API_time_format)}
    details = cache(process_details, prod, params)
    return jsonify(result=details)

def process_details(prod, params, force_refresh=False, cache_time=CACHE_TIME):
    tweets = cache(tweety.get_keyword, prod, force_refresh=force_refresh, cache_time=CACHE_TIME, **params)

    tweetList = []
    imagesList = []
    URLList = []
    wordCloudDict = Counter()
    tsDict = Counter()
    mapLocations = []

    for tweet in tweets:
        tweetList.append(tweet["id_str"])

        tokens = tokenizeRawTweetText(tweet["text"].lower())
        wordCloudDict.update(tokens)

        dt = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        tsDict.update([(dt.year, dt.month, dt.day, dt.hour)])

        try:
            for obj in tweet["entities"]["media"]:
                imagesList.append(obj["media_url"])
        except KeyError:
            pass

        try:
            for obj in tweet["entities"]["urls"]:
                URLList.append(expand(obj["expanded_url"]))
        except KeyError:
            pass

        try:
            if tweet["coordinates"] is not None:
                if tweet["coordinates"]["type"] == "Point":
                    coords = tweet["coordinates"]["coordinates"]
                    mapLocations.append({"lng": coords[0], "lat": coords[1]})
        except KeyError:
            pass

    wordCloud = []
    for token in wordCloudDict:
        if token not in _stop_words and "http" not in token and len(token) > 1:
            wordCloud.append({"text": token, "weight": wordCloudDict[token]})

    ts = []
    tsStart = sorted(tsDict)[0]
    tsEnd = sorted(tsDict)[-1]
    temp = datetime(tsStart[0], tsStart[1], tsStart[2], tsStart[3], 0, 0)
    while temp < datetime(tsEnd[0], tsEnd[1], tsEnd[2], tsEnd[3], 0, 0):
        if (temp.year, temp.month, temp.day, temp.hour) in tsDict:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "value": tsDict[(temp.year, temp.month, temp.day, temp.hour)]})
        else:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "value": 0})

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
    for (url,count) in Counter(imagesList).most_common():
        images.append({"link": url, "occ": count})

    urls = []
    for (url,count) in Counter(URLList).most_common():
        urls.append({"link": url, "occ": count})

    data = {
        "tweets": tweetList[::-1],
        "timeSeries": ts,
        "URLs": urls,
        "photos": images,
        "tagCloud": wordCloud,
        "locations": mapLocations,
        "centerloc": avLoc
    }
    return data

with open("../database/data/stoplist-nl.txt", "rb") as f:
    _stop_words = [w.decode("utf-8").strip() for w in f]
    _stop_words = {w: 1 for w in _stop_words}  # stop words to filter out in word cloud

API_time_format = "%Y-%m-%d-%H-%M-%S"

if __name__ == '__main__':
    app.run(debug=True)
