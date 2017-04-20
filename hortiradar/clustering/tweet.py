import ujson as json

from tweepy.api import API
from tweepy.models import Status

# TODO: maybe make stop_words part of variables for database package? like get_db currently
with open("/home/rahiel/hortiradar/hortiradar/database/data/stoplist-nl.txt", encoding='utf-8') as f:
    stop_words = [w.strip("\n") for w in f.readlines()]

class ExtendedTweet:
    
    def __init__(self,tweetDict):
        self.tweet = Status.parse(API(),tweetDict["tweet"])
        self.keywords = tweetDict["keywords"]
        self.groups = tweetDict["groups"]
        self.tokens = []
        self.filt_tokens = []
        for token in tweetDict["tokens"]:
            t = Token(token)
            self.tokens.append(t)
            if not t.filter_token():
                self.filt_tokens.append(t)

    def __hash__(self):
        return hash(self.tweet.id_str)

    def __eq__(self,other):
        if type(other) == ExtendedTweet:
            return self.tweet.id_str == other.tweet.id_str
        else:
            return False

    def print_tokens(self):
        print([str(token) for token in self.filt_tokens])

class Token:

    def __init__(self,tokenDict):
        self.lemma = tokenDict["lemma"]
        self.pos = tokenDict["pos"]
        self.posprob = tokenDict["posprob"]

    def __str__(self):
        return self.lemma

    def __repr__(self):
        return self.lemma

    def __hash__(self):
        return hash(self.lemma)

    def __eq__(self,other):
        return self.lemma == other.lemma

    def filter_token(self):
        if ("LET" in self.pos or "BW" in self.pos or "WW" in self.pos):
            return True
        elif ("http" in self.lemma.lower() or self.lemma.lower() in stop_words):
            return True
        else:
            return False