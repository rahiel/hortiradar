from datetime import datetime

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def round_time(dt, interval="hour"):
    if interval == "hour":
        dt = dt.replace(minute=0, second=0, microsecond=0)
    elif interval == "minute":
        dt = dt.replace(second=0, microsecond=0)
    elif interval == "day":
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return dt


def dt_to_ts(dt):
    # use POSIX epoch
    diff = dt - datetime(1970, 1, 1)
    return diff.total_seconds()


def get_token_array(tokens, filt_tokens):
    return [tokens[t] for t in filt_tokens]


def jac(a, b):
    """ return the Jaccard similarity of two sets"""
    if type(a) != set:
        a = set(a)
    if type(b) != set:
        b = set(b)

    n = len(a.intersection(b))
    return n / float(len(a) + len(b) - n)


def cos_sim(a, b):
    if type(a) == list:
        if a:
            a = np.asarray(a).reshape(1, -1)
        else:
            return 0.0
    if type(b) == list:
        if b:
            b = np.asarray(b).reshape(1, -1)
        else:
            return 0.0

    return cosine_similarity(a, b)[0][0]
