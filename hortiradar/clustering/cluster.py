from calendar import timegm
from collections import Counter
from datetime import datetime
import random

import ujson as json

from hortiradar.clustering import Config, tweet_time_format
from .util import jac, cos_sim, round_time, dt_to_ts

tweet_threshold = Config.getfloat('storify:parameters','tweet_threshold')


class Cluster:

    def __init__(self,tt=None):
        now = datetime.utcnow()
        self.id = dt_to_ts(now)
        self.created_at = round_time(now)
        self.tokens = set()
        self.filt_tokens = set()
        self.tweets = []   
        self.token_counts = Counter()
        self.tweet_counts = Counter()

        self.tweet_threshold = tt if tt else tweet_threshold

    def __eq__(self,other):
        if type(other) == Cluster:
            return self.id == other.id
        else:
            return False

    def is_similar(self,ext_tweet,algorithm="jaccard"):
        if algorithm == "jaccard":
            return jac(self.filt_tokens,set(ext_tweet.filt_tokens)) >= self.tweet_threshold
        elif algorithm == "cosine_similarity":
            return cos_sim(self.filt_tokens,set(ext_tweet.filt_tokens)) >= self.tweet_threshold
        else:
            raise NotImplementedError("This algorithm is not yet implemented.")

    def add_tweet(self,ext_tweet):
        self.tokens.update(ext_tweet.tokens)
        self.filt_tokens.update(ext_tweet.filt_tokens)
        self.tweets.append(ext_tweet)
        self.token_counts.update(ext_tweet.tokens)
        self.tweet_counts[ext_tweet.tweet.id_str] += 1

    def get_best_tweet(self):
        ext_tweets = [tweet for tweet in self.tweets]
        similarities = [jac(self.filt_tokens,set(tweet.filt_tokens)) for tweet in self.tweets]
        max_idx = similarities.index(max(similarities))
        return ext_tweets[max_idx].tweet.id_str

    def get_wordcloud(self):
        wordcloud = []
        for token in self.token_counts:
            if token in self.filt_tokens:
                wordcloud.append({"text": token.lemma.encode('utf-8'), "weight": self.token_counts[token]})

        return wordcloud

    def get_locations(self):
        mapLocations = []
        for ext_tweet in self.tweets:
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
        for ext_tweet in self.tweets:
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
        for ext_tweet in self.tweets:
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
        for ext_tweet in self.tweets:
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
        for ext_tweet in self.tweets:
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
        return {"starting_time": timegm(self.created_at.timetuple())*1000, "display": "circle", "tokens": self.get_tokens()}

    def get_jsondict(self):
        jDict = {}

        jDict["cluster_time"] = datetime.strftime(self.created_at,tweet_time_format)

        jDict["tweets"] = [tw.tweet.id_str for tw in self.tweets]
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