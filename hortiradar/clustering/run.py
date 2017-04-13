from datetime import datetime, timedelta
from time import sleep

### TODO: import werkt nog niet, moet aangepast worden bij integratie
from keywords import get_db

from cluster import Cluster
from stories import Stories
from tweet import ExtendedTweet
from util import jac

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
    # TODO: clusters worden weggeschreven naar bestanden, dit moet nog aangepast worden naar cache
    with open("clusters/{dt}_clusters.json".format(dt=now.strftime("%Y%m%d_%H")),"w") as f:
        json.dump(jsonify_clusters(clusters),f)

def storify_clusters(stories,clusters):
    if not stories:
            for c in clusters:
                stories.append(Stories(len(stories),c))
        else:
            current_stories = get_current_stories(stories)

            for c in clusters:
                matched = False
                for i,story in enumerate(current_stories):
                    if story.is_similar(c):
                        matched = True
                        story.add_cluster(c)
                        storyToRemove = i

                if matched:
                    current_stories.pop(storyToRemove)
                else:
                    stories.append(Stories(len(stories),c))

            for story in current_stories:
                story.add_delay()
                if story.close_story():
                    story.end_story()

    return stories

def get_current_stories(stories):
    current_stories = []
    for story in stories:
        if not story.close_story():
            current_stories.append(story)

    return current_stories

def get_finished_stories(stories):
    finished_stories = []
    for story in stories:
        if story.close_story():
            finished_stories.append(story)

    return finished_stories

def get_new_finished_stories(stories):
    finished_stories = []
    for story in stories:
        if story.close_story() and story.has_been_outputted==False:
            finished_stories.append(story)

    return finished_stories

def jsonify_stories(stories):
    jsonDict = {"stories": []}
    for story in stories:
        jsonDict["stories"].append(story.get_json())

    return jsonDict

def output_stories(stories,now):
    finished_stories = []
    for story in stories:
        if story.close_story() and story.has_been_outputted==False:
            finished_stories.append(story)
            story.has_been_outputted = True

    # TODO: stories worden weggeschreven naar bestanden, dit moet nog aangepast worden naar cache
    with open("stories/{dt}_finished_stories.json".format(dt=now.strftime("%Y%m%d_%H")),"w") as f:
        json.dump(jsonify_stories(finished_stories),f)

def main():
    stories = []

    while True:
        now = datetime.utcnow()
        clusters = cluster_tweets(now)
        output_clusters(clusters,now)
        
        stories = storify_clusters(stories,clusters)
        output_stories(stories,now)

        seconds_to_sleep = get_sleep_time()
        sleep(seconds_to_sleep)

if __name__ == '__main__':
    main()