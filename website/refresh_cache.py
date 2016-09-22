# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from app import cache, process_top, process_details, round_time, API_time_format


groups = [u"bloemen", u"groente_en_fruit"]


# bigger than usual time for when the hourly recache is too slow
cache_time = 90 * 60


max_amount = 10
group_data = []
for group in groups:
    print("Caching group: {}".format(group))
    group_data.append(cache(process_top, group, max_amount, force_refresh=True, cache_time=cache_time))


end = round_time(datetime.utcnow())
interval = 60 * 60 * 24 * 7
start = end + timedelta(seconds=-interval)
params = {"start": start.strftime(API_time_format), "end": end.strftime(API_time_format)}
keyword_data = []
for group in group_data:
    for keyword in group:
        prod = keyword["label"]
        print("Caching keyword: {}".format(prod))
        keyword_data.append(cache(process_details, prod, params, force_refresh=True, cache_time=cache_time))
