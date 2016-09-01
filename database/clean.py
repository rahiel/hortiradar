from datetime import datetime, timedelta

from streamer import get_db


tweets = get_db().tweets

# tweet timestamps are in UTC time
two_weeks_ago = datetime.utcnow() - timedelta(days=14)

tweets.delete_many({
    "num_keywords": 0,
    "datetime": {"$lt": two_weeks_ago}
})
