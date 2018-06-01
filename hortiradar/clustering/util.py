from collections import Counter
from datetime import datetime
from math import sqrt

from sklearn.metrics.pairwise import cosine_similarity

from hortiradar.clustering import Cluster, Stories

def round_time(dt,interval="hour"):
    if interval == "hour":
        dt = dt.replace(minute=0,second=0,microsecond=0)
    elif interval == "minute":
        dt = dt.replace(second=0,microsecond=0)
    elif interval == "day":
        dt = dt.replace(hour=0,minute=0,second=0,microsecond=0)
    return dt

def dt_to_ts(dt):
    diff = dt - datetime(1970, 1, 1) # use POSIX epoch
    return diff.total_seconds()

def get_token_array(tokens,filt_tokens):
    return [tokens[t] for t in filt_tokens]

def get_tweet_list(obj):
    """returns a list of all tweets in the Stories or Cluster object"""
    if type(obj) not in [Stories, Cluster]:
        raise TypeError("Object type does not contain tweets.")

    tweets = [tw for tw in obj.tweets.elements()]
    for rid in obj.retweets:
        tweets += obj.retweets[rid]

    return tweets

def jac(a,b):
    """ return the Jaccard similarity of two sets"""
    if type(a) != set:
        a = set(a)
    if type(b) != set:
        b = set(b)
    
    n = len(a.intersection(b))
    return n / float(len(a) + len(b) - n)

def cos_sim(a,b):
    if type(a) == list:
        a = np.asarray(a).reshape(1,-1)
    if type(b) == list:
        b = np.asarray(b).reshape(1,-1)

    return cosine_similarity(a,b)[0][0]