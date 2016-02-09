#!/usr/bin/python
from tokencounts import tokenCounts
from tweepy import StreamListener
from tweepy.parsers import RawParser
from twokenize import tokenizeRawTweetText
import json, time, tweepy, sys, datetime, calendar, os, Queue, threading, ConfigParser

Param = ConfigParser.ConfigParser()
Param.read('parameters.ini')
Twitdata = ConfigParser.ConfigParser()
Twitdata.read('twitdata.ini')

## authentication
auth = tweepy.OAuthHandler(Twitdata.get('Tweepy','consumer_key'), Twitdata.get('Tweepy','consumer_secret'))
auth.set_access_token(Twitdata.get('Tweepy','access_key'), Twitdata.get('Tweepy','access_secret'))

## initialize API
api = tweepy.API(auth)

global keywords
with open("keywords_bloemen_top10app.txt") as doc:
	keywords = unicode(doc.read()).lower().split(',')

exitFlag = 0
queueLock = threading.Lock()
countsLock = threading.Lock()

class Top10Streamer(StreamListener):

	def __init__(self, q, api = None):
		self.api = api or API()
		self.output  = 'tweets/'
		if not os.path.exists(os.path.dirname(os.path.abspath('__file__'))+"/tweets"):
			os.makedirs(os.path.dirname(os.path.abspath('__file__'))+"/tweets")
		self.delout  = open('tweets/delete.txt', 'a')
		self.q = q

	def on_status(self, status):
		
		# save tweet to file
		if "lievelingsbloem" in status.text.lower():
			with open(self.output + "lievelingsbloem/" + status.created_at.strftime("%Y-%m-%d.%H.00.00") + ".json", "a") as doc:
				doc.write(json.dumps(status._json) + "\n")
		# if "twuinbijt" in status.text.lower():
			# with open(self.output + "twuinbijt/" + status.created_at.strftime("%Y-%m-%d.%H.00.00") + ".json", "a") as doc:
				# doc.write(json.dumps(status._json) + "\n")
		if "tulpendag" in status.text.lower():
			with open(self.output + "tulpendag/" + status.created_at.strftime("%Y-%m-%d.%H.00.00") + ".json", "a") as doc:
				doc.write(json.dumps(status._json) + "\n")
		else:
			with open(self.output + status.created_at.strftime("%Y-%m-%d.%H.00.00") + ".json", "a") as doc:
				doc.write(json.dumps(status._json) + "\n")

			# put tweet in queue
			queueLock.acquire()
			self.q.put(status)
			queueLock.release()
				
		return 

	def on_delete(self, status_id, user_id):
		self.delout.write( str(status_id) + "\n")
		return

	def on_limit(self, track):
		sys.stderr.write(track + "\n")
		return

	def on_error(self, status_code):
		sys.stderr.write('Error: ' + str(status_code) + "\n")
		return False

	def on_timeout(self):
		sys.stderr.write("Timeout, sleeping for 60 seconds...\n")
		time.sleep(60)
		return 

class listenerThread(threading.Thread):
	def __init__(self, threadID, name, q, keywords):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		self.q = q
		self.keywords = keywords
	def run(self):
		print "Starting " + self.name
		start_streaming(self.q,self.keywords)
		print "Exiting " + self.name

class workerThread(threading.Thread):
	def __init__(self,threadID,name,q,counts):
		threading.Thread.__init__(self)
		self.threadID = threadID
		self.name = name
		self.q = q
		self.counts = counts
	def run(self):
		print "Starting " + self.name
		process_tweet(self.q,self.counts,self.name)
		print "Exiting " + self.name

def process_tweet(tweetQueue,tCounts,name):
	while not exitFlag:
		queueLock.acquire()
		if not tweetQueue.empty():
			tweet = tweetQueue.get()
			queueLock.release()
			
			# tokenize tweet.text
			tokens = tokenizeRawTweetText(tweet.text)
			
			# update counts
			countsLock.acquire()
			tCounts.update(tokens,calendar.timegm(tweet.created_at.timetuple()))
			interval = calendar.timegm(datetime.datetime.utcnow().timetuple())-calendar.timegm(tCounts.last_output.timetuple())
			if interval > tCounts.output_interval:
				tCounts.makeOutput()
			countsLock.release()
		else:
			queueLock.release()

def start_streaming(tweetQueue,keywords):
	listen = Top10Streamer(tweetQueue,api)
	stream = tweepy.Stream(auth, listen)
	print "Streaming started at " + datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")
	while True:
		try:
			stream.filter(track = keywords)
		except:
			print "Streaming disconnected at " + datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")
			stream.disconnect()

	print "Streaming stopped at " + datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S +0000 %Y")

def main():
	threadList = ["Worker-1", "Worker-2", "Worker-3"]
	tweetQueue = Queue.Queue(100000)
	threads = []

	count = tokenCounts(keywords,Param.getint('Parameters','min_interval'))
 	
	try:
		# Create listener thread
		thread = listenerThread(1,"Listener",tweetQueue,keywords)
		thread.start()
		threads.append(thread)

		# Create worker threads
		threadID = 2
		for tName in threadList:
			thread = workerThread(threadID, tName, tweetQueue, count)
			thread.start()
			threads.append(thread)
			threadID += 1
	except:
		exitFlag = 1
		for t in threads:
			t.join()
			print "Exiting Main Thread"


if __name__ == '__main__': main()	