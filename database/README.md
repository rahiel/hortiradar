Database
========

# Usage

`config.ini` is a config file with:

``` shell
[twitter]
consumer_key = abcdefg
consumer_secret = hijklmno
access_key = 321321321-PQRSTUVWXYZ
access_secret = c3VwcmlzZWQgc29tZW9uZSBmb3VuZCB0aGlzISEhISEK
```

There are supervisor configurations and cron jobs for the following, but here an
overview of the different parts:

The tweets are saved in MongoDB with the `streamer` script:
``` shell
python streamer.py
```

The database is cleaned periodically (every day) by running:
``` shell
python clean.py
```

Make the indexes for the API with:
``` shell
python indexes.py
```

Start the API with:
``` shell
gunicorn api -k gevent -w 2 --threads 2
```

# Installation

Requirements:

* Python 2.7
* MongoDB
* RabbitMQ

``` shell
sudo apt install python-pip virtualenv mongodb-server rabbitmq-server redis-server
```

Get the code and make a virtualenv for all Python packages:
``` shell
cd ~
git clone https://github.com/mctenthij/hortiradar.git
cd hortiradar/
virtualenv -p python venv
. venv/bin/activate
```

Python dependencies:
``` shell
pip install -r database/requirements.txt --upgrade
```

Our common code in the hortiradar module:
``` shell
pip install --editable . --upgrade
```

Install cythonized Falcon:
``` shell
pip install cython --upgrade
pip install --no-binary :all: falcon --upgrade
```

We use the [Frog][] NLP software by the [Language Machines][lama] group at
Radboud University, this should be installed in the virtualenv (this will take a
while). [Follow the instruction][lamachine] for the local installation.

[Frog]: https://languagemachines.github.io/frog/
[lama]: http://applejack.science.ru.nl/languagemachines/
[lamachine]: https://proycon.github.io/LaMachine/

Install supervisor configurations and cron jobs:
``` shell
sudo cp streamer-supervisor.conf /etc/supervisor/conf.d/hortiradar-streamer.conf
sudo cp master-supervisor.conf /etc/supervisor/conf.d/hortiradar-master.conf
sudo cp api-supervisor.conf /etc/supervisor/conf.d/hortiradar-api.conf
sudo cp clean.cron /etc/cron.d/hortiradar-clean
sudo mkdir -p /var/log/hortiradar
sudo supervisorctl reread
sudo supervisorctl update
```

Finally with everything already running, set up the indexes:
``` shell
python indexes.py
```

Set up [access to RabbitMQ](http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html#setting-up-rabbitmq):
(Replace password with an actual good password.)
``` shell
sudo rabbitmqctl add_user worker password
sudo rabbitmqctl add_vhost hortiradar
sudo rabbitmqctl set_permissions -p hortiradar worker ".*" ".*" ".*"
sudo rabbitmqctl set_permissions -p hortiradar guest ".*" ".*" ".*"
```

Also place the password in a file called `worker_settings.py` in the database
directory like so:
``` python
password = "the password"
```

# Workers

We use a distributed task queue to process the incoming tweets in parallel.
Worker nodes need the following Debian packages:
``` shell
sudo apt install python-pip virtualenv redis-server
```

In addition they need all Python packages from the previous section including
the LaMachine software distribution, except Falcon.

Install the supervisor config:
``` shell
sudo cp worker-supervisor.conf /etc/supervisor/conf.d/hortiradar-worker1.conf
sudo mkdir -p /var/log/hortiradar
sudo supervisorctl reread
sudo supervisorctl update
```

Copy the config if you need more workers, replacing `worker1` with a higher
number.
