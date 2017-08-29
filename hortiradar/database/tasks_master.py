from datetime import datetime
from typing import Sequence

import ujson as json
from redis import StrictRedis

from hortiradar.database import app, get_db


redis = StrictRedis()
db = get_db()

# the "created_at" field, example: 'Tue Jun 28 15:01:54 +0000 2016'
tweet_time_format = "%a %b %d %H:%M:%S +0000 %Y"


@app.task
def insert_tweet(id_str, keywords, groups, tokens):
    """Task to insert tweet into MongoDB."""
    key = "t:" + id_str
    j = json.loads(redis.get(key))
    tweet = {
        "tweet": j,
        "keywords": keywords,
        "num_keywords": len(keywords),
        "groups": groups,
        "tokens": tokens,
        "datetime": datetime.strptime(j["created_at"], tweet_time_format),
    }
    spam = j.get("possibly_sensitive", False)
    if spam:
        tweet["spam"] = 0.7
    db.tweets.insert_one(tweet)
    redis.delete(key)


@app.task
def insert_lemma(key: str, lemmas: Sequence[str]):
    redis.set(key, json.dumps(lemmas), ex=60 * 30)
