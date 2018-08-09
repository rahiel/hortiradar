from datetime import datetime, timedelta
from getopt import getopt, GetoptError
import pickle
import sys

import gensim
import numpy as np
from redis import StrictRedis
from scipy.sparse import csgraph

from hortiradar.clustering import Config, ExtendedTweet, Cluster, Stories
from hortiradar.clustering.util import round_time
from hortiradar.database import get_db, get_keywords


db = get_db()
groups = [g["name"] for g in db.groups.find({}, projection={"name": True, "_id": False})]
storiesdb = db.stories
tweetsdb = db.tweets

keywords = get_keywords(local=True)

redis = StrictRedis()

spam_level = Config.getfloat('database:parameters', "spam_level")
tweet_threshold = Config.getfloat('storify:parameters', 'tweet_threshold')

def is_spam(t):
    return t.get("spam") is not None and t["spam"] > spam_level

def get_filt_tokens(tweet):
    return [t.lemma for t in tweet.tokens if not t.filter_token()]

def get_tweets(start, end, key, keytype):
    jsontweets = tweetsdb.find({
        keytype: key,
        "datetime": {"$gte": start, "$lt": end}
    }, projection={
        "tweet.id_str": True, "tokens": True, "tweet.entities": True, "tweet.created_at": True,
        "tweet.user.id_str": True, "tweet.user.screen_name": True, "tweet.retweeted_status.user.id_str": True,
        "tweet.retweeted_status.user.screen_name": True, "tweet.retweeted_status.id_str": True,
        "tweet.in_reply_to_user_id_str": True, "tweet.in_reply_to_screen_name": True,
        "tweet.text": True, "spam": True, "_id": False
    })

    tweets = []
    for jtweet in jsontweets:
        if not is_spam(jtweet):
            tweets.append(ExtendedTweet(jtweet))

    return tweets

def perform_clustering(tweets, stories, key):
    non_retweets = []
    for tw in tweets:
        if hasattr(tw.tweet, "retweeted_status"):
            rt_id_str = tw.tweet.retweeted_status.id_str
            for story in stories:
                story_tweet_ids = [tw.tweet.id_str for tw in story.tweets]
                if rt_id_str in story_tweet_ids:
                    story.add_tweet(tw)
                    break
        else:
            non_retweets.append(tw)

    if non_retweets:
        clusters = perform_clustering_tweets(non_retweets, key)
    else:
        clusters = []

    return clusters, stories

def perform_clustering_tweets(tweets, key):
    texts = [get_filt_tokens(tw) for tw in tweets]
    dictionaries = gensim.corpora.Dictionary(texts)
    corpus = [dictionaries.doc2bow(text) for text in texts]
    sims = gensim.similarities.Similarity('/tmp/clustering_{g}'.format(g=key), corpus, num_features=len(dictionaries))

    mat = []
    for j, tw in enumerate(tweets):
        mat.append([1 if x > tweet_threshold else 0 for x in sims[dictionaries.doc2bow(get_filt_tokens(tw))]])

    n_clusters, cluster_labels = csgraph.connected_components(mat, directed=False)
    clusters = [Cluster() for _ in range(n_clusters)]

    for num, label in enumerate(cluster_labels):
        clusters[label].add_tweet(tweets[num])

    return clusters

def storify_clusters(stories, clusters):
    if not stories:
        for c in clusters:
            stories.append(Stories(c))
    else:
        matched_boolean = [False] * len(stories)

        for c in clusters:
            sim, vals = zip(*[s.is_similar(c) for s in stories])
            match = False
            for m in np.flipud(np.argsort(vals)):
                if sim[m]:
                    match = True
                    break

            if match and not matched_boolean[m]:
                stories[m].add_cluster(c)
                matched_boolean[m] = True
            else:
                stories.append(Stories(c))
                matched_boolean.append(True)

        for j, story in enumerate(stories):
            if not matched_boolean[j]:
                story.add_delay()
                if story.close_story():
                    story.end_story()

    return stories

def find_finished_stories(stories):
    active_stories = []
    finished_stories = []
    for story in stories:
        if story.close_story():
            story.end_story()
            finished_stories.append(story)
        else:
            active_stories.append(story)

    return active_stories, finished_stories

def output_stories(stories, key, keytype):
    for story in stories:
        storydict = story.get_jsondict()

        storydict[keytype] = key
        storydict["datetime"] = story.closed_at

        storiesdb.insert_one(storydict)

def run_storify(stories, key, keytype):
    end = round_time(datetime.utcnow())
    start = end - timedelta(hours=1)
    tweets = get_tweets(start, end, key, keytype)

    if tweets:
        clusters, stories = perform_clustering(tweets, stories, key)

        stories = storify_clusters(stories, clusters)
        stories, finished_stories = find_finished_stories(stories)

        if finished_stories:
            output_stories(finished_stories, key, keytype)

    return stories

def process_key(key, keytype):
    k = "s:{k}".format(k=key)
    v = redis.get(k)
    if v:
        stories = pickle.loads(v)
    else:
        stories = []

    stories = run_storify(stories, key, keytype)

    stories_out = pickle.dumps(stories)
    redis.set(k, stories_out, ex=60 * 90)

def main(argv):
    try:
        opts, args = getopt(argv, "ht:", ["type="])
    except GetoptError:
        print("test.py -t <processing type>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("test.py -t <processing type>")
            sys.exit()
        elif opt in ["-t", "--type"]:
            if arg == "groups":
                for group in groups:
                    process_key(group, arg)
            elif arg == "keywords":
                for keyword in keywords:
                    process_key(keyword, arg)
            else:
                raise(NotImplementedError)


if __name__ == "__main__":
    main(sys.argv[1:])
