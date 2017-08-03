from configparser import ConfigParser

from .cluster import Cluster
from .tweet import ExtendedTweet
from .stories import Stories

Config = ConfigParser()
Config.read('config.ini')

tweet_time_format = "%a %b %d %H:%M:%S +0000 %Y"