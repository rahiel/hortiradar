from os import environ

from celery import Celery


if environ.get("ROLE") == "master":
    broker_url = "amqp://guest@localhost//"
else:
    broker_url = "amqp://guest@localhost//"

app = Celery("tasks", broker=broker_url)

app.conf.update(task_ignore_result=True)


if __name__ == "__main__":
    app.start()
