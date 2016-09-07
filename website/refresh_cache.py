# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from app import cache, process_top_fruits, process_details, round_time, API_time_format


groups = ["bloemen", "groente_en_fruit"]


max_amount = 10
group_data = []
for group in groups:
    group_data.append(cache(process_top_fruits, group, max_amount, force_refresh=True))


end = round_time(datetime.utcnow())
interval = 60 * 60 * 24 * 7
start = end + timedelta(seconds=-interval)
params = params = {"start": start.strftime(API_time_format), "end": end.strftime(API_time_format)}
keyword_data = []
for group in group_data:
    for keyword in group:
        prod = keyword["label"]
        keyword_data.append(cache(process_details, prod, params, force_refresh=True))
