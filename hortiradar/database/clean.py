from datetime import datetime, timedelta

from keywords import get_db


tweets = get_db().tweets

# tweet timestamps are in UTC time
limit = datetime.utcnow() - timedelta(days=31 * 15)

tweets.delete_many({
    "num_keywords": 0,
    "datetime": {"$lt": limit}
})
