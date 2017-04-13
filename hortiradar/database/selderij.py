from os import environ

from celery import Celery


if environ.get("ROLE") == "master":
    broker_url = "amqp://guest@localhost:5672/hortiradar"
else:
    from worker_settings import password
    username = "worker"
    master = "acba.labs.vu.nl"
    broker_url = "amqp://{}:{}@{}:5672/hortiradar".format(username, password, master)

app = Celery("tasks", broker=broker_url)

app.conf.update(task_ignore_result=True, worker_prefetch_multiplier=20)


if __name__ == "__main__":
    app.start()
