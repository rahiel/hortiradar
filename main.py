from __future__ import division, print_function
from ConfigParser import ConfigParser
from time import sleep
import traceback

from logbook import Logger, RotatingFileHandler
import pymongo
import tweepy
from requests import ConnectionError, Timeout
from requests.packages.urllib3.exceptions import ProtocolError, ReadTimeoutError

from twokenize import tokenizeRawTweetText


DATABASE = None

RotatingFileHandler("twitter.log", backup_count=5).push_application()
log = Logger("main")
log.info("Started")


def get_db():
    """Returns the twitter database."""
    global DATABASE
    if DATABASE is None:
        mongo = pymongo.MongoClient()
        # check info so we quit early if we can't connect to mongo
        try:
            mongo.server_info()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise Exception("Can't connect to MongoDB at " + str(e))
        print("Connected to MongoDB")
        DATABASE = mongo.twitter
    return DATABASE


class StreamListener(tweepy.StreamListener):
    """Tweepy will continuously receive notices from Twitter and dispatches
    them to one of the event handlers.
    """
    def __init__(self, api, keywords):
        self.api = api
        self.keywords = keywords
        # these below should be class attributes if we had more than 1 instance
        self.db = get_db()
        self.tweets = self.db.tweets  # Mongo collection
        self.time_format = "%a %b %d %H:%M:%S +0000 %Y"  # 'Tue Jun 28 15:01:54 +0000 2016'

    def on_status(self, status):
        """Handle arrival of a new tweet."""
        tokens = tokenizeRawTweetText(status.text)
        keywords = find_keywords(tokens, self.keywords)
        self.tweets.insert_one({
            "tweet": status._json,
            "keywords": keywords,
            "num_keywords": len(keywords),
            "datetime": status.created_at
        })

    def on_delete(self, status_id, user_id):
        """A user deleted a tweet, respect their decision by also deleting it
        on our end.
        """
        status_id, user_id = unicode(status_id), unicode(user_id)
        log.notice("on_delete: status_id = {}, user_id = {}".format(status_id, user_id))
        self.tweets.delete_one({"tweet.id_str": status_id, "tweet.user.id_str": user_id})

    def on_error(self, status_code):
        """This does the Twitter-recommended exponential backoff when it
        returns non-False and disconnects on False.
        """
        log.error("on_error: status_code = {}".format(status_code))
        if status_code == 420:  # rate limit
            return True


def find_keywords(tokens, keywords):
    """Returns a list of the keywords that occur in tokens."""
    kw = []
    for t in tokens:
        a = keywords.get(t, None)
        if a is not None:
            kw.append(t)
    return kw


def get_keywords():
    """Gets keywords from the file."""
    with open("data/keywords_bloemen_top10app.txt") as doc:
        return unicode(doc.read()).lower().split(',')


def main():
    config = ConfigParser()
    config.read("config.ini")

    auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
    auth.set_access_token(config.get("twitter", "access_key"), config.get("twitter", "access_secret"))
    api = tweepy.API(auth, compression=True, wait_on_rate_limit=True)

    keywords = get_keywords()
    keyword_dict = {key: 1 for key in keywords}  # for O(1) checking of keywords

    listener = StreamListener(api, keyword_dict)
    stream = tweepy.Stream(auth=auth, listener=listener)

    with open("data/stoplist_nl_extended.txt") as f:
        track = [unicode(l.split()[0]) for l in f.readlines()]   # list of most common Dutch words

    while True:
        try:
            stream.filter(track=track, languages=["nl"])
        except (ProtocolError, ConnectionError, Timeout, ReadTimeoutError) as e:
            sleep(1)
        except Exception as e:
            tb = traceback.format_exc()
            log.critical(tb)
            sleep(1)


if __name__ == "__main__":
    main()
