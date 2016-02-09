#!/usr/bin/python

from __future__ import division
from datetime import datetime, timedelta
import gzip
import json
from operator import itemgetter

from dateutil.relativedelta import relativedelta
from twokenize import tokenizeRawTweetText

global bloemen_keys
with open("keywords_bloemen_top10app.txt") as doc:
	bloemen_keys = unicode(doc.read()).lower().split(',')

global groentefruit_keys
with open("keywords_groentefruit_top10app.txt") as doc:
	groentefruit_keys = unicode(doc.read()).lower().split(',')

def process_hour(dt_obj,key_counts,location="d1"):
	if location == "d1":
		filename = "/home/pkampst/archive/%(year)i%(month)02i/%(year)i%(month)02i%(day)02i_%(hour)02i.out.gz" % {"year": dt_obj.year, "month": dt_obj.month, "day": dt_obj.day, "hour": dt_obj.hour}
	elif location == "local":
		filename = "F:/Promotie/tweets/%(year)i%(month)02i/%(year)i%(month)02i%(day)02i_%(hour)02i.out.gz" % {"year": dt_obj.year, "month": dt_obj.month, "day": dt_obj.day, "hour": dt_obj.hour}
	try:
		with gzip.open(filename,'rb') as doc:
			for line in doc:
				if line[0] in ['0','3']:
					try:
						tweet = json.loads(line[1:])
						try:
							if tweet['lang'] == 'nl':
								text = tweet['text'].replace('\n',' ')
								tokens = tokenizeRawTweetText(tweet['text'])
								for token in tokens:
									if token in bloemen_keys:
										if token in key_counts["bloemen"]:
											key_counts["bloemen"][token] += 1
										else:
											key_counts["bloemen"][token] = 1
									elif token in groentefruit_keys:
										if token in key_counts["groentefruit"]:
											key_counts["groentefruit"][token] += 1
										else:
											key_counts["groentefruit"][token] = 1
						except KeyError:
							pass
					except (ValueError, TypeError) as e:
						pass
	except IOError:
		pass

	return key_counts

def get_quarter_counts(start,location="d1",numberOfMonths=3):
	current = datetime(year=start.year,month=start.month,day=start.day,hour=start.hour,second=start.second)
	end = start+relativedelta(months=numberOfMonths)
	key_counts = {"bloemen": {}, "groentefruit": {}}

	while current < end:
		key_counts = process_hour(current,key_counts,location)
		print "Just processed time:", current.strftime("%Y-%m-%d %H:%M:%S")
		current += timedelta(hours=1)

	totals = {"bloemen": sum(key_counts["bloemen"].itervalues()), "groentefruit": sum(key_counts["groentefruit"].itervalues())}
	sorted_counts = {"bloemen": sorted(key_counts["bloemen"].items(), key=itemgetter(1)), "groentefruit": sorted(key_counts["groentefruit"].items(), key=itemgetter(1))}

	filename = "_"+start.strftime("%Y_%b")+"-"+end.strftime("%b")+".txt"
	for key in key_counts:
		with open("../"+key+filename,'wb') as doc:
			for entry in sorted_counts[key]:
				percentage = "%.02f" % (entry[1]/totals[key])
				doc.write(entry[0]+"\t"+str(entry[1]) + "\t" + percentage + "\n")


# get_quarter_counts(datetime(2015,7,1,0),location="local")
# get_quarter_counts(datetime(2015,9,1,0),location="local",numberOfMonths=2)
get_quarter_counts(datetime(2014,10,1,0))