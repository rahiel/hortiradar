"""Script to migrate group management from the textfiles in `data` to a MongoDB
collection."""
from keywords import get_db, GROUPS


db = get_db()

for (group_name, filename) in GROUPS.items():
    with open(filename, "r") as f:
        keywords = []
        for line in f:
            lemma, pos = line.strip().split(",")
            keywords.append({"lemma": lemma, "pos": pos})
    group = {"name": group_name, "keywords": keywords}
    db.groups.insert_one(group)
