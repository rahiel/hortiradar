#!/usr/bin/python

def union(keywords, tokens):
	""" return the union of two lists """
	union = []
	for t in tokens:
		if t in keywords:
			union.append(t)
		elif t.strip('#') in keywords:
			union.append(t.strip('#'))
	return union