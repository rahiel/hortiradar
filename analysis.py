from collections import Counter
from datetime import datetime

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from main import get_db


db = get_db()

# gets all tweets with any keywords
tweets_with_keywords = db.tweets.find({"num_keywords": {"$gt": 0}})


def plot_keyword_frequency(keyword):
    tweets = db.tweets.find({"keywords": [keyword]})
    tweets = list(tweets)

    df = pd.DataFrame([t["tweet"] for t in tweets])
    df["num_keywords"] = [t["num_keywords"] for t in tweets]
    df["keywords"] = [t["keywords"] for t in tweets]

    df["datetime"] = pd.to_datetime(df["created_at"])
    df_datetime = pd.DatetimeIndex(df["datetime"])
    df["month"] = df_datetime.month
    df["day"] = df_datetime.day
    df["day_of_year"] = df_datetime.dayofyear

    dates = zip(df_datetime.month, df_datetime.day)
    counts = sorted(Counter(dates).items(), key=lambda x: x[0])
    days, number = zip(*counts)

    labels = [datetime(2016, m, d).strftime("%d %b") for m, d in days]
    sns.barplot(labels, number)
    plt.show()


plot_keyword_frequency("bloemen")
