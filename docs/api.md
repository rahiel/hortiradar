# API

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-generate-toc again -->
**Table of Contents**

- [Introduction](#introduction)
- [Resources](#resources)
    - [`/keywords`](#keywords)
        - [`/keywords/{keyword}`](#keywordskeyword)
        - [`/keywords/{keyword}/ids`](#keywordskeywordids)
        - [`/keywords/{keyword}/media`](#keywordskeywordmedia)
        - [`/keywords/{keyword}/urls`](#keywordskeywordurls)
        - [`/keywords/{keyword}/texts`](#keywordskeywordtexts)
        - [`/keywords/{keyword}/users`](#keywordskeywordusers)
        - [`/keywords/{keyword}/wordcloud`](#keywordskeywordwordcloud)
        - [`/keywords/{keyword}/series`](#keywordskeywordseries)
    - [`/tweet/{id_str}`](#tweetidstr)
- [Python Wrapper](#python-wrapper)

<!-- markdown-toc end -->

## Introduction

The data in the Hortiradar is accessible from a HTTP API. The base URL is:
``` text
http://bigtu.q-ray.nl
```

Every request requires an authentication token passed in as a GET parameter:
``` text
http://bigtu.q-ray.nl/keywords?token=123456abcd
```

An incorrect token results in a 404 error. In what follows, resources and
examples are shown relative to the base URL, so the resource `/keywords` is
located at: `http://bigtu.q-ray.nl/keywords`.

The API talks in JSON: responses are either JSON or a HTTP error. The same API
is used for the [Hortiradar website](https://acba.labs.vu.nl/hortiradar/).
Internally we use the Tweety [Python Wrapper](#python-wrapper) for our API. The
Tweety method names are mentioned at the corresponding API resources.

**Note**: some requests may take a long time before you get a response. This
means that the database is working, as it has to analyze a lot of tweets! Please
be patient and do not prematurely cancel your request to retry.

**The API is still in beta and subject to change.**

## Resources

### `/keywords`

The main API resource is `/keywords`. Sending it a GET request returns a list of
objects with all tracked keywords and their count: the number of tweets
containing that keyword.

The keyword objects are sorted from most to least mentioned, with as keys
`keyword` for the keyword name and `count` for the number of occurrences.

By default this resource shows all keywords from all keyword groups, with an
additional `group` GET parameter the group can be specified. Currently available
groups are `bloemen` and `groente_en_fruit`.

All resources under `/keywords` take the optional `start` and `end` GET
parameters. With these you can specify the range of time you're interested in.
They are strings using the time format `%Y-%m-%d-%H-%M-%S`, so for example
`2016-11-24-14-01-26` is 24th November 2016 at 14:01:26. If you don't specify
`start` or `get` you will get all matching tweets in the database.

For example, to get an overview of all keyword counts in the "bloemen" group
from 2016-10-15 to 2016-11-15:
``` shell
GET http://bigtu.q-ray.nl/keywords?token=123456abcd&group=bloemen&start=2016-10-15-00-00-00&end=2016-11-15-00-00-00
```

Example output:
``` json
[
  {
    "keyword": "plant",
    "count": 62
  },
  {
    "keyword": "bos",
    "count": 48
  },
  {
    "keyword": "fruit",
    "count": 21
  },
  {
    "keyword": "bloemen",
    "count": 20
  }
]
```

The following resources are shown as URI templates, so in the resource
`/keywords/{keyword}/ids` the part with the curly braces should be replaced with
the actual value you're interested in, for example `/keywords/banaan/ids`.

Tweety: `Tweety.get_keywords(group)`

#### `/keywords/{keyword}`

This resource provides additional data for specific keywords. For example,
sending a GET request to `/keywords/fruit` gives a list of tweet objects with
the entities and timestamp as provided by Twitter, and the NLP analysis of the
tweet's text.

This resource is only internally available in compliance with Twitter's terms of
service. If you have to read this, then you don't have access to this resource.
You could however have access to data derived from the raw tweets, provided in
the next resources.

Tweety: `Tweety.get_keyword(keyword)`

#### `/keywords/{keyword}/ids`

Sending a GET request for a specific keyword returns a list of strings, each
representing a tweet id. You can request more data on the tweet directly from
Twitter.

Tweety: `Tweety.get_keyword_id(keyword)`

#### `/keywords/{keyword}/media`

Responds to GET requests with a list of objects with the `entities` key. The
`entities` key holds the `media` key with data as given by Twitter's API.

Tweety: `Tweety.get_keyword_media(keyword)`

#### `/keywords/{keyword}/urls`

The same as with media, but now the `entities` objects hold the `urls` key as
supplied by Twitter.

Tweety: `Tweety.get_keyword_urls(keyword)`

#### `/keywords/{keyword}/texts`

Returns a list with objects containing tweet texts on GET requests. The objects
have `text` and `id_str` keys. This resource is only internally available.

Tweety: `Tweety.get_keyword_texts(keyword)`

#### `/keywords/{keyword}/users`

On GET: returns a list of users found tweeting the keyword. The users are
objects with the keys `id_str` and `count`, the number of times they tweeted the
keyword.

Tweety: `Tweety.get_keyword_users(keyword)`

#### `/keywords/{keyword}/wordcloud`

On GET: makes a wordcloud of all words in the tweet texts containing the
keyword. Responds with a list of objects with as keys `word` and `count`, sorted
on the count.

Tweety: `Tweety.get_keyword_wordcloud(keyword)`

#### `/keywords/{keyword}/series`

This resource is useful to see how much a keyword is tweeted over time. It
returns a time series with the number of tweets from `start` to `end` in bins of
`step`, all three specified as GET parameters. `step` is a mandatory GET
parameter: number of seconds as an integer.

Returns an object where:
- start is the beginning of the first bin
- end is the end of the last bin (so nothing was counted after this time)
- step is the requested time bin size
- bins is the number of filled bins
- series is an object where the keys are the bin numbers and the values the
  counts

For example to get a time series of the keyword "ananas" for the whole day of
October 1st 2016 with a bin size of an hour:
``` shell
GET http://bigtu.q-ray.nl/keywords/ananas/series?token=123456abcd&start=2016-10-01-00-00-00&end=2016-10-02-00-00-00&step=2600
```

With as output:
``` json
{
  "series": {
    "15": 4,
    "14": 5,
    "12": 1,
    "11": 1,
    "9": 3,
    "7": 2,
    "5": 2,
    "4": 2,
    "3": 3,
    "0": 1
  },
  "bins": 10,
  "end": "2016-10-01-22-00-00",
  "step": 3600,
  "start": "2016-10-01-06-00-00"
}
```
The `series` key holds the time series object. It is represented with bin
numbers and their count, missing bins are empty. So above bin 0 with a count of
1 means that there was one tweet about "ananas" in the period from 2016-10-01
00:00 to 01:00. In 01:00-02:00 and from 02:00-03:00 there were zero tweets, With
3 tweets again in 03:00-04:00. The most tweets were from 14:00-15:00 with a
count of 5.

Tweety: `Tweety.get_keyword_series(keyword, step=2600)`

### `/tweet/{id_str}`

This resource is for internal use only.

On GET: shows the raw Twitter data for the tweet.
On DELETE: deletes the tweet from the database.
On PATCH: modifies specified data for the tweet. 

Tweety: `Tweety.get_tweet(id_str)`, `Tweety.delete_tweet(id_str)`

## Python Wrapper

It's preferable to have descriptive functions in code instead of bare HTTP
requests. Internally we use the Tweety wrapper for Python 2 (open an issue if
you need Python 3 support). Install it from our repository:

``` shell
pip install git+https://github.com/mctenthij/hortiradar.git
```

And use it like:

``` python
from hortiradar import Tweety

# The Tweety class takes the base URL and the token as arguments.
tweety = Tweety("http://bigtu.q-ray.nl", "123456abcd")

all_keywords = tweety.get_keywords()
flowers = tweety.get_keywords("bloemen")
banana_wordcloud = tweety.get_keyword_wordcloud("banaan")
```

URI template parameters are positional arguments of tweety methods and GET
parameters are optional keyword arguments of tweety methods. Notice that the
token is only passed in once to the `Tweety` constructor.

All API methods are available in Tweety, see a list of them with `dir(tweety)`.
