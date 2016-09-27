Website
=======


# Installation

``` shell
sudo apt install virtualenv python-pip redis-server
git clone https://github.com/mctenthij/hortiradar.git
cd hortiradar/
virtualenv -p python venv
. venv/bin/activate
pip install -r website/requirements.txt
pip install --editable . --upgrade
pip install gunicorn gevent

cd website/
sudo apt install supervisor
sudo mkdir /var/log/hortiradar
sudo cp supervisor.conf /etc/supervisor/conf.d/hortiradar.conf
sudo systemctl enable supervisor.service

sudo apt install nginx
sudo cp nginx.conf /etc/nginx/sites-enable/hortiradar.conf
sudo cp caching.cron /etc/cron.d/hortiradar
```
