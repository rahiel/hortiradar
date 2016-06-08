#!/usr/bin/python
from os import makedirs
from os.path import abspath, dirname, exists
from datetime import datetime
from calendar import timegm
from json import dumps

from util import union


class tokenCounts:
    """Counts the frequency in which keywords occur and stores the tokens with which they occur

    Example (after processing "Ik eet een banaan"):
    keywordCounts: {"banaan": 1}
    subCounts: {"banaan": {"Ik": 1, "eet": 1, "een": 1}}
    """

    def __init__(self, keywords, min_interval=60, outputLocation="results/"):
        """
        Parameters
        keywords:       array of keywords that should be counted
        min_interval:   output interval in minutes

        Variables
        keywords:		array of keywords that are counted
        keywordCounts:	dictionary with frequency of occurrance per keyword
        subCounts:		dictionary with frequency of co-occuring tokens per keyword
        resultsdict:	dictionary of token arrays that attribute to counts
        last_output:	last time when the scores where written to a file
        output:			folder to which the scores are written (is created if it is not present)
        """
        self.keywords = keywords
        self.keywordCounts = {}
        self.subCounts = {}
        self.resultsdict = {}
        self.last_output = datetime.utcnow()
        self.output_interval = 60 * min_interval  # output interval in seconds
        self.output = outputLocation
        if not exists(dirname(abspath('__file__')) + self.output):
            makedirs(dirname(abspath('__file__')) + self.output)

    def update(self, tokens, timestamp):
        """Adds tweet tokens to resultsdict using timestamp of tweet"""
        self.resultsdict[timestamp] = tokens

    def setInitialScores(self):
        """Initiates the scores for each keyword and makes subcount dictionaries"""
        for word in self.keywords:
            self.keywordCounts[word] = 0
            self.subCounts[word] = {}

    def calcScore(self):
        """Calculate scores and subcounts per keyword"""
        # initialize scores
        self.setInitialScores()

        for entry in self.resultsdict:

            # Determine which keywords are mentioned in tweet
            toUpdate = union(self.keywords, self.resultsdict[entry])

            for word in toUpdate:
                self.keywordCounts[word] += 1
                for t in self.resultsdict[entry]:
                    if t != word and t.strip('#') != word:
                        if t in self.subCounts[word]:
                            self.subCounts[word][t] += 1
                        else:
                            self.subCounts[word][t] = 1

    def removeOldTweets(self):
        """Removes all entries that are older than the desired interval from resultsdict"""
        cur_ts = timegm(datetime.utcnow().timetuple())
        for key in list(self.resultsdict.keys()):
            if cur_ts - key > self.output_interval:
                del self.resultsdict[key]

    def makeOutput(self):
        """Write results to file after calculating scores"""

        self.removeOldTweets()
        self.calcScore()

        self.last_output = datetime.utcnow()
        with open(self.output + self.last_output.strftime("%Y-%m-%d.%H.%M.00") + ".json", "w") as doc:
            doc.write(dumps({"counts": self.keywordCounts, "subcounts": self.subCounts}))
