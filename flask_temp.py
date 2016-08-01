# -*- coding: utf-8 -*-
from __future__ import division
import json
from datetime import datetime,timedelta
import httplib
import urlparse
import requests

from twokenize import tokenizeRawTweetText
from flask import Flask, jsonify, render_template, request
app = Flask(__name__)

from secret import TOKEN

def round_time(dt):
	return dt + timedelta(minutes=-dt.minute,seconds=-dt.second,microseconds=-dt.microsecond)

def unshorten_url(url):
    parsed = urlparse.urlparse(url)
    h = httplib.HTTPConnection(parsed.netloc)
    resource = parsed.path
    if parsed.query != "":
        resource += "?" + parsed.query
    user_agent = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.63 Safari/534.3'
    headers = { 'User-Agent' : user_agent }
    h.request('HEAD', resource ,headers=headers)
    response = h.getresponse()
    return response.getheader('Location')

@app.route('/')
def index():
    return render_template('top10.html')

@app.route('/_add_top_k')
def show_top():
    """Visualize a top k result file"""
    max_amount = request.args.get('k', 10, type=int)

    end = round_time(datetime.utcnow())
    start = end + timedelta(days=-1)
    params = {"token": TOKEN, "start": start.strftime(_API_time_format), "end": end.strftime(_API_time_format)}
    API_response = requests.get("{APIurl}/keywords/".format(APIurl=_API_location),params=params)
    counts = json.loads(API_response.content)

    total = 0
    for entry in counts:
    	total += entry["count"]

    topkArray = []
    for i,entry in enumerate(counts):
        if i < max_amount:
            if entry["count"] > 0:
              topkArray.append({"label": entry["keyword"], "y": entry["count"]/total})
    
    return jsonify(result=topkArray)

@app.route('/details.html')
def details():
    return render_template('details.html')

@app.route('/_get_details')
def show_details():
    """Visualize the details of a top k product"""
    prod = request.args.get('product', '', type=str)
    
    end = round_time(datetime.utcnow())
    start = end + timedelta(weeks=-1)
    params = {"token": TOKEN, "start": start.strftime(_API_time_format), "end": end.strftime(_API_time_format)}
    API_response = requests.get("{APIurl}/keywords/{keyword}".format(APIurl=_API_location, keyword=prod), params=params)
    tweets = json.loads(API_response.content)

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

        dt = datetime.strptime(tweet["created_at"],"%a %b %d %H:%M:%S +0000 %Y")
        if (dt.year,dt.month,dt.day,dt.hour) in tsDict:
            tsDict[(dt.year,dt.month,dt.day,dt.hour)] += 1
        else:
            tsDict[(dt.year,dt.month,dt.day,dt.hour)] = 1

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
        if token not in _stop_words and "http" not in token and len(token)>1:
            wordCloud.append({"text": token, "weight": wordCloudDict[token]})

    ts = []
    tsStart = sorted(tsDict)[0]
    tsEnd = sorted(tsDict)[-1]
    temp = datetime(tsStart[0],tsStart[1],tsStart[2],tsStart[3],0,0)
    while temp < datetime(tsEnd[0],tsEnd[1],tsEnd[2],tsEnd[3],0,0):
        if (temp.year,temp.month,temp.day,temp.hour) in tsDict:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "value": tsDict[(temp.year,temp.month,temp.day,temp.hour)]})
        else:
            ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "value": 0})

        temp += timedelta(hours=1)

    lng = 0
    lat = 0
    if mapLocations:
        for loc in mapLocations:
            lng += loc["lng"]
            lat += loc["lat"]
        avLoc = {"lng": lng/len(mapLocations), "lat": lat/len(mapLocations)}
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

_API_location = "http://127.0.0.1:8000"  ## CHANGE FOR ACTUAL ADDRESS
_API_time_format = "%Y-%m-%d-%H-%M-%S"

if __name__ == '__main__':
    app.run(debug=True)
