from main import get_db


db = get_db()
db.tweets.delete_many({"num_keywords": 0})
