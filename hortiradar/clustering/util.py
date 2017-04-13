from math import sqrt

def get_time_passed(start,end,unit="hour"):
    if unit == "hour":
        return (end-start).seconds / (60*60)
    elif unit == "minute":
        return (end-start).seconds / 60
    elif unit == "day":
        return (end-start).seconds / (24*60*60)

def round_time(dt,interval="hour"):
    if interval == "hour":
        dt = dt.replace(minute=0,second=0,microsecond=0)
    elif interval == "minute":
        dt = dt.replace(second=0,microsecond=0)
    elif interval == "day":
        dt = dt.replace(hour=0,minute=0,second=0,microsecond=0)
    return dt

def jac(a,b):
    """ return the Jaccard similarity of two sets"""
    try:
        frac = len(a & b) / len(a | b)
    except ZeroDivisionError:
        frac = 0
    return frac

def cos_sim(a,b):
    """ Return the cosine similarity of token counters a and b: (a dot b)/{||a||*||b||)"""
    dotproduct, aSq, bSq = 0, 0, 0
    for token in a:
        if token in b:
            dotproduct += a[token] * b[token]
            aSq += a[token] ** 2
    
    for token in b:
        bSq += b[token] ** 2
    
    return dotproduct/sqrt(aSq*bSq)