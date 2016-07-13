from datetime import datetime, timedelta

from main import get_db


tweets = get_db().tweets

# tweet timestamps are in UTC time
two_weeks_ago = datetime.utcnow() - timedelta(days=14)

# parse tweet timestamps
tw = tweets.find({"datetime": {"$exists": False}})
time_format = "%a %b %d %H:%M:%S +0000 %Y"  # 'Tue Jun 28 15:01:54 +0000 2016'
for t in tw:
    dt = datetime.strptime(t["tweet"]["created_at"], time_format)
    tweets.update_one({"_id": t["_id"]}, {"$set": {"datetime": dt}})


tweets.delete_many({
    "num_keywords": 0,
    "datetime": {"$lt": two_weeks_ago}
})
