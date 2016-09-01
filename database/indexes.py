from streamer import get_db


tweets = get_db().tweets


tweets.create_index([("num_keywords", 1), ("datetime", 1)])  # api:/keywords
tweets.create_index([("groups", 1), ("datetime", 1)])  # api:/keywords
tweets.create_index([("keywords", 1), ("datetime", 1)])  # api:/keywords/{keyword}/*
