from calendar import timegm
from collections import Counter
from datetime import datetime
import random

import numpy as np
import ujson as json

from hortiradar.clustering import Config, tweet_time_format
from .util import cos_sim, round_time, dt_to_ts, get_token_array


class Cluster:

    def __init__(self):
        now = datetime.utcnow()
        self.id = dt_to_ts(now)
        self.created_at = round_time(now)
        self.tokens = Counter()
        self.filt_tokens = set()
        self.tweets = Counter()
        self.retweets = {}

    def __eq__(self,other):
        if type(other) == Cluster:
            return self.id == other.id
        else:
            return False

    def add_tweet(self,ext_tweet):
        self.tokens.update(ext_tweet.tokens)
        self.filt_tokens.update(ext_tweet.filt_tokens)
        if hasattr(ext_tweet.tweet,"retweeted_status"):
            rtid = ext_tweet.tweet.retweeted_status.id_str
            if rtid not in self.retweets:
                self.retweets[rtid] = []
            self.retweets[rtid].append(ext_tweet)
        else:
            self.tweets.update([ext_tweet])

    def get_best_tweet(self):
        cluster_array = get_token_array(self.tokens,self.filt_tokens)
        ext_tweets = [tweet for tweet in self.tweets]
        similarities = []
        for tw in ext_tweets:
            tweet_tokens = Counter(tw.tokens)
            tweet_array = get_token_array(tweet_tokens,self.filt_tokens)
            sim_value = cos_sim(cluster_array,tweet_array)
            if tw.tweet.id_str in self.retweets:
                sim_value *= np.sqrt( len( self.retweets[tw.tweet.id_str] ) )
            similarities.append(sim_value)

        if similarities:
            return ext_tweets[np.argmax(similarities)]
        else:
            return None

    def get_timeseries(self):
        tsDict = Counter()
        for tw in get_tweet_list():
            tweet = tw.tweet
            dt = tweet.created_at
            tsDict.update([(dt.year, dt.month, dt.day, dt.hour)])

        ts = []
        if self.tweets:
            tsStart = sorted(tsDict)[0]
            tsEnd = sorted(tsDict)[-1]
            temp = datetime(tsStart[0], tsStart[1], tsStart[2], tsStart[3], 0, 0)
            while temp <= datetime(tsEnd[0], tsEnd[1], tsEnd[2], tsEnd[3], 0, 0):
                if (temp.year, temp.month, temp.day, temp.hour) in tsDict:
                    ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": tsDict[(temp.year, temp.month, temp.day, temp.hour)]})
                else:
                    ts.append({"year": temp.year, "month": temp.month, "day": temp.day, "hour": temp.hour, "count": 0})

                temp += timedelta(hours=1)

        return ts

    def get_wordcloud(self):
        wordcloud = []
        for token in self.token_counts:
            if token in self.filt_tokens:
                wordcloud.append({"text": token.lemma.encode('utf-8'), "weight": self.token_counts[token]})

        return wordcloud

    def get_locations(self):
        mapLocations = []
        for ext_tweet in get_tweet_list():
            try:
                if ext_tweet.tweet.coordinates is not None:
                    if ext_tweet.tweet.coordinates.type == "Point":
                        coords = ext_tweet.tweet.coordinates.coordinates
                        mapLocations.append({"lng": coords[0], "lat": coords[1]})
            except AttributeError:
                pass

        lng = 0
        lat = 0
        if mapLocations:
            for loc in mapLocations:
                lng += loc["lng"]
                lat += loc["lat"]
                avLoc = {"lng": lng / len(mapLocations), "lat": lat / len(mapLocations)}
        else:
            avLoc = {"lng": 5, "lat": 52}

        return {"locs": mapLocations, "avLoc": avLoc}

    def get_images(self):
        imagesList = []
        for ext_tweet in get_tweet_list():
            try:
                for obj in ext_tweet.tweet.entities["media"]:
                    imagesList.append(obj["media_url_https"])
            except KeyError:
                pass

        images = []
        for (url, count) in Counter(imagesList).most_common():
            images.append({"link": url, "occ": count})

        return images

    def get_URLs(self):
        URLList = []
        for ext_tweet in get_tweet_list():
            try:
                for obj in ext_tweet.tweet.entities["urls"]:
                    url = obj["expanded_url"]
                    if url is not None:
                        URLList.append(url)
            except KeyError:
                pass

        urls = []
        for (url, count) in Counter(URLList).most_common():
            urls.append({"link": url, "occ": count})

        return urls

    def get_hashtags(self):
        htlist = []
        for ext_tweet in get_tweet_list():
            try:
                for obj in ext_tweet.tweet.entities["hashtags"]:
                    htlist.append(obj["text"])
            except AttributeError:
                pass

        hashtags = []
        for (ht, count) in Counter(htlist).most_common():
            hashtags.append({"ht": ht, "occ": count})

        return hashtags

    def get_interaction_graph(self):
        nodes = {}
        edges = []
        for ext_tweet in get_tweet_list():
            tweet = ext_tweet.tweet
            user_id_str = tweet.user.id_str
            try:
                rt_user_id_str = tweet.retweeted_status.user.id_str

                if rt_user_id_str not in nodes:
                    nodes[rt_user_id_str] = tweet.retweeted_status.user.screen_name
                if user_id_str not in nodes:
                    nodes[user_id_str] = tweet.user.screen_name

                edges.append({"source": rt_user_id_str, "target": user_id_str, "value": "retweet"})
            except AttributeError:
                pass

            try:
                for obj in tweet.entities["user_mentions"]:
                    if obj["id_str"] not in nodes:
                        nodes[obj["id_str"]] = obj.screen_name
                    if user_id_str not in nodes:
                        nodes[user_id_str] = tweet.user.screen_name

                    edges.append({"source": user_id_str, "target": obj.id_str, "value": "mention"})
            except AttributeError:
                pass

            try:
                if tweet.in_reply_to_user_id_str not in nodes:
                    nodes[tweet.in_reply_to_user_id_str] = tweet.in_reply_to_screen_name
                if user_id_str not in nodes:
                    nodes[user_id_str] = tweet.user.screen_name

                edges.append({"source": user_id_str, "target": tweet.in_reply_to_user_id_str, "value": "reply"})
            except AttributeError:
                pass

        graph = {"nodes": [], "edges": []}
        for node in nodes:
            graph["nodes"].append({"id": nodes[node]})

        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            graph["edges"].append({"source": nodes[source], "target": nodes[target], "value": edge["value"]})

        return graph

    def get_tokens(self):
        return [token.lemma.encode('utf-8') for token in self.filt_tokens]

    def get_cluster_details(self):
        best_tw = self.get_best_tweet()
        return {"starting_time": timegm(self.created_at.timetuple())*1000, "display": "circle", "summarytweet": best_tw.tweet.text}

    def get_tweet_list(self):
        """returns a list of all tweets in the Cluster object"""
        tweets = [tw for tw in self.tweets.elements()]
        for rid in self.retweets:
            tweets += self.retweets[rid]

        return tweets

    def get_jsondict(self):
        jDict = {}

        jDict["cluster_time"] = datetime.strftime(self.created_at,tweet_time_format)

        jDict["tweets"] = [tw.tweet.id_str for tw in get_tweet_list()]
        jDict["summary_tweet"] = self.get_best_tweet()

        jDict["tokens"] = self.get_tokens()
        
        jDict["timeSeries"] = self.get_timeseries()
        
        jDict["photos"] = self.get_images()
        jDict["URLs"] = self.get_URLs()
        jDict["tagCloud"] = self.get_wordcloud()
        jDict["hashtags"] = self.get_hashtags()
        
        loc_result = self.get_locations()
        jDict["locations"] = loc_result["locs"]
        jDict["centerloc"] = loc_result["avLoc"]

        jDict["graph"] = self.get_interaction_graph()

        return jDict