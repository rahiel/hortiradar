from datetime import datetime, timedelta
import json

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import squarify
import wikipedia
from scipy.interpolate import interp1d
from statsmodels.tsa.seasonal import seasonal_decompose

from hortiradar import Tweety, TOKEN
from hortiradar.database import get_db, get_keywords, stop_words
from hortiradar.clustering.util import round_time

mpl.use('Agg')
mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = [r'\usepackage{amsmath,amssymb,amsthm,bbm}']
wikipedia.set_lang("nl")

time_format = "%Y-%m-%d-%H-%M-%S"

tweety = Tweety("https://acba.labs.vu.nl/hortiradar/api/", TOKEN)
db = get_db()
groups = [g["name"] for g in db.groups.find({}, projection={"name": True, "_id": False})]
keywords = get_keywords(local=True)

num_colors = 10
cm = plt.get_cmap('tab10')
cNorm = mpl.colors.Normalize(vmin=0, vmax=num_colors-1)
scalarMap = mpl.cm.ScalarMappable(norm=cNorm, cmap=cm)
tab10 = [scalarMap.to_rgba(i) for i in range(num_colors)]

num_colors2 = 20
cm2 = plt.get_cmap('tab20')
cNorm2 = mpl.colors.Normalize(vmin=0, vmax=num_colors2-1)
scalarMap2 = mpl.cm.ScalarMappable(norm=cNorm2, cmap=cm2)
tab20 = [scalarMap2.to_rgba(i) for i in range(num_colors2)]


def rescale_time(values):
    # switch from t to t*
    x = range(25)
    y = [0]+[i/sum(values)*24 for i in np.cumsum(values).tolist()]

    xtick = interp1d(y, x)(range(25))
    return xtick.tolist()


def rescale_to_normal(xtick):
    # from t* back to t
    xtick_back = rescale_time(np.diff(xtick))
    return xtick_back


class Redistributor:
    def __init__(self, cycle=[]):
        self.cycle = cycle
        self.xtick = []
        self.xtick_back = []

    def set_xtick(self):
        if np.any(self.cycle):
            ticks = rescale_time(self.cycle)
            self.xtick = ticks[1:]
            ticks_back = rescale_to_normal(ticks)
            self.xtick_back = ticks_back[1:]
        else:
            raise(AttributeError("Attribute cycle is not defined."))

    def redistribute(self, views, rtype="to_red_time"):
        if rtype == "to_red_time":
            ticks = self.xtick
        elif rtype == "from_red_time":
            ticks = self.xtick_back
        else:
            raise(NotImplementedError)

        xdata = [0]+ticks
        ydata = [0]+np.cumsum(views).tolist()

        ynew = interp1d(range(len(ydata)), ydata, bounds_error=False, fill_value=np.nan)(xdata)

        red_data = np.diff(ynew).tolist()

        return red_data


def get_wordcloud(kw, s):
    jstr = tweety.get_keyword_wordcloud(kw, start=datetime.strftime(s-timedelta(hours=1), time_format), end=datetime.strftime(s, time_format)).decode("utf-8")
    terms = json.loads(jstr)
    for term in terms:
        try:
            page = wikipedia.page(term["word"])
            term["summary"] = page.summary
        except Exception:
            term["summary"] = ""
    return terms


def get_ts(kw, s, e):
    jstr = tweety.get_keyword_series(kw, step=3600, start=datetime.strftime(s, time_format), end=datetime.strftime(e, time_format)).decode("utf-8")
    if "Internal Server Error" not in jstr:
        res = json.loads(jstr)
        nh = num_hours(datetime.strptime(res["end"], time_format)-datetime.strptime(res["start"], time_format))
        ts = np.transpose([res["series"][str(k)] if str(k) in res["series"] else 0 for k in range(nh)])
        ans_s = datetime.strptime(res["start"], time_format)
        ans_e = datetime.strptime(res["end"], time_format)
        if ans_s != s:
            ts = np.append(np.ones(num_hours(ans_s-s)), ts)
        if ans_e != e:
            ts = np.append(ts, np.ones(num_hours(e-ans_e)))
    else:
        ts = []
    return ts


def num_hours(td):
    return 24*td.days + td.seconds//3600


