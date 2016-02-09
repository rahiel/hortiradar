#!/usr/bin/python
import json

import plotter

with open('results/2015-11-02.20.39.00.json') as doc:
	for line in doc:
		d = json.loads(line)

i=0
top10_plot = {"x": [], "y": [], "labels": []}
for k in sorted(d['counts'], key=lambda k: d['counts'][k], reverse=True):
	if i<10:
		# plotter.plot_wordcloud(d['subcounts'][k],{"filename": "wc_top10_"+k,"title": ""})
		top10_plot["x"].append(len(top10_plot["x"]))
		top10_plot["y"].append(d["counts"][k])
		top10_plot["labels"].append(k)
	i+=1

top10_axis = {"filename": "top10_bar", "xticks": [x+0.4 for x in top10_plot["x"]]}
plotter.plot_top10(top10_plot,top10_axis)