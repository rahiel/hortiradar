from os.path import expanduser

import attr
import frog
import pymongo


DATABASE = None
FROG = None
GROUPS = {
    "bloemen": "data/flowers.txt",
    "groente_en_fruit": "data/fruitsandveg.txt"
}


@attr.s(slots=True)
class Keyword(object):
    lemma = attr.ib()
    pos = attr.ib()
    groups = attr.ib(default=attr.Factory(list))


def get_keywords():
    """Gets keywords from the source files. Returns a dictionary where the keys are
    the lemma's of the keywords and the values the Keyword objects.
    """
    keywords = {}
    for group_name in GROUPS:
        words = read_keywords(GROUPS[group_name])
        for k in words:
            if k.lemma in keywords:
                keywords[k.lemma].groups.append(group_name)
            else:
                k.groups.append(group_name)
                keywords[k.lemma] = k
    return keywords


def read_keywords(filename):
    """Returns a list of Keyword objects from the datafile."""
    keywords = []
    lemmas = []
    frog = get_frog()
    with open(filename) as f:
        for line in f:
            word, pos = line.strip().split(",")
            word = word.lower()
            if word[0] == '#':
                word = word[1:]
            tokens = frog.process(word)
            if len(tokens) == 1:  # TODO: we skip over multi-word keywords
                lemma = tokens[0]["lemma"]
                if lemma not in lemmas:  # we only want unique lemma's
                    k = Keyword(lemma=lemma, pos=pos)
                    keywords.append(k)
                    lemmas.append(lemma)
    return keywords


def get_frog():
    """Returns the interface object to frog NLP. (There should only be one
    instance, because it spawns a frog process that consumes a lot of RAM.)
    """
    global FROG
    if FROG is None:
        FROG = frog.Frog(frog.FrogOptions(
            tok=True, lemma=True, morph=False, daringmorph=False, mwu=True,
            chunking=False, ner=False, parser=False
        ), expanduser("~/hortiradar/venv/share/frog/nld/frog.cfg"))
    return FROG


def get_db():
    """Returns the twitter database."""
    global DATABASE
    if DATABASE is None:
        mongo = pymongo.MongoClient(connect=False)
        # connect=False: http://api.mongodb.com/python/current/faq.html#is-pymongo-fork-safe
        DATABASE = mongo.twitter
    return DATABASE
