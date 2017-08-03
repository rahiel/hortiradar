from os.path import dirname

from .keywords import get_db


def read_data(filename):
    with open(dirname(__file__)+"/database/data/{}".format(filename), "r") as f:
        entities = [w.strip() for w in f if not w.startswith("#")]
    return {w: 1 for w in entities}

stop_words = read_data("stoplist-nl.txt")  # stop words to filter out in word cloud
obscene_words = read_data("obscene_words.txt")
blocked_users = read_data("blocked_users.txt")
blacklist = read_data("blacklist.txt")
