from os.path import expanduser

import attr
import frog
import pymongo
import ujson as json


from hortiradar import Tweety, TOKEN


DATABASE = None
FROG = None
GROUPS = {
    "bloemen": "data/flowers.txt",
    "groente_en_fruit": "data/fruitsandveg.txt"
}


@attr.s(slots=True)
class Keyword:
    lemma = attr.ib()
    pos = attr.ib()
    groups = attr.ib(default=attr.Factory(list))


def get_keywords(local=False):
    """Gets keywords from the `groups` collection in MongoDB. Returns a dictionary
    where the keys are the lemma's of the keywords and the values the Keyword
    objects.

    Set `local` to `True` if running on the same server as the database.
    """
    keywords = {}
    for group_name in GROUPS:
        words = request_keywords(group_name, local)
        for k in words:
            if k.lemma in keywords:
                keywords[k.lemma].groups.append(group_name)
            else:
                k.groups.append(group_name)
                keywords[k.lemma] = k
    return keywords


def request_keywords(group, local=False):
    """Returns a list of Keyword objects from the keywords in the group."""
    if local:
        mongo = pymongo.MongoClient()
        db = mongo.twitter
        g = db.groups.find_one({"name": group})["keywords"]
    else:
        tweety = Tweety("https://acba.labs.vu.nl/hortiradar/api/", TOKEN)
        g = json.loads(tweety.get_group(group))
    keywords = []
    for keyword in g:
        k = Keyword(lemma=keyword["lemma"], pos=keyword["pos"])
        keywords.append(k)
    return keywords


def read_keywords(filename):
    """Returns a list of Keyword objects from the datafile. Assumes keywords in
    filename are lemmatised, lowercase (but capitalized for names, according to
    the pos) and unique.
    """
    keywords = []
    with open(filename) as f:
        for line in f:
            lemma, pos = line.strip().split(",")
            k = Keyword(lemma=lemma, pos=pos)
            keywords.append(k)
    return keywords


def clean_wordlist(filename):
    frog = get_frog()
    keywords = []

    with open("data/{}".format(filename)) as f:
        for line in f:
            word, pos = line.strip().split(",")
            if not pos.startswith("SPEC"):
                word = word.lower()
            if word[0] == "#":
                word = word[1:]
            tokens = frog.process(word)
            if len(tokens) > 1:  # TODO: we skip over multi-word keywords
                lemma = word
            else:
                lemma = tokens[0]["lemma"]
            keywords.append((lemma, pos))

    keywords = sorted(set(keywords))

    with open("data/new_{}".format(filename), "w") as f:
        for (word, pos) in keywords:
            f.write("{},{}\n".format(word, pos))


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
