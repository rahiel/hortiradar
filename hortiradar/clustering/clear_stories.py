from redis import StrictRedis

from hortiradar.database import get_db


redis = StrictRedis()
db = get_db()
groups = [g["name"] for g in db.groups.find({}, projection={"name": True, "_id": False})]

for group in groups:
    k = "s:{gr}".format(gr=group)
    redis.delete(k)
