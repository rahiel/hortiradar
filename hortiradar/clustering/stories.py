import calendar
from collections import Counter
from datetime import datetime
import json

from hortiradar.clustering import Config
from hortiradar.clustering.util import jac, round_time, get_time_passed

class Stories:
    """
    Tracks clusters with similar content over longer time periods

    Parameters:
    max_idle:               Maximum amount of intervals that the story can be idle (no cluster is added)
    J_threshold:            Jaccard index threshold for adding cluster w.r.t. latest added tokens
    J_original_threshold:   Jaccard index threshold for adding cluster w.r.t. first added tokens

    Attributes:
    tokens:                 Set of tokens that were added last_edited
    original_tokens:        Set of tokens that were added on creation
    filt_tokens:            Set of filtered tokens that were added last_edited
    original_filt_tokens:   List of filtered tokens that were added on creation
    last_edited:            Number of iterations ago that a cluster was added
    token_counts:           Frequencies that tokens are used in tweets
    tweets:                 Set of tweets corresponding to the story
    time_series:            List of number of tweets per hour in story
    """
    max_idle = Config.getint('Parameters','max_idle')
    J_threshold = Config.getfloat('Parameters','cluster_jac_threshold')
    J_original_threshold = Config.getfloat('Parameters','cluster_original_jac_threshold')

    def __init__(self,c):
        self.created_at = datetime.utcnow()
        self.last_edited = 0
        
        self.tokens = c.tokens
        self.filt_tokens = c.filt_tokens

        self.original_tokens = c.tokens
        self.original_filt_tokens = c.filt_tokens
        
        self.tweets = Counter(c.tweets)
        self.token_counts = c.token_counts
        self.first_tweet_time = min([tw.tweet.created_at for tw in self.tweets])
        self.time_series = self.calc_TS()

    def __str__(self):
        return ",".join([token.lemma for token in self.filt_tokens])

    def is_similar(self,c): ## was CalcMatch
        """Calculate if the cluster matches to the story"""
        currentJaccard = jac(self.filt_tokens,c.filt_tokens)
        originalJaccard = jac(self.original_filt_tokens,c.filt_tokens)
        return (currentJaccard >= self.J_threshold and originalJaccard >= self.J_original_threshold)

    def add_cluster(self,c): ## was addTime
        """Add a new cluster to the story"""
        self.tokens.update(c.tokens)
        self.filt_tokens.update(c.filt_tokens)
        self.token_counts.update(c.token_counts)
        for tweet in c.tweets:
            self.tweets[tweet] += 1
        
        self.first_tweet_time = min([tw.tweet.created_at for tw in self.tweets])
        self.time_series = self.calc_TS()

    def add_delay(self):
        """Update idle time counter"""
        self.last_edited+=1

    def close_story(self):
        """Check if idle time has passed. If function returns true, then call endStory()"""
        return self.last_edited >= self.max_idle

    def end_story(self):
        """Add closing time to Story and calculate time series"""
        self.closed_at = datetime.utcnow()

    def calc_TS(self):
        """Given an array of datetime objects, return the time series."""
        rounded_times = [round_time(tw.tweet.created_at) for tw in self.tweets]
        TS_counter = Counter(rounded_times)

        start = min(rounded_times)
        end = max(rounded_times)

        TS_length = int(get_time_passed(start,end))+1
        TS = [0]*TS_length

        for dt in rounded_times:
            interval = int(get_time_passed(dt,end))
            TS[interval] += 1

        self.time_series = TS

    def get_best_tweet(self):
        ext_tweets = [tweet for tweet in self.tweets]
        similarities = [jac(self.filt_tokens,set(tweet.filt_tokens)) for tweet in self.tweets]
        max_idx = similarities.index(max(similarities))
        return ext_tweets[max_idx].tweet.text

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

    def get_original_wordcloud(self):
        wordcloud = []
        for token in self.original_filt_tokens:
            wordcloud.append({"text": token.lemma, "weight": self.token_counts[token]})

        return wordcloud

    def write_to_file(self,loc=""):
        outputloc = loc+self.created_at.strftime("story_%Y%m%d_%H%M%S_%f")
        with open(outputloc,w) as f:
            json.dump(self.get_json,f)

    def get_json(self): ## was writeJSON
        """Builds the dict for output to JSON"""
        loc_result = self.get_locations()
        
        jDict = {}
        jDict["startStory"] = datetime.strftime(self.created_at,"%Y-%m-%d %Hh")
        try:
            jDict["endStory"] = datetime.strftime(self.closed_at,"%Y-%m-%d %Hh")
        except AttributeError:
            pass
        jDict["firstTweetTime"] = calendar.timegm(self.first_tweet_time.timetuple())
        jDict["ts"] = self.time_series
        jDict["original_wordcloud"] = self.get_original_wordcloud()
        
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