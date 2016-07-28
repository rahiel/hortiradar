# Usage

`config.ini` is a config file with:

``` shell
[twitter]
consumer_key = abcdefg
consumer_secret = hijklmno
access_key = 321321321-PQRSTUVWXYZ
access_secret = c3VwcmlzZWQgc29tZW9uZSBmb3VuZCB0aGlzISEhISEK
```

The tweets are saved in MongoDB with the main script:
``` shell
python main.py
```

The database is cleaned periodically by running:
``` shell
python clean.py
```

The indexes for the API are made with:
``` shell
python indexes.py
```

The API is started with:
``` shell
gunicorn api -k gevent -w 2 --threads 2
```

# Installation

Requirements:

* Python 2.7
* MongoDB

``` shell
sudo apt install python-pip mongodb-server
```

Python dependencies:
``` shell
pip install -r requirements.txt --upgrade
```

Install cythonized Falcon:
``` shell
pip install cython --upgrade
pip install --no-binary :all: falcon --upgrade
```
