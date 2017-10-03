Website
=======


# Installation

Follow instructions at <https://certbot.eff.org/> for the SSL certificate and the instructions
at <https://weakdh.org/sysadmin.html> to use a strong Diffie-Hellman group.

``` shell
sudo apt install virtualenv python3-pip redis-server
git clone https://github.com/mctenthij/hortiradar.git
cd hortiradar/
virtualenv -p python3 venv
. venv/bin/activate
pip install --editable . --upgrade
cd hortiradar/website/
pip install -r requirements.txt

sudo apt install supervisor
sudo mkdir /var/log/hortiradar
sudo cp supervisor.conf /etc/supervisor/conf.d/hortiradar.conf
sudo cp processing-supervisor.conf /etc/supervisor/conf.d/hortiradar-processor.conf
sudo cp open_nsfw-supervisor.conf /etc/supervisor/conf.d/open_nsfw.conf

sudo apt install nginx
sudo cp nginx.conf /etc/nginx/sites-enabled/hortiradar.conf
sudo systemctl restart nginx.service
sudo cp caching.cron /etc/cron.d/hortiradar-cache

sudo apt install nodejs-legacy npm
echo "prefix = ~/.npm-global" > ~/.npmrc
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.profile
. ~/.profile
npm -g install npm
npm install
npm run build
```

The Flask app also needs to send email:
``` shell
sudo apt install mailutils postfix     # select "Internet Site" and "acba.labs.vu.nl" for "mail name"
```
Test sending mail with:
``` shell
echo 'Hello! | mail -r hortiradar -s 'Test email' user@example.com  # replace user@example.com with own email address
```

Copy flask-user files for Dutch translation of login/register/etc. pages:
``` shell
cd ~/hortiradar/
cp -r ./venv/lib/python3*/site-packages/flask_user/translations/ ./website/
```

[Install Docker][docker] for the NSFW photo filter. Add the user running the
Hortiradar to the `docker` group:
``` shell
sudo gpasswd -a $USER docker
```
logout and login again.

Build the image:
``` shell
docker build -t open_nsfw https://raw.githubusercontent.com/rahiel/open_nsfw--/master/Dockerfile
```

Start everything:
``` shell
sudo systemctl restart supervisor.service
```

[docker]: https://docs.docker.com/engine/installation/
