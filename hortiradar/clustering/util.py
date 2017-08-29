import calendar
from collections import Counter
from math import sqrt

def round_time(dt,interval="hour"):
    if interval == "hour":
        dt = dt.replace(minute=0,second=0,microsecond=0)
    elif interval == "minute":
        dt = dt.replace(second=0,microsecond=0)
    elif interval == "day":
        dt = dt.replace(hour=0,minute=0,second=0,microsecond=0)
    return dt

def dt_to_ts(dt):
    return calendar.timegm(dt.timetuple())

def jac(a,b):
    """ return the Jaccard similarity of two sets"""
    try:
        frac = len(a & b) / len(a | b)
    except ZeroDivisionError:
        frac = 0
    return frac

def cos_sim(a,b):
    """ Return the cosine similarity of sets a and b: (a dot b)/(||a||*||b||)"""
    try:
        frac = len(a & b) / sqrt( len(a) * len(b) )
    except ZeroDivisionError:
        frac = 0
    return frac