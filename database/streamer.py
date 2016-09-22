from __future__ import division, print_function
from collections import defaultdict
from ConfigParser import ConfigParser
from time import sleep
import traceback

from logbook import Logger, RotatingFileHandler
import pymongo
import tweepy
from requests import ConnectionError, Timeout
from requests.packages.urllib3.exceptions import ProtocolError, ReadTimeoutError

from hortiradar import tokenizeRawTweetText


DATABASE = None
GROUPS = {
    "bloemen": "data/flowers.txt",
    "groente_en_fruit": "data/fruitsandveg.txt"
}

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
        keywords, groups = find_keywords_and_groups(tokens, self.keywords)
        tweet = {
            "tweet": status._json,
            "keywords": keywords,
            "num_keywords": len(keywords),
            "groups": groups,
            "datetime": status.created_at,
        }
        spam = getattr(status, "possibly_sensitive", False)
        if spam:
            tweet["spam"] = 0.7
        self.tweets.insert_one(tweet)

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


def find_keywords_and_groups(tokens, keywords):
    """Returns a list of the keywords and a list of associated groups that occur in tokens."""
    kw = []
    groups = []
    for t in tokens:
        if t[0] == '#':  # hashtags
            t = t[1:]
        t = t.lower()
        g = keywords.get(t, None)
        if g is not None:
            kw.append(t)
            groups += g
    return list(set(kw)), list(set(groups))


def get_keywords():
    """Gets keywords from the source files. keywords is a dictionary where the keys are the
    keywords and the values a list of the groups that keyword is in.
    """
    keywords = defaultdict(set)
    for group_name in GROUPS:
        words = read_keywords(GROUPS[group_name])
        for k in words:
            keywords[k].add(group_name)
    return {k: list(v) for k, v in keywords.items()}


def read_keywords(filename):
    keywords = []
    with open(filename) as f:
        for line in f:
            word = line.decode("utf-8").strip().lower()
            if word[0] == '#':
                word = word[1:]
            keywords.append(word)
    return keywords


def main():
    config = ConfigParser()
    config.read("config.ini")

    auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
    auth.set_access_token(config.get("twitter", "access_key"), config.get("twitter", "access_secret"))
    api = tweepy.API(auth, compression=True, wait_on_rate_limit=True)

    keywords = get_keywords()

    listener = StreamListener(api, keywords)
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