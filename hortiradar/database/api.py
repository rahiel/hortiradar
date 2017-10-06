from collections import Counter
from datetime import datetime, timedelta
from time import time

import falcon
import ujson as json

from keywords import get_db, get_keywords
from hortiradar import admins, users, time_format
from hortiradar.database import stop_words


db = get_db()
tweets = db.tweets
groups = db.groups

KEYWORDS = get_keywords(local=True)
keywords_sync_time = time()


def get_dates(req, resp, resource, params):
    """Parse the `start` and `end` datetime parameters."""
    try:
        today = datetime.today()
        today = datetime(today.year, today.month, today.day)
        start = req.get_param("start")
        if start:
            start = datetime.strptime(start, time_format)
        else:
            start = today - timedelta(days=1)
        end = req.get_param("end")
        if end:
            end = datetime.strptime(end, time_format)
        else:
            end = today
        params["start"] = start
        params["end"] = end
    except ValueError:
        msg = "Invalid datetime format string, use: %s" % time_format
        raise falcon.HTTPBadRequest("Bad request", msg)

def want_spam(req):
    return req.get_param("spam") == '1'

def is_spam(t):
    spam_level = 0.6
    return t.get("spam") is not None and t["spam"] > spam_level


class KeywordsResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, start, end):
        """All tracked keywords in the database.
        Returns a sorted list with the keywords and their counts.
        Takes the "group" GET parameters for the keyword group.
        """
        global KEYWORDS, keywords_sync_time
        if (time() - keywords_sync_time) > 60 * 60:
            KEYWORDS = get_keywords(local=True)
            keywords_sync_time = time()
        query = {
            "num_keywords": {"$gt": 0},
            "datetime": {"$gte": start, "$lt": end}
        }
        group = req.get_param("group")
        if group:
            del query["num_keywords"]
            query["groups"] = group
        tw = tweets.find(query, projection={"keywords": True, "_id": False})
        counts = Counter()
        for t in tw:
            kws = t["keywords"]
            if group:
                keywords = []
                for kw in kws:
                    if kw in KEYWORDS:
                        if group in KEYWORDS[kw].groups:
                            keywords.append(kw)
                kws = keywords
            counts.update(kws)
        data = [{"keyword": kw, "count": c} for kw, c in counts.most_common()]
        resp.body = json.dumps(data)

class GroupsResource:
    def on_get(self, req, resp):
        """The groups currently tagged in the database."""
        gs = groups.find({}, projection={"name": True, "_id": False})
        group_names = [g["name"] for g in gs]
        resp.body = json.dumps(group_names)

    def on_post(self, req, resp):
        """Add a new group to the system."""
        name = req.get_param("name")
        gs = groups.find({}, projection={"name": True, "_id": False})
        group_names = [g["name"] for g in gs]
        if name not in group_names and len(name) > 0:
            group = {"name": name}
            groups.insert_one(group)

class GroupResource:
    def on_get(self, req, resp, group):
        """List of keywords in the group."""
        g = groups.find_one({"name": group})
        try:
            data = g["keywords"]
        except KeyError:
            data = []
        resp.body = json.dumps(data)

    def on_put(self, req, resp, group):
        """Update group wordlist."""
        g = groups.find_one({"name": group})
        if not g:
            raise falcon.HTTPNotFound()
        keywords = json.load(req.bounded_stream)
        groups.update_one({"name": group}, {"$set": {"keywords": keywords}})

    def on_delete(self, req, resp, group):
        groups.delete_one({"name": group})

class KeywordResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """NLP analysis of the tweet text, entities and timestamp of tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={
            "tweet.id_str": True, "tokens": True, "tweet.entities": True, "tweet.created_at": True,
            "tweet.user.id_str": True, "tweet.user.screen_name": True, "tweet.retweeted_status.user.id_str": True,
            "tweet.retweeted_status.user.screen_name": True, "tweet.retweeted_status.id_str": True,
            "tweet.in_reply_to_user_id_str": True, "tweet.in_reply_to_screen_name": True,
            "spam": True, "_id": False
        })
        if not want_spam(req):
            tw = [t for t in tw if not is_spam(t)]
        resp.body = json.dumps(tw)

class KeywordIdsResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """A list of the tweet id's matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.id_str": True, "spam": True, "_id": False})
        if want_spam(req):
            data = [t["tweet"]["id_str"] for t in tw]
        else:
            data = [t["tweet"]["id_str"] for t in tw if not is_spam(t)]
        resp.body = json.dumps(data)

class KeywordMediaResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of the media entities for tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.id_str": True, "tweet.entities.media": True, "spam": True, "_id": False})
        # alternative:  "tweet.entities.media": {"$ne": None} in query
        if want_spam(req):
            data = [t["tweet"] for t in tw if "media" in t["tweet"]["entities"]]
        else:
            data = [t["tweet"] for t in tw if "media" in t["tweet"]["entities"] if not is_spam(t)]
        resp.body = json.dumps(data)

class KeywordUrlsResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of the urls entities for tweets matching keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end}
        }, projection={"tweet.entities.urls": True, "tweet.id_str": True, "spam": True, "_id": False})
        # "tweet.entities.urls": {"$ne": []}
        if want_spam(req):
            data = [t["tweet"] for t in tw if t["tweet"]["entities"]["urls"]]
        else:
            data = [t["tweet"] for t in tw if t["tweet"]["entities"]["urls"] if not is_spam(t)]
        resp.body = json.dumps(data)

class KeywordTextsResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        "List of the tweet texts of keyword."
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tweet.text": True, "tweet.id_str": True, "spam": True, "_id": False})
        if want_spam(req):
            data = [t["tweet"] for t in tw]
        else:
            data = [t["tweet"] for t in tw if not is_spam(t)]
        resp.body = json.dumps(data)

class KeywordUsersResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """List of users who tweeted keyword.
        Returns a sorted list with tuples of the user id and the number of tweets.
        """
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tweet.user.id_str": True, "spam": True, "_id": False})
        counts = Counter()
        skip_spam = not want_spam(req)
        for t in tw:
            if skip_spam and is_spam(t):
                continue
            counts[t["tweet"]["user"]["id_str"]] += 1
        data = [{"id_str": id_str, "count": c} for id_str, c in counts.most_common()]
        resp.body = json.dumps(data)

class KeywordWordcloudResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """Returns words and their counts in all tweets for keyword."""
        tw = tweets.find({
            "keywords": keyword,
            "datetime": {"$gte": start, "$lt": end},
        }, projection={"tokens.lemma": True, "spam": True, "_id": False})
        words = Counter()
        skip_spam = not want_spam(req)
        for t in tw:
            if skip_spam and is_spam(t):
                continue
            lemmas = [token["lemma"] for token in t["tokens"]]
            words.update([l for l in lemmas if l.lower() not in stop_words])
        data = [{"word": w, "count": c} for w, c in words.most_common()]
        resp.body = json.dumps(data)

class KeywordTimeSeriesResource:
    @falcon.before(get_dates)
    def on_get(self, req, resp, keyword, start, end):
        """Returns a time series with number of tweets from start to end in bins of step.
        Step is a mandatory GET parameter: number of seconds as an integer.

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
        skip_spam = not want_spam(req)
        for t in tw:
            if skip_spam and is_spam(t):
                continue
            while not t["datetime"] < start + (i + 1) * dt:
                i += 1
            series[i] += 1
        last = max(series.keys())
        data = {
            "start": start.strftime(time_format), "end": (start + (last + 1) * dt).strftime(time_format),
            "step": int(step), "bins": len(series), "series": series
        }
        resp.body = json.dumps(data)

class TweetResource:
    def on_get(self, req, resp, id_str):
        t = tweets.find_one({"tweet.id_str": id_str}, projection={"datetime": False, "_id": False})
        if t:
            resp.body = json.dumps(t)
        else:
            raise falcon.HTTPNotFound()

    def on_delete(self, req, resp, id_str):
        t = tweets.delete_one({"tweet.id_str": id_str})
        if t.deleted_count > 0:
            resp.status = falcon.HTTP_204
        else:
            raise falcon.HTTPNotFound()

    def on_patch(self, req, resp, id_str):
        """Update value of tweet document. Only allows (un)setting top-level attributes for now."""
        data = req.stream.read()
        try:
            patch = json.loads(data)
        except ValueError as e:
            msg = "Invalid JSON: " + str(e)
            raise falcon.HTTPBadRequest("Bad request", msg)
        t = tweets.find_one({"tweet.id_str": id_str}, projection={"_id": True})
        if not t:
            raise falcon.HTTPNotFound()
        update = json_merge_patch_to_mongo_update(patch)
        try:
            tweets.update_one({"_id": t["_id"]}, update)
            resp.status = falcon.HTTP_204
        except Exception as e:
            msg = ("Error: {}. ".format(str(e)) +
                   "This endpoint accepts JSON merge patches as specified in https://tools.ietf.org/html/rfc7396")
            raise falcon.HTTPBadRequest("Bad request", msg)


def json_merge_patch_to_mongo_update(patch):
    update = {}
    set_values = []
    unset = []
    for key, value in patch.items():
        if value is not None:
            set_values.append((key, value))
        else:
            unset.append(key)
    if set_values:
        update["$set"] = dict(set_values)
    if unset:
        update["$unset"] = {k: True for k in unset}
    return update


class AuthenticationMiddleware:
    def process_request(self, req, resp):
        token = req.get_param("token")
        if token in admins:
            pass                # admins can access everything
        elif token in users:
            p = req.path
            m = req.method
            # users may not access:
            if (p.startswith("/keywords/") and (p.endswith("/texts") or p.count("/") == 2) or  # /keywords/{keyword}, /keywords/{keyword}/texts
                p.startswith("/tweet/") or  # /tweet/{id_str}
                p.startswith("/groups/") and m in ["DELETE", "PUT"] or  # PUT/DELETE on /groups/{group}
                p.startswith("/groups") and m == "POST"):   # POST on /groups
                raise falcon.HTTPForbidden()
        else:
            raise falcon.HTTPForbidden()


app = application = falcon.API(middleware=AuthenticationMiddleware())
app.add_route("/keywords", KeywordsResource())
app.add_route("/groups", GroupsResource())
app.add_route("/groups/{group}", GroupResource())
app.add_route("/keywords/{keyword}", KeywordResource())
app.add_route("/keywords/{keyword}/ids", KeywordIdsResource())
app.add_route("/keywords/{keyword}/media", KeywordMediaResource())
app.add_route("/keywords/{keyword}/urls", KeywordUrlsResource())
app.add_route("/keywords/{keyword}/texts", KeywordTextsResource())
app.add_route("/keywords/{keyword}/users", KeywordUsersResource())
app.add_route("/keywords/{keyword}/wordcloud", KeywordWordcloudResource())
app.add_route("/keywords/{keyword}/series", KeywordTimeSeriesResource())
app.add_route("/tweet/{id_str}", TweetResource())
