import argparse
from datetime import datetime

import flask
import ujson as json

from app import app, get_period
from hortiradar import time_format
from processing import get_cache_key, get_process_top_params, process_details, process_top, redis


def main():
    parser = argparse.ArgumentParser(description="Refresh the cache for hortiradar analytics.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    # bigger than usual time for when the hourly recache is too slow
    cache_time = 120 * 60

    groups = ["bloemen", "groente_en_fruit"]
    get_time = lambda: datetime.now().strftime("%H:%M")

    start_time = get_time()
    max_amount = 10
    group_data = []
    for group in groups:
        if args.verbose:
            print("Caching group: {}".format(group))
        arguments = (group, max_amount, get_process_top_params(group))
        key = get_cache_key(process_top, *arguments)
        data = process_top(*arguments, force_refresh=True, cache_time=cache_time)
        group_data.append((key, data))

    with app.test_request_context("/?period=week"):
        _, start, end, _ = get_period(flask.request, "week")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = []
    for (_, group) in group_data:
        for keyword in group:
            prod = keyword["label"]
            if args.verbose:
                print("Caching keyword: {}".format(prod))
            key = get_cache_key(process_details, prod, params)
            data = process_details(prod, params, force_refresh=True, cache_time=cache_time)
            keyword_data.append((key, data))
    end_time = get_time()

    # Now populate the cache with the new data
    for (key, data) in group_data + keyword_data:
        redis.set(key, json.dumps(data), ex=cache_time)

    sync_time = "{} - {}".format(start_time, end_time) if start_time != end_time else start_time
    redis.set("sync_time", sync_time)


if __name__ == "__main__":
    main()
