from os.path import dirname

from .api import is_spam
from .keywords import get_db, get_frog, get_keywords
from .selderij import app
from .tasks_master import insert_lemma, insert_tweet
from .tasks_workers import lemmatize


def read_data(filename):
    with open(dirname(__file__) + "/data/{}".format(filename), "r", encoding="utf-8") as f:
        entities = [w.strip() for w in f if not w.startswith("#")]
    return {w: 1 for w in entities}

stop_words = read_data("stoplist-nl.txt")  # stop words to filter out in word cloud
obscene_words = read_data("obscene_words.txt")
blacklist = read_data("blacklist.txt")
