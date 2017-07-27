"""Script to migrate group management from the textfiles in `data` to a MongoDB
collection."""
import argparse

from keywords import get_db


GROUPS = {
    "bloemen": "data/flowers.txt",
    "groente_en_fruit": "data/fruitsandveg.txt",
}


db = get_db()


parser = argparse.ArgumentParser()
parser.add_argument("--wordlist", help="wordlist(s) to insert into Mongo", nargs="+", type=str)
parser.add_argument("--name", help="name(s) for the wordlists", nargs="+", type=str)
parser.add_argument("-a", "--all", help="insert all wordlists in data into Mongo", action="store_true")
args = parser.parse_args()

if args.all:
    groups = GROUPS.items()
if args.wordlist:
    assert len(args.wordlist) == len(args.name)
    groups = zip(args.name, args.wordlist)


for (group_name, filename) in groups:
    with open(filename, "r") as f:
        keywords = []
        for line in f:
            lemma, pos = line.strip().split(",")
            keywords.append({"lemma": lemma, "pos": pos})
    group = {"name": group_name, "keywords": keywords}
    db.groups.delete_many({"name": group_name})
    db.groups.insert_one(group)
