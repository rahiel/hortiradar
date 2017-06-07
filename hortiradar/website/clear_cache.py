from redis import StrictRedis


redis = StrictRedis()

for key in redis.scan_iter():
    if key.startswith(b'"cache:') or key.startswith(b"loading:"):
        redis.delete(key)
