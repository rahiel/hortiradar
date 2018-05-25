from os.path import dirname

from configparser import ConfigParser

Config = ConfigParser()
Config.read(dirname(__file__)+'/config.ini')

tweet_time_format = "%a %b %d %H:%M:%S +0000 %Y"

from .cluster import Cluster
from .tweet import ExtendedTweet, Token
from .stories import Stories