from configparser import ConfigParser

from redis import StrictRedis
import ujson as json

from keywords import get_frog, get_keywords
from selderij import app
from tasks_master import insert_tweet


keywords = get_keywords()

config = ConfigParser()
config.read("tasks_workers.ini")
posprob_minimum = config["workers"].getfloat("posprob_minimum")

r = StrictRedis()
rt_cache_time = 60 * 60 * 6


@app.task
def find_keywords_and_groups(id_str, text, retweet_id_str):
    """Find the keywords and associated groups in the tweet."""
    # First check if retweets are already processed in the cache
    if retweet_id_str:
        key = "t:%s" % retweet_id_str
        rt = r.get(key)
        if rt:
            kw, groups, tokens = json.loads(rt)
            insert_tweet.apply_async((id_str, kw, groups, tokens), queue="master")
            r.expire(key, ex=rt_cache_time)
            return

    frog = get_frog()
    tokens = frog.process(text)  # a list of dictionaries with frog's analysis per token
    kw = []
    groups = []
    for t in tokens:
        lemma = t["lemma"].lower()
        k = keywords.get(lemma, None)
        if k is not None:
            if t["posprob"] > posprob_minimum:
                if not t["pos"].startswith(k.pos + "("):
                    continue
            kw.append(lemma)
            groups += k.groups
    kw, groups = list(set(kw)), list(set(groups))
    insert_tweet.apply_async((id_str, kw, groups, tokens), queue="master")

    # put retweets in the cache
    if retweet_id_str:
        data = [kw, groups, tokens]
        r.set(key, json.dumps(data), ex=rt_cache_time)
