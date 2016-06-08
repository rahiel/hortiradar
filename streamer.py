#!/usr/bin/python
from json import dumps
from time import sleep
from sys import stderr
from os import makedirs
from os.path import exists, abspath, dirname

from tweepy import StreamListener, API
from pymongo import MongoClient

from tokencounts import tokenCounts


class Top10Streamer(StreamListener):

    def __init__(self, q, api=None):
        """
        Object that handles incoming data of the twitter streaming API

        Parameters
        q: 		queue of tweets that need to be processed
        output: folder where tweets are saved 									(TBD: auto-store tweets in DB)
        delout: file where ID's of tweets that have to be deleted are stored 	(TBD: auto-delete in DB)
        api: 	twitter API-object
        """
        self.api = api or API()
        self.output = 'tweets/'
        if not exists(dirname(abspath('__file__')) + "/tweets"):
            makedirs(dirname(abspath('__file__')) + "/tweets")
        self.delout = open('tweets/delete.txt', 'a')
        self.q = q

    def on_status(self, status):
        """
        Called when a new status arrives

        Parameters
        status: 	status object received from Twitter
        """

        # with open(self.output + status.created_at.strftime("%Y-%m-%d.%H.00.00") + ".json", "a") as doc:
        #     doc.write(dumps(status._json) + "\n")

        print(status.text)

        client = MongoClient('localhost', 27017)
        db = client.test_database
        db.tweets.insert_one(status._json)

        __queueLock.acquire()
        self.q.put(status)
        __queueLock.release()
        return

    def on_delete(self, status_id, user_id):
        """
        Called when a delete notice arrives for a status

        Parameters
        status_id: 	id of the status that has to be removed
        user_id:	id of the user that removed the status
        """
        self.delout.write(str(status_id) + "\n")
        return

    def on_limit(self, track):
        """
        Called when a limitation notice arrives

        Parameters
        track:		dictionary with information regarding limitation
        """
        stderr.write(track + "\n")
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        stderr.write('Error: ' + str(status_code) + "\n")
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        stderr.write("Timeout, sleeping for 60 seconds...\n")
        sleep(60)
        return

    def on_disconnect(self, notice):
        """Called when twitter sends a disconnect notice
        Disconnect codes are listed here:
        https://dev.twitter.com/docs/streaming-apis/messages#Disconnect_messages_disconnect
        """
        # TBD: notify if disconnected
        return
