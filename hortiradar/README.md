# Hortiradar

There are README's for the different parts of the Hortiradar with instructions
on how to set them up.

Many processes are managed by [Supervisor][], it starts them at system boot and
restarts them when they fail. Failure notifications are sent to a Telegram group
with [supervisor-alert][].

The error messages of failing cron jobs are sent to the same Telegram group
with [telegram-send][]:

``` shell
sudo apt install moreutils python3-pip
sudo pip3 install telegram-send
sudo telegram-send --global-config --configure-group
```

[supervisor]: http://supervisord.org/
[supervisor-alert]: https://github.com/rahiel/supervisor-alert
[telegram-send]: https://github.com/rahiel/telegram-send
