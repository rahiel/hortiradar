from configparser import ConfigParser
from time import sleep
import traceback

import tweepy
import ujson as json
from logbook import Logger, RotatingFileHandler
from redis import StrictRedis
from requests import ConnectionError, Timeout
from requests.packages.urllib3.exceptions import ProtocolError, ReadTimeoutError

from tasks_workers import find_keywords_and_groups


RotatingFileHandler("twitter.log", backup_count=5).push_application()
log = Logger("main")
log.info("Started")

redis = StrictRedis()


class StreamListener(tweepy.StreamListener):
    """Tweepy will continuously receive notices from Twitter and dispatches
    them to one of the event handlers.
    """
    def __init__(self, api):
        self.api = api

    def on_status(self, status):
        """Handle arrival of a new tweet."""
        j = filter_tweet(clean_tweet(status._json))
        redis.set("t:" + j["id_str"], json.dumps(j))
        if "retweeted_status" in j:
            retweet_id_str = j["retweeted_status"]["id_str"]
        else:
            retweet_id_str = None
        find_keywords_and_groups.apply_async((j["id_str"], j["text"], retweet_id_str), queue="workers")

    def on_delete(self, status_id, user_id):
        """A user deleted a tweet, respect their decision by also deleting it
        on our end.
        """
        status_id, user_id = str(status_id), str(user_id)
        log.notice("on_delete: status_id = {}, user_id = {}".format(status_id, user_id))
        self.tweets.delete_one({"tweet.id_str": status_id})

    def on_error(self, status_code):
        """This does the Twitter-recommended exponential backoff when it
        returns non-False and disconnects on False.
        """
        log.error("on_error: status_code = {}".format(status_code))
        if status_code == 420:  # rate limit
            return True


def clean_tweet(j):
    """Clean the tweet json from redundant fields. For example duplicate data in
    integer/string form and http/https forms of URLs.
    """
    # The following fields are deprecated: https://dev.twitter.com/overview/api/tweets
    del j["contributors"]
    del j["geo"]

    # these are redundant because we have `id_str` versions of them
    del j["id"]
    del j["in_reply_to_status_id"]
    del j["in_reply_to_user_id"]
    if j.get("quoted_status_id"):
        del j["quoted_status_id"]

    # user
    del j["user"]["id"]
    del j["user"]["profile_background_image_url"]  # profile_background_image_url_https
    del j["user"]["profile_image_url"]             # profile_image_url_https

    # entities
    if j["entities"].get("media"):
        for m in j["entities"]["media"]:
            del m["id"]         # id_str
            del m["media_url"]  # media_url_https
            if m.get("source_status_id"):
                del m["source_status_id"]  # source_status_id_str
    if j["entities"].get("user_mentions"):
        for mention in j["entities"]["user_mentions"]:
            del mention["id"]

    # retweet data
    if j.get("retweeted_status"):
        j["retweeted_status"] = clean_tweet(j["retweeted_status"])

    # truncated tweets, replace data with extended_tweet
    if j["truncated"]:
        if j.get("extended_tweet"):
            ext = j["extended_tweet"]
            if ext.get("full_text"):
                j["text"] = ext["full_text"]
            del j["extended_tweet"]
    del j["truncated"]

    return j


def filter_tweet(j):
    """Filter the tweet JSON from data we won't use."""
    if j.get("display_text_range"):
        del j["display_text_range"]
    del j["timestamp_ms"]

    def filter_entities(entities):
        if entities.get("media"):
            for m in entities["media"]:
                del m["url"]
                del m["display_url"]
                del m["expanded_url"]
                del m["indices"]
                del m["sizes"]

        if entities.get("hashtags"):
            for h in entities["hashtags"]:
                del h["indices"]

        if entities.get("symbols"):
            for s in entities["symbols"]:
                del s["indices"]

        if entities.get("urls"):
            for u in entities["urls"]:
                del u["indices"]
                del u["display_url"]
                del u["url"]

        if entities.get("user_mentions"):
            for m in entities["user_mentions"]:
                del m["indices"]
                del m["name"]

        return entities

    j["entities"] = filter_entities(j["entities"])
    if j.get("extended_entities"):
        j["extended_entities"] = filter_entities(j["extended_entities"])

    del j["user"]["time_zone"]
    del j["user"]["contributors_enabled"]
    del j["user"]["profile_background_color"]
    del j["user"]["profile_background_image_url_https"]
    del j["user"]["profile_background_tile"]
    if j["user"].get("profile_banner_url"):
        del j["user"]["profile_banner_url"]
    del j["user"]["profile_image_url_https"]
    del j["user"]["profile_link_color"]
    del j["user"]["profile_sidebar_border_color"]
    del j["user"]["profile_sidebar_fill_color"]
    del j["user"]["profile_text_color"]
    del j["user"]["profile_use_background_image"]
    del j["user"]["default_profile"]
    del j["user"]["default_profile_image"]

    return j


def main():
    config = ConfigParser()
    config.read("streamer.ini")
    config = config["twitter"]

    auth = tweepy.OAuthHandler(config["consumer_key"], config["consumer_secret"])
    auth.set_access_token(config["access_key"], config["access_secret"])
    api = tweepy.API(auth, compression=True, wait_on_rate_limit=True)

    listener = StreamListener(api)
    stream = tweepy.Stream(auth=auth, listener=listener)

    with open("data/stoplist_nl_extended.txt") as f:
        track = [str(l.split()[0]) for l in f.readlines()]   # list of most common Dutch words

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
