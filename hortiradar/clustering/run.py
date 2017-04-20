from datetime import datetime, timedelta
from time import sleep

from redis import StrictRedis

from hortiradar.database import get_db

from cluster import Cluster
from stories import Stories
from tweet import ExtendedTweet
from util import jac, round_time

redis = StrictRedis()
db = get_db()

def get_sleep_time(now):
    next = cast_to_interval(now)
    seconds_to_sleep = (next-now).total_seconds()
    return seconds_to_sleep

def cast_to_interval(dt,jump="forward"):
    if jump == "forward":
        dt = dt+timedelta(hours=1)
    elif jump == "backward":
        dt = dt+timedelta(hours=-1)
    dt = dt.replace(minute=30,second=0,microsecond=0)
    return dt

def get_recent_tweets(end):
    ## TODO: Currently directly queried from db, could be adjusted to Tweety call
    query = {
        "num_keywords": {"$gt": 0},
        "datetime": {"$gte": cast_to_interval(end,jump="backward"), "$lt": end}
    }

    tweetsdb = db.tweets
    tweetCursor = tweetsdb.find(query,projection={"_id": False, "datetime": False})

    tweets = []
    for item in tweetCursor:
        tweet = ExtendedTweet(item)
        tweets.append(tweet)

    return tweets

def cluster_tweets(now):
    clusters = []

    tweets = get_recent_tweets(now)

    for tweet in tweets:
        found_match = False

        for cluster in clusters:
            if cluster.is_similar(tweet):
                found_match = True
                cluster.add_tweet(tweet)
                break

        if not found_match:
            cluster = Cluster(tweet)
            clusters.append(cluster)

    return clusters

def jsonify_clusters(clusters):
    jsonDict = {"clusters": []}
    for cluster in clusters:
        jsonDict["clusters"].append(cluster.get_json())

    return jsonDict

def output_clusters(clusters,now):
    output = jsonify_clusters(clusters)
    output["clustertime"] = round_time(now)
    db.clusters.insert_one(output)

def storify_clusters(stories,clusters):
    if not stories:
        for c in clusters:
            stories.append(Stories(c))
    else:
        matched_boolean = [0]*len(stories)

        for c in clusters:
            matched = False
            for i,story in enumerate(stories):
                if story.is_similar(c):
                    matched = True
                    story.add_cluster(c)
                    match_position = i

            if matched:
                matched_boolean[match_position] = 1
            else:
                stories.append(Stories(c))

        for j,story in enumerate(current_stories):
            if matched_boolean[j] == 0:
                story.add_delay()
                if story.close_story():
                    story.end_story()

    return stories

def jsonify_stories(stories):
    jsonDict = {"stories": []}
    for story in stories:
        jsonDict["stories"].append(story.get_json())

    return jsonDict

def insert_story(story):
    db.stories.insert_story(story.get_json())

def output_finished_stories(stories):
    active_stories = []
    for story in stories:
        if story.close_story():
            story.end_story()            
            insert_story(story)
        else:
            active_stories.append(story)

    return active_stories

stories = []

while True:
    now = datetime.utcnow()
    clusters = cluster_tweets(now)
    redis.set("clusters",jsonify_clusters(clusters))
    output_clusters(clusters,now)
    
    stories = storify_clusters(stories,clusters)
    stories = output_finished_stories(stories)
    redis.set("stories",jsonify_stories(stories))

    seconds_to_sleep = get_sleep_time(now)
    sleep(seconds_to_sleep)