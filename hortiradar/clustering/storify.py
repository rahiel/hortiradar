from datetime import datetime, timedelta

import gensim
from redis import StrictRedis
from sklearn.cluster import AffinityPropagation
import ujson as json

from hortiradar.clustering import ExtendedTweet, Cluster, Stories, tweet_time_format
from hortiradar.database import get_db
from hortiradar.clustering.util import round_time


db = get_db()
groups = [g["name"] for g in db.groups.find({}, projection={"name": True, "_id": False})]
storiesdb = db.stories
tweetsdb = db.tweets

redis = StrictRedis()


def get_tweets(start,end,group):
    jsontweets = tweetsdb.find({
        "groups": group,
        "datetime": {"$gte": start, "$lt": end}
    },projection={
        "tweet.id_str": True, "tokens": True, "tweet.entities": True, "tweet.created_at": True,
        "tweet.user.id_str": True, "tweet.user.screen_name": True, "tweet.retweeted_status.user.id_str": True,
        "tweet.retweeted_status.user.screen_name": True, "tweet.retweeted_status.id_str": True,
        "tweet.in_reply_to_user_id_str": True, "tweet.in_reply_to_screen_name": True,
        "spam": True, "_id": False
    })

    tweets = []
    texts = []
    for jtweet in jsontweets:
        tweets.append(ExtendedTweet(jtweet))
        texts.append([t["lemma"] for t in jtweet["tokens"]])

    dictionaries = gensim.corpora.Dictionary(texts)
    corpus = [dictionaries.doc2bow(text) for text in texts]

    return tweets, corpus

def cluster_tweets(tweets,corpus):
    if len(tweets) > 1:
        mat = gensim.matutils.corpus2csc(corpus)
        X = mat.transpose()
        
        # TODO: figure out why AP throws IndexError
        try:
            af = AffinityPropagation(preference=-25).fit(X)    
        except IndexError:
            try:
                af = AffinityPropagation(preference=-15).fit(X) 
            except IndexError:
                af = AffinityPropagation().fit(X) 

        cluster_labels = af.labels_

        n_clusters = len(af.cluster_centers_indices_)

        clusters = [Cluster() for _ in range(n_clusters)]

        for num,label in enumerate(af.labels_):
            clusters[label].add_tweet(tweets[num])

    else:
        clusters = [Cluster()]
        clusters[0].add_tweet(tweets[0])
        
    return clusters

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
                matched_boolean.append(1)

        for j,story in enumerate(stories):
            if matched_boolean[j] == 0:
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

    return active_stories,finished_stories

def output_stories(stories,group):
    for story in stories:
        storydict = story.get_jsondict()

        storydict["groups"] = group
        storydict["datetime"] = story.closed_at

        storiesdb.insert_one(storydict)

def run_storify(stories,group):
    end = round_time(datetime.utcnow())
    start = end - timedelta(hours=1)
    tweets, corpus = get_tweets(start,end,group)
    
    if tweets:        
        clusters = cluster_tweets(tweets,corpus)

        stories = storify_clusters(stories,clusters)
        stories,finished_stories = find_finished_stories(stories)
        
        if finished_stories:
            output_stories(finished_stories,group)

    return stories

def load_stories(group, start, end):
    closed = storiesdb.find({"groups": group, "datetime": {"$gte": start, "$lt": end}})
    active = redis.get("s:{gr}".format(gr=group))

    return [json.loads(s) for s in active], [json.loads(s) for s in closed]

stories = {}
for group in groups:
    k = "s:{gr}".format(gr=group)
    v = redis.get(k)
    if v:
        stories[group] = v
    else:
        stories[group] = []

    stories[group] = run_storify(stories[group],group)

    redis.set(k,stories[group],ex=60*90)