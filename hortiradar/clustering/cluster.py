from collections import Counter
from configparser import ConfigParser
from datetime import datetime
import json

from tweet import ExtendedTweet
from util import jac, cos_sim

Config = ConfigParser()
Config.read('config.ini')

class Cluster:
    def __init__(self,ext_tweet):
        self.tokens = set(ext_tweet.tokens)
        self.filt_tokens = set(ext_tweet.filt_tokens)
        self.tweets = [ext_tweet]   
        self.token_counts = Counter(ext_tweet.tokens)
        self.tweet_counts = Counter(ext_tweet.tweet.id_str)
        self.created_at = datetime.utcnow()

    def __str__(self):
        return ",".join([token.lemma for token in self.filt_tokens])

    def is_similar(self,ext_tweet,algorithm="jaccard"):
        t = set(ext_tweet.tokens)
        if algorithm == "jaccard":
            return jac(self.filt_tokens,set(ext_tweet.filt_tokens)) >= Config.getfloat('Parameters','tweet_jac_threshold')
        else:
            raise NotImplementedError("This algorithm is not yet implemented.")

    def add_tweet(self,ext_tweet):
        self.tweets.append(ext_tweet)
        self.tweet_counts[ext_tweet.tweet.id_str] += 1
        self.filt_tokens.update(ext_tweet.filt_tokens)
        self.token_counts.update(ext_tweet.tokens)
        for token in ext_tweet.tokens:
            self.tokens.add(token)

    def get_best_tweet(self):
        similarities = [jac(self.filt_tokens,set(tweet.filt_tokens)) for tweet in self.tweets]
        max_idx = similarities.index(max(similarities))
        return self.tweets[max_idx].tweet.text

    def get_wordcloud(self):
        wordcloud = []
        for token in self.token_counts:
            if token in self.filt_tokens:
                wordcloud.append({"text": token.lemma, "weight": self.token_counts[token]})

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

    def write_to_file(self,loc=""):
        outputloc = loc+self.created_at.strftime("cluster_%Y%m%d_%H%M%S_%f")
        with open(outputloc,w) as f:
            json.dump(self.get_json,f)

    def get_json(self):
        loc_result = self.get_locations()
        
        jDict = {}
        jDict["tokens"] = [token.lemma for token in self.filt_tokens]
        jDict["num_tweets"] = len(self.tweets)
        jDict["locations"] = loc_result["locs"]
        jDict["avLoc"] = loc_result["avLoc"]
        jDict["images"] = self.get_images()
        jDict["urls"] = self.get_URLs()
        jDict["wordcloud"] = self.get_wordcloud()
        jDict["hashtags"] = self.get_hashtags()
        jDict["best_tweet"] = self.get_best_tweet()
        jDict["tweets"] = [tw.tweet.id_str for tw in self.tweets]
        return jDict