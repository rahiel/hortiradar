from selderij import app
from keywords import get_keywords, get_frog
from tasks_master import insert_tweet


keywords = get_keywords()


# task for worker nodes
@app.task
def find_keywords_and_groups(id_str, text):     # TODO: cache retweets
    """Returns a list of the keywords and a list of associated groups that occur in tokens."""
    frog = get_frog()
    tokens = frog.process(text)  # a list of dictionaries with frog's analysis per token
    kw = []
    groups = []
    for t in tokens:
        lemma = t["lemma"].lower()
        k = keywords.get(lemma, None)
        if k is not None:
            if t["posprob"] > 0.6:
                if not t["pos"].startswith(k.pos + "("):
                    continue
            kw.append(lemma)
            groups += k.groups
    insert_tweet.apply_async((id_str, list(set(kw)), list(set(groups))), queue="master")
