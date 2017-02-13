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
pip install --editable . --upgrade
cd website/
pip install -r requirements.txt

sudo apt install supervisor
sudo mkdir /var/log/hortiradar
sudo cp supervisor.conf /etc/supervisor/conf.d/hortiradar.conf
sudo systemctl restart supervisor.service

sudo apt install nginx
sudo cp nginx.conf /etc/nginx/sites-enabled/hortiradar.conf
sudo systemctl restart nginx.service
sudo cp caching.cron /etc/cron.d/hortiradar
```

The Flask app also needs to send email:
``` shell
sudo apt install mailutils postfix     # select "Internet Site" and "acba.labs.vu.nl" for "mail name"
```
Test sending mail with:
``` shell
echo 'Hello! | mail -r hortiradar -s 'Test email' user@example.com  # replace user@example.com with own email address
```
