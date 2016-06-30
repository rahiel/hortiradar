from __future__ import division, print_function
from ConfigParser import ConfigParser
from time import sleep

import pymongo
import tweepy
from requests.packages.urllib3.exceptions import ProtocolError
from requests import ConnectionError

from twokenize import tokenizeRawTweetText


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
    def __init__(self, api, keywords):
        self.api = api
        self.db = get_db()
        self.keywords = keywords

    def on_status(self, status):
        """Handle arrival of a new tweet."""
        tokens = tokenizeRawTweetText(status.text)
        print(tokens)
        keywords = get_keywords(tokens, self.keywords)
        tweets = self.db.tweets
        tweets.insert_one({
            "tweet": status._json,
            "keywords": keywords,
            "num_keywords": len(keywords)
        })

    def on_delete(self, status_id, user_id):
        """A user deleted a tweet, respect their decision by also deleting it
        on our end.
        """
        # TODO: not tested, rare event
        status_id, user_id = unicode(status_id), unicode(user_id)
        tweets = self.db.tweets
        tweets.delete_one({"tweet.id_str": status_id, "tweet.user.id_str": user_id})

    def on_error(self, status_code):
        """This does the Twitter-recommended exponential backoff when it
        returns non-False and disconnects on False.
        """
        if status_code == 420:  # rate limit
            return False


def get_keywords(tokens, keywords):
    """Returns a list of the keywords that occur in tokens."""
    kw = []
    for t in tokens:
        a = keywords.get(t, None)
        if a is not None:
            kw.append(t)
    return kw


def main():
    config = ConfigParser()
    config.read("twitter.ini")

    auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
    auth.set_access_token(config.get("twitter", "access_key"), config.get("twitter", "access_secret"))
    api = tweepy.API(auth, compression=True, wait_on_rate_limit=True)

    with open("data/keywords_bloemen_top10app.txt") as doc:
        keywords = unicode(doc.read()).lower().split(',')
    keyword_dict = {key: 1 for key in keywords}

    listener = StreamListener(api, keyword_dict)
    stream = tweepy.Stream(auth=auth, listener=listener)

    with open("data/stoplist_nl_extended.txt") as f:
        track = [unicode(l.split()[0]) for l in f.readlines()]   # list of most common Dutch words

    while True:
        try:
            stream.filter(track=track, languages=["nl"])
        except (ProtocolError, ConnectionError) as e:
            sleep(1)


if __name__ == "__main__":
    main()
