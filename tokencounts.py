import os, datetime, calendar, json

class tokenCounts:
	def __init__(self,keywords,min_interval):
		self.keywords = keywords
		self.keywordCounts = {}
		self.subCounts = {}
		self.resultsdict = {}
		self.last_output = datetime.datetime.utcnow()
		self.output_interval = 60*min_interval # output interval in seconds
		self.output = "results/"
		if not os.path.exists(os.path.dirname(os.path.abspath('__file__'))+"/results"):
			os.makedirs(os.path.dirname(os.path.abspath('__file__'))+"/results")

	def update(self,tokens,timestamp):
		self.resultsdict[timestamp] = tokens

	def setInitialScores(self):
		for word in self.keywords:
			self.keywordCounts[word] = 0
			self.subCounts[word] = {}

	def calcScore(self):
		self.setInitialScores()
		for entry in self.resultsdict:
			toUpdate = union(self.keywords,self.resultsdict[entry])
			for word in toUpdate:
				try:
					self.keywordCounts[word] += 1
					for t in self.resultsdict[entry]:
						if t != word and t.strip('#') != word:
							if t in self.subCounts[word]:
								self.subCounts[word][t] += 1
							else:
								self.subCounts[word][t] = 1
				except KeyError:
					pass

	def removeOldEntries(self):
		to_delete = []
		cur_ts = calendar.timegm(datetime.datetime.utcnow().timetuple())
		for entry in self.resultsdict:
			if cur_ts-entry > self.output_interval:
				to_delete.append(entry)

		temp_dict = {}
		for key in self.resultsdict:
			if key not in to_delete:
				temp_dict[key] = self.resultsdict[key]
		self.resultsdict = temp_dict

	def makeOutput(self):
		# output results to json file

		self.calcScore()

		self.last_output = datetime.datetime.utcnow()
		with open(self.output + self.last_output.strftime("%Y-%m-%d.%H.%M.00") + ".json", "w") as doc:
				doc.write(json.dumps({"counts": self.keywordCounts, "subcounts": self.subCounts}))

		self.removeOldEntries()

	def union(keywords, tokens):
    """ return the union of two lists """
    union = []
    for t in tokens:
    	if t in keywords:
    		union.append(t)
    	elif t.strip('#') in keywords:
    		union.append(t.strip('#'))
    return union

