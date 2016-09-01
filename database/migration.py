from streamer import get_db, get_keywords, find_keywords_and_groups

from hortiradar import tokenizeRawTweetText

tweets = get_db().tweets
keywords = get_keywords()


tw = tweets.find()
for t in tw:
    tokens = tokenizeRawTweetText(t["tweet"]["text"])
    kws, groups = find_keywords_and_groups(tokens, keywords)
    tweets.update_one({"_id": t["_id"]}, {
        "$set": {
            "keywords": kws,
            "groups": groups,
            "num_keywords": len(kws)
        }
    })