def check_for_peak(kw, now, begin):
    s = round_time(begin, "day")
    e = round_time(now, "day", rounding="ceil")

    df = pd.DataFrame()
    df["hours"] = [s + timedelta(hours=x) for x in range(num_hours(e-s))]
    df.set_index("hours", inplace=True)

    timeseries = get_ts(kw, s, now)
    if timeseries != []:
        missing_hours = num_hours(e-s) - len(timeseries)
        df[kw] = np.append(timeseries, [np.nan] * missing_hours)

        decomposition = seasonal_decompose(df.loc[:now-timedelta(hours=1)])
        season = decomposition.seasonal.loc[s:e, :].values[:24]
        cycle = (season - np.min(season)) / sum(season - np.min(season))
        red = Redistributor(cycle=cycle.reshape(-1))
        red.set_xtick()

        yvals = np.nanmean(df[kw].values)*np.ones(25)
        yvals_std = yvals + 2 * np.nanstd(df[kw].values)*np.ones(25)

        yvals_circ = red.redistribute(yvals, "from_red_time")
        yvals_circ_std = red.redistribute(yvals_std, "from_red_time")

        circ_long = yvals_circ * (e-s).days
        df["{kw}_circ".format(kw=kw)] = circ_long

        circ_std_long = yvals_circ_std * (e-s).days
        df["{kw}_circ_std".format(kw=kw)] = circ_std_long

        peak = yvals_circ_std[now.hour-1] < df[kw].loc[now-timedelta(hours=1)] and yvals_circ_std[now.hour-1] > np.maximum(3.0, np.nanmean(df[kw].values))
        difference = (df[kw] - df["{kw}_circ".format(kw=kw)]).loc[now-timedelta(hours=1)]

        return df, peak, difference
    else:
        return None, None, None


def plot_peak_data(df, kws, begin, now, group):
    s = round_time(begin, "day")
    e = round_time(now, "day", rounding="ceil")

    modval = 20
    colors = tab20

    fig, axarr = plt.subplots(len(kws), 1, figsize=(11.7, 8.3))

    for i, kw in enumerate(kws):
        ax = axarr[i]
        col = colors[2*i % modval]
        col2 = colors[2*i % modval + 1]
        ax.plot(df.index, df[kw].values, lw=3, color=col, label="Hortiradar: {kw}".format(kw=kw))
        # ax.plot(df["{kw}_circ".format(kw=kw)].loc[now-timedelta(hours=1):], lw=3, color=col, linestyle="dashed")
        ax.plot(df["{kw}_circ".format(kw=kw)].loc[:], lw=3, color=col2, linestyle="dashed", label="Average daily cycle")
        ax.plot(df["{kw}_circ_std".format(kw=kw)].loc[now-timedelta(hours=1):], lw=1, color='k', linestyle="dashed", label="Threshold line")
        ax.plot(now-timedelta(hours=1), df[kw].loc[now-timedelta(hours=1)], "o", color=col, ms=10)

        ylims = ax.get_ylim()
        ax.vlines(now-timedelta(hours=1), *ylims, lw=3, color="0.6", linestyle="dashed")
        ax.set_xlim(s, e)
        ax.set_ylim(*ylims)

        ax.legend()
    # fig.savefig("{g}_{dt}h.pdf".format(g=group, dt=datetime.strftime(now, "%Y_%m_%d_%H")), dpi=600, orientation="landscape", papertype="a4")


def main():
    now = round_time(datetime.utcnow())
    begin = now - timedelta(hours=7*24)

    s = round_time(begin, "day")
    e = round_time(now, "day", rounding="ceil")

    dfs = {}
    differences = {}
    peaks = {}
    for g in groups:
        dfs[g] = pd.DataFrame()
        peaks[g] = []
        dfs[g]["hours"] = [s + timedelta(hours=x) for x in range(num_hours(e-s))]
        dfs[g].set_index("hours", inplace=True)

    for kw in keywords:
        try:
            df_kw, peak, diff = check_for_peak(kw, now, begin)
            differences[kw] = diff
            for gr in keywords[kw].groups:
                dfs[g] = pd.concat([dfs[g], df_kw], axis=1)
        except json.JSONDecodeError:
            pass

    for g in groups:
        plot_peak_data(dfs[g], peaks[g], begin, now, g)


if __name__ == '__main__':
    main()
