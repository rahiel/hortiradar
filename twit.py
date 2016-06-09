from __future__ import division, print_function
from ConfigParser import ConfigParser

import pymongo
import tweepy

from twokenize import tokenizeRawTweetText


config = ConfigParser()
config.read("twitter.ini")

auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
auth.set_access_token(config.get("twitter", "access_key"), config.get("twitter", "access_secret"))
api = tweepy.API(auth, compression=True, wait_on_rate_limit=True)

DATABASE = None


def get_db():
    """Returns the twitter database."""
    global DATABASE
    if DATABASE is None:
        mongo = pymongo.MongoClient()
        DATABASE = mongo.twitter
    return DATABASE


class StreamListener(tweepy.StreamListener):
    """Tweepy will continuously receive notices from Twitter and dispatches
    them to one of the event handlers.
    """
    def __init__(self, api):
        self.api = api
        self.db = get_db()

    def on_status(self, status):
        """Handle arrival of a new tweet."""
        tokens = tokenizeRawTweetText(status.text)
        print(tokens)
        keywords = get_keywords(tokens)
        tweets = self.db.tweets
        tweets.insert_one({"tweet": status._json, "keywords": keywords})

    def on_delete(self, status_id, user_id):
        """A user deleted a tweet, respect their decision by also deleting it
        on our end.
        """
        # TODO: not tested, rare event
        status_id, user_id = unicode(status_id), unicode(user_id)
        tweets = self.db.tweets
        tweets.delete_one({"tweet.id_str": status_id, "tweet.user.id_str": user_id})


listener = StreamListener(api)
stream = tweepy.Stream(auth=auth, listener=listener)

with open("data/keywords_bloemen_top10app.txt") as doc:
    keywords = unicode(doc.read()).lower().split(',')

keyword_dict = {key: 1 for key in keywords}


def get_keywords(tokens):
    """Returns a list of the keywords that occur in tokens."""
    kw = []
    for t in tokens:
        a = keyword_dict.get(t, None)
        if a is not None:
            kw.append(t)
    return kw


stream.filter(track=keywords, languages=["nl"])
