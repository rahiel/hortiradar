from tweepy.api import API
from tweepy.models import Status

from hortiradar.database import stop_words


class ExtendedTweet:

    def __init__(self, tweetDict):
        self.tweet = Status.parse(API(), tweetDict["tweet"])
        try:
            self.keywords = tweetDict["keywords"]
        except KeyError:
            pass
        try:
            self.groups = tweetDict["groups"]
        except KeyError:
            pass
        self.tokens = []
        self.filt_tokens = []
        for token in tweetDict["tokens"]:
            t = Token(token)
            self.tokens.append(t)
            if not t.filter_token():
                self.filt_tokens.append(t)

    def __hash__(self):
        return hash(self.tweet.id_str)

    def __eq__(self, other):
        if type(other) == ExtendedTweet:
            return self.tweet.id_str == other.tweet.id_str
        else:
            return False


class Token:

    def __init__(self, tokenDict):
        self.lemma = tokenDict["lemma"]
        self.pos = tokenDict["pos"]
        self.posprob = tokenDict["posprob"]

    def __hash__(self):
        return hash(self.lemma)

    def __eq__(self, other):
        return self.lemma == other.lemma

    def filter_token(self):
        pos_to_filter = ["BW", "LET", "LID", "VG", "TSW", "VZ", "VNW"]
        match = False
        for ptag in pos_to_filter:
            if ptag in self.pos:
                match = True
                break
        if match:
            return True
        elif ("http" in self.lemma.lower() or self.lemma.lower() in stop_words):
            return True
        else:
            return False
