from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import ujson as json
import wikipedia
from redis import StrictRedis
from scipy.interpolate import interp1d
from statsmodels.tsa.seasonal import seasonal_decompose

from hortiradar import TOKEN, Tweety, time_format
from hortiradar.database import get_keywords
from hortiradar.clustering.util import round_time


wikipedia.set_lang("nl")
tweety = Tweety("http://127.0.0.1:8888", TOKEN)
keywords = get_keywords(local=True)
redis = StrictRedis()


def rescale_time(values):
    # switch from t to t*
    x = range(25)
    y = [0] + [i/sum(values)*24 for i in np.cumsum(values).tolist()]

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

        xdata = [0] + ticks
        ydata = [0] + np.cumsum(views).tolist()

        ynew = interp1d(range(len(ydata)), ydata, bounds_error=False, fill_value=np.nan)(xdata)

        red_data = np.diff(ynew).tolist()

        return red_data


def get_wordcloud(kw, s):
    jstr = tweety.get_keyword_wordcloud(kw, start=datetime.strftime(s-timedelta(hours=1), time_format), end=datetime.strftime(s, time_format)).decode("utf-8")
    tokens = json.loads(jstr)
    terms = []
    for token in tokens:
        term = {"size": token["count"], "name": token["word"]}
        try:
            page = wikipedia.page(token["word"])
            term["summary"] = page.summary
        except Exception:
            term["summary"] = ""

        terms.append(term)
    return terms


def get_ts(kw, s, e):
    jstr = tweety.get_keyword_series(kw, step=3600, start=datetime.strftime(s, time_format), end=datetime.strftime(e, time_format)).decode("utf-8")
    if "Internal Server Error" not in jstr:
        res = json.loads(jstr)
        nh = num_hours(datetime.strptime(res["end"], time_format) - datetime.strptime(res["start"], time_format))
        ts = np.transpose([res["series"][str(k)] if str(k) in res["series"] else 0 for k in range(nh)])
        ans_s = datetime.strptime(res["start"], time_format)
        ans_e = datetime.strptime(res["end"], time_format)
        if ans_s != s:
            ts = np.append(np.ones(num_hours(ans_s - s)), ts)
        if ans_e != e:
            ts = np.append(ts, np.ones(num_hours(e - ans_e)))
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

        return df, peak
    else:
        return None, None


def output_ts(pdseries):
    ts = []
    for pdts, tw in pdseries.dropna().iteritems():
        dt = pdts.to_pydatetime()
        md = {"hour": dt.hour, "day": dt.day, "year": dt.year, "month": dt.month, "count": tw}

        ts.append(md)
    return ts


def output_peaks(peaks, peak_df, terms):
    peaks_json = []
    for peak in peaks:
        print(peak)
        peak_dict = {}
        peak_dict["threshold"] = output_ts(peak_df[peak+"_circ_std"])
        peak_dict["actual"] = output_ts(peak_df[peak])
        peak_dict["circadian"] = output_ts(peak_df[peak+"_circ"])
        peak_dict["treemap"] = {"name": peak, "children": terms[peak]}
        peaks_json.append([peak, peak_dict])
    return peaks_json


def main():
    end = round_time(datetime.utcnow())
    start = end - timedelta(hours=7*24)

    s = round_time(start, "day")
    e = round_time(end, "day", rounding="ceil")

    peak_df = pd.DataFrame()
    peak_df["hours"] = [s + timedelta(hours=x) for x in range(num_hours(e-s))]
    peak_df.set_index("hours", inplace=True)
    peaks = []
    terms = {}

    for kw in keywords:
        try:
            df_kw, peak = check_for_peak(kw, end, start)
            if peak:
                peaks.append(kw)
                peak_df = pd.concat([peak_df, df_kw], axis=1)
                terms[kw] = get_wordcloud(kw, end)
        except json.JSONDecodeError:
            pass

    if peaks:
        peaks_json = output_peaks(peaks, peak_df, terms)
    else:
        peaks_json = []

    jdict = json.dumps(peaks_json)
    cache_time = 60 * 60 * 2
    redis.set("anomalies", jdict, ex=cache_time)
    redis.set("anomalies_start", json.dumps(start.strftime(time_format)), ex=cache_time)
    redis.set("anomalies_end", json.dumps(end.strftime(time_format)), ex=cache_time)


if __name__ == "__main__":
    main()
