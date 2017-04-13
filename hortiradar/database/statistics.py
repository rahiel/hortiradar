import ujson as json
from redis import StrictRedis

from keywords import get_db


db = get_db()
redis = StrictRedis()

format_count = lambda c: "{:,}".format(c)  # use , for thousands separator
clean_count = lambda c: int(c.replace(",", ""))

stats = db.command("collstats", "tweets", scale=int(1E9))
count = stats["count"]               # number of tweets
size = stats["size"]                 # raw collection size
storage_size = stats["storageSize"]  # compressed collection size

oldest_tweet = db.tweets.find({"num_keywords": 0}).sort("datetime", 1).limit(1)[0]
latest_tweet = db.tweets.find({"num_keywords": 0}).sort("datetime", -1).limit(1)[0]
oldest_date = oldest_tweet["datetime"].strftime("%Y-%m-%d")
latest_date = latest_tweet["datetime"].strftime("%Y-%m-%d")

try:
    prev_stats = json.loads(redis.get("t:stats"))
    prev_count = clean_count(prev_stats["count"])
except TypeError:
    prev_count = 0
count_24h = count - prev_count  # number of tweets in the last 24h

stats = {
    "count": format_count(count),
    "count_24h": format_count(count_24h),
    "size": size,
    "storage_size": storage_size,
    "date_oldest_tweet": oldest_date,
    "date_latest_tweet": latest_date
}
redis.set("t:stats", json.dumps(stats))
