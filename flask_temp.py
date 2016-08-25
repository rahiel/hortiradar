# -*- coding: utf-8 -*-
from __future__ import division
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

from twokenize import tokenizeRawTweetText
from tweety import Tweety
from secret import TOKEN


app = Flask(__name__)

local = "http://127.0.0.1:8000"
qray = "http://bigtu.q-ray.nl"
tweety = Tweety(local, TOKEN)


def round_time(dt):
    return dt + timedelta(minutes=-dt.minute, seconds=-dt.second, microseconds=-dt.microsecond)

@app.route('/')
def index():
    return render_template('top10.html')

@app.route("/_add_top_k/<group>")
def show_top_fruits(group):
    """Visualize a top k result file"""
    max_amount = request.args.get('k', 10, type=int)

    end = round_time(datetime.utcnow())
    start = end + timedelta(days=-1)
    params = {
        "start": start.strftime(_API_time_format), "end": end.strftime(_API_time_format),
        "group": group
    }
    counts = tweety.get_keywords(**params)

    total = 0
    for entry in counts:
        total += entry["count"]

    topkArray = []
    for i, entry in enumerate(counts):
        if i < max_amount:
            if entry["count"] > 0:
                topkArray.append({"label": entry["keyword"], "y": entry["count"] / total})
        else:
            break

    return jsonify(result=topkArray)

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
    interval = request.args.get('interval', '', type=int)

    end = round_time(datetime.utcnow())
    start = end + timedelta(seconds=-interval)
    params = {"start": start.strftime(_API_time_format), "end": end.strftime(_API_time_format)}
    tweets = tweety.get_keyword(prod, **params)

    tweetList = []
    imagesList = []
    URLList = []
    wordCloudDict = {}
    tsDict = {}
    mapLocations = []

    for tweet in tweets:
        tweetList.append(tweet["id_str"])

        tokens = tokenizeRawTweetText(tweet["text"].lower())
        for t in tokens:
            if t not in wordCloudDict:
                wordCloudDict[t] = 1
            else:
                wordCloudDict[t] += 1

        dt = datetime.strptime(tweet["created_at"], "%a %b %d %H:%M:%S +0000 %Y")
        if (dt.year, dt.month, dt.day, dt.hour) in tsDict:
            tsDict[(dt.year, dt.month, dt.day, dt.hour)] += 1
        else:
            tsDict[(dt.year, dt.month, dt.day, dt.hour)] = 1

        try:
            for obj in tweet["entities"]["media"]:
                imagesList.append(obj["media_url"])
        except KeyError:
            pass

        try:
            for obj in tweet["entities"]["urls"]:
                URLList.append(obj["expanded_url"])
        except KeyError:
            pass

        try:
            if tweet["coordinates"] != None:
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

    data = {
        "tweets": tweetList[::-1],
        "timeSeries": ts,
        "URLs": URLList,
        "photos": imagesList,
        "tagCloud": wordCloud,
        "locations": mapLocations,
        "centerloc": avLoc
    }

    return jsonify(result=data)

with open("data/stoplist-nl.txt", "rb") as f:
    _stop_words = [w.decode("utf-8").strip() for w in f]
    _stop_words = {w: 1 for w in _stop_words}  # stop words to filter out in word cloud

_API_time_format = "%Y-%m-%d-%H-%M-%S"

if __name__ == '__main__':
    app.run(debug=True)
