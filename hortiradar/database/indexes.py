from keywords import get_db


tweets = get_db().tweets


tweets.create_index([("num_keywords", 1), ("datetime", 1)])  # api:/keywords, statistics.py
tweets.create_index([("groups", 1), ("datetime", 1)])  # api:/keywords, api:/groups/{group}
tweets.create_index([("keywords", 1), ("datetime", 1)])  # api:/keywords/{keyword}/*
