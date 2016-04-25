#!/usr/bin/python
from datetime import datetime
from calendar import timegm
from Queue import Queue
from threading import Thread, Lock
from ConfigParser import ConfigParser

from tweepy import StreamListener, OAuthHandler, API, Stream
from tweepy.parsers import RawParser
from twokenize import tokenizeRawTweetText

from tokencounts import tokenCounts
from streamer import Top10Streamer

class listenerThread(Thread):
	"""Thread that is used to receive tweets through Twitter API"""

	def __init__(self, name, queue, conf, track):
		"""
		Parameters
		name:	name of the thread
		queue:	queue of tweets that need to be processed
		conf:	location of config file for Twitter API authentication
		track:	keywords that are used to filter twitter messages
		"""
		Thread.__init__(self)
		self.name = name
		self.q = queue
		self.configLocation = conf
		self.keywords = track

	def run(self):
		"""Initiates the streaming process"""
		print "Starting " + self.name
		self.start_streaming()
		print "Exiting " + self.name

	def start_streaming(self):
		"""Initiates the streaming of tweets fetching all tweets that contain one of the given keywords"""
		
		## Load API config data
		Twitdata = ConfigParser()
		Twitdata.read(self.configLocation)

		## initialize connection with Twitter API
		auth = OAuthHandler(Twitdata.get('Tweepy','consumer_key'), Twitdata.get('Tweepy','consumer_secret'))
		auth.set_access_token(Twitdata.get('Tweepy','access_key'), Twitdata.get('Tweepy','access_secret'))
		api = API(auth)

		## set up Streamer
		listen = Top10Streamer(self.q,api)
		stream = Stream(auth, listen)
		print "Streaming started at " + datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")
		while True:
			try:
				stream.filter(track = self.keywords)
			except:
				print "Streaming disconnected at " + datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")
				stream.disconnect()

		print "Streaming stopped at " + datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")

class workerThread(Thread):
	"""Thread that processes the tweets to count occurences of keywords"""
	
	def __init__(self,threadID,name):
		"""
		Parameters
		threadID: 	id of thread
		name: 		name of thread
		"""
		Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		
	def run(self):
		"""Initiates the processing"""
		print "Starting " + self.name
		self.process_tweets()
		print "Exiting " + self.name

	def process_tweets(self):
		"""Handles the processing of tweets"""
		while not __exitFlag:
			__queueLock.acquire()
			if not __tweetQueue.empty():
				tweet = __tweetQueue.get()
				__queueLock.release()
				
				# tokenize tweet.text
				tokens = tokenizeRawTweetText(tweet.text)
				
				# update counts
				__countsLock.acquire()
				__tCounts.update(tokens,timegm(tweet.created_at.timetuple()))
				interval = timegm(datetime.utcnow().timetuple())-timegm(__tCounts.last_output.timetuple())
				if interval > __tCounts.output_interval:
					__tCounts.makeOutput()
				__countsLock.release()
			else:
				__queueLock.release()


def main():
	"""Starts streaming and processing threads and initiates tokencounter"""
	threadList = ["Worker-1", "Worker-2", "Worker-3"]
	threads = []

	Param = ConfigParser()
	Param.read('data/parameters.ini')
 	
 	global __exitFlag
	global __tweetQueue
	global __queueLock
	global __countsLock
	global __tCounts

	with open("data/keywords_groentefruit_top10app.txt") as doc:
		keywords = unicode(doc.read()).lower().split(',')
	
	__exitFlag = 0
	__tweetQueue = Queue(100000)
	__queueLock = Lock()
	__countsLock = Lock()
	__tCounts = tokenCounts(keywords,Param.getint('Parameters','min_interval'))

	try:
		# Create listener thread
		thread = listenerThread("Listener",queue=__tweetQueue,conf="data/twitdata.ini",track=keywords)
		thread.start()
		threads.append(thread)

		# Create worker threads
		threadID = 2
		for tName in threadList:
			thread = workerThread(threadID, tName)
			thread.start()
			threads.append(thread)
			threadID += 1
	except:
		__exitFlag = 1
		for t in threads:
			t.join()
			print "Exiting Main Thread"


if __name__ == '__main__': main()	