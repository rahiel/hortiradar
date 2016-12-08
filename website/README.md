Website
=======


# Installation

Follow instructions at <https://certbot.eff.org/> for the SSL certificate and the instructions
at <https://weakdh.org/sysadmin.html> to use a strong Diffie-Hellman group.

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
sudo cp nginx.conf /etc/nginx/sites-enabled/hortiradar.conf
sudo cp caching.cron /etc/cron.d/hortiradar
```