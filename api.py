from collections import Counter
from datetime import datetime, timedelta
import json
from math import ceil

import falcon

from main import get_db
from twokenize import tokenizeRawTweetText
from secret import TOKEN


tweets = get_db().tweets
time_format = "%Y-%m-%d-%H-%M-%S"

with open("data/stoplist-nl.txt") as f:
    stop_words = [w.decode("utf-8").strip() for w in f.readlines()]
    stop_words = {w: 1 for w in stop_words}  # stop words to filter out in word cloud

with open("data/fruitsandveg.txt") as f:
    fruitsandveg_words = [w.decode("utf-8").strip() for w in f.readlines()]

with open("data/flowers.txt") as f:
    flowers_words = [w.decode("utf-8").strip() for w in f.readlines()]

def get_dates(req, resp, resource, params):
    """Parse the 'start' and 'end' datetime parameters."""
    try:
        start = req.get_param("start")
        start = datetime.strptime(start, time_format) if start else datetime(2001, 1, 1)
        end = req.get_param("end")
        end = datetime.strptime(end, time_format) if end else datetime(3001, 1, 1)
        params["start"] = start
        params["end"] = end
    except ValueError:
        msg = "Invalid datetime format string, use: %s" % time_format
        raise falcon.HTTPBadRequest("Bad request", msg)


class KeywordsResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, start, end):
        """All tracked keywords in the database.
        Returns a sorted list with the keywords and their counts.
        """
        tw = tweets.find({
            "num_keywords": {"$gt": 0},
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"keywords": True, "_id": False})
        counts = Counter()
        for t in tw:
            counts.update(t["keywords"])
        data = [{"keyword": kw, "count": c} for kw, c in counts.most_common()]
        resp.body = json.dumps(data)

class KeywordsFlowersResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, start, end):
        """All tracked keywords in the database.
        Returns a sorted list with the flower keywords and their counts.
        """
        tw = tweets.find({
            "num_keywords": {"$gt": 0},
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"keywords": True, "_id": False})
        counts = Counter()
        for t in tw:
            filt_keywords = [kw for kw in t["keywords"] if kw in flowers_words]
            counts.update(filt_keywords)
        data = [{"keyword": kw, "count": c} for kw, c in counts.most_common()]
        resp.body = json.dumps(data)

class KeywordsFruitsResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, start, end):
        """All tracked keywords in the database.
        Returns a sorted list with the fruit and veg keywords and their counts.
        """
        tw = tweets.find({
            "num_keywords": {"$gt": 0},
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"keywords": True, "_id": False})
        counts = Counter()
        for t in tw:
            filt_keywords = [kw for kw in t["keywords"] if kw in fruitsandveg_words]
            counts.update(filt_keywords)
        data = [{"keyword": kw, "count": c} for kw, c in counts.most_common()]
        resp.body = json.dumps(data)

class KeywordResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """The text, entities and timestamp of tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={
            "tweet.id_str": True, "tweet.text": True, "tweet.entities": True, "tweet.created_at": True,
            "_id": False
        })
        data = [t["tweet"] for t in tw]
        resp.body = json.dumps(data)

class KeywordIdsResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """A list of the tweet id's matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.id_str": True, "_id": False})
        data = [t["tweet"]["id_str"] for t in tw]
        resp.body = json.dumps(data)

class KeywordMediaResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of the media entities for tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.id_str": True, "tweet.entities.media": True, "_id": False})
        # alternative:  "tweet.entities.media": {"$ne": None} in query
        data = [t["tweet"] for t in tw if "media" in t["tweet"]["entities"]]
        resp.body = json.dumps(data)

class KeywordUrlsResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of the urls entities for tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.entities.urls": True, "tweet.id_str": True, "_id": False})
        # "tweet.entities.urls": {"$ne": []}
        data = [t["tweet"] for t in tw if t["tweet"]["entities"]["urls"]]
        resp.body = json.dumps(data)


class KeywordTextsResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        "List of the tweet texts of keyword."
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tweet.text": True, "tweet.id_str": True, "_id": False})
        data = [t["tweet"] for t in tw]
        resp.body = json.dumps(data)

class KeywordUsersResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of users who tweeted keyword.
        Returns a sorted list with tuples of the user id and the number of tweets.
        """
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tweet.user.id_str": True, "_id": False})
        counts = Counter()
        for t in tw:
            counts[t["tweet"]["user"]["id_str"]] += 1
        data = [{"id_str": id_str, "count": c} for id_str, c in counts.most_common()]
        resp.body = json.dumps(data)

class KeywordWordcloudResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """Returns words and their counts in all tweets for keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tweet.text": True, "_id": False})
        words = Counter()
        for t in tw:
            tokens = tokenizeRawTweetText(t["tweet"]["text"])
            words.update([w for w in tokens if w.lower() not in stop_words])
        data = [{"word": w, "count": c} for w, c in words.most_common()]
        resp.body = json.dumps(data)

class KeywordTimeSeriesResource(object):
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """Returns a time series with number of tweets from start to end in bins of step.
        Step is mandatory GET parameters: number of seconds as an integer.

        Returns an object where:
            - start is the beginning of the first bin
            - end is the end of the last bin (so nothing was counted after this time)
            - step is the requested time bin size
            - bins is the number of filled bins
            - series is an object where the keys are the bin numbers and the values the counts
        """
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"datetime": True, "_id": False}).sort("datetime")
        step = req.get_param("step")
        try:
            dt = timedelta(seconds=int(step))
        except (ValueError, TypeError):
            msg = "Invalid step: step is an integer of the number of seconds."
            raise falcon.HTTPBadRequest("Bad request", msg)
        first = tw[0]["datetime"]
        steps_until_first = int((first - start).total_seconds() // dt.total_seconds())
        start = start + steps_until_first * dt
        i = 0
        series = Counter()
        for t in tw:
            while not t["datetime"] < start + (i + 1) * dt:
                i += 1
            series[i] += 1
        last = max(series.keys())
        data = {
            "start": start.strftime(time_format), "end": (start + (last + 1) * dt).strftime(time_format),
            "step": int(step), "bins": len(series), "series": series
        }
        resp.body = json.dumps(data)


class AuthenticationMiddleware(object):
    def process_request(self, req, resp):
        token = req.get_param("token")
        if token != TOKEN:
            raise falcon.HTTPNotFound()


app = application = falcon.API(middleware=AuthenticationMiddleware())
app.add_route("/keywords", KeywordsResource())
app.add_route("/keywords/flowers", KeywordsFlowersResource())
app.add_route("/keywords/fruits", KeywordsFruitsResource())
app.add_route("/keywords/{keyword}", KeywordResource())
app.add_route("/keywords/{keyword}/ids", KeywordIdsResource())
app.add_route("/keywords/{keyword}/media", KeywordMediaResource())
app.add_route("/keywords/{keyword}/urls", KeywordUrlsResource())
app.add_route("/keywords/{keyword}/texts", KeywordTextsResource())
app.add_route("/keywords/{keyword}/users", KeywordUsersResource())
app.add_route("/keywords/{keyword}/wordcloud", KeywordWordcloudResource())
app.add_route("/keywords/{keyword}/series", KeywordTimeSeriesResource())
