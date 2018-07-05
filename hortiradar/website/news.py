from configparser import ConfigParser
from datetime import datetime
from urllib.request import urlretrieve, urlopen
from xml.etree import ElementTree
import re

from googletrans import Translator

from hortiradar.database import get_keywords, get_db, get_frog


# tags in the EMM are in English, therefore we need to translate the tags to Duth during processing
tlr = Translator()

keywords = get_keywords(local=True)
frog = get_frog()

db = get_db()
newsdb = db.news

config = ConfigParser()
config.read("../database/tasks_workers.ini")
posprob_minimum = config["workers"].getfloat("posprob_minimum")

pattern = re.compile(b"<td class=\"center_leadin\">Country:</td><td class=\"center_leadin\">([A-Za-z]+)</td>")


def check_if_exists(nid):
    return newsdb.find({"nid": nid}).count() > 0


def find_keywords_and_groups(text):
    # tokens contains a list of dictionaries with frog's analysis per token
    # each dict has the keys "index", "lemma", "pos", "posprob" and "text"
    # where "text" is the original text
    tokens = frog.process(text)
    kw = []
    groups = []
    for (i, t) in enumerate(tokens):
        lemma = t["lemma"]
        k = keywords.get(lemma, None)
        if k is not None:
            if t["posprob"] > posprob_minimum:
                if not t["pos"].startswith(k.pos + "("):
                    continue

            kw.append(lemma)
            groups += k.groups
    kw, groups = list(set(kw)), list(set(groups))
    return kw, groups


def process_triggers(item, group):
    """ This function determines all the trigger words that have been tagged by the EMM"""
    categories = item.findall("category")
    for it in categories:
        if it.text == group:
            attr = it.attrib
            for k in attr:
                if 'trigger' in k:
                    kws = [kw.lower().split("[")[0] for kw in attr[k].split("; ") if len(kw) > 0]
                    return kws
    return []


def process_item(item, kws, groups):
    title = item.find("title").text
    link = item.find("link").text
    pubdate = datetime.strptime(item.find("pubDate").text, "%a, %d %b %Y %H:%M:%S %z")
    description = item.find("description").text
    nid = item.find("guid").text

    source = item.find("source").text

    # flag is determined by the top level domain of the source url of the news message
    source_url = item.find("source").attrib.get("url")
    flag = source_url.split("/")[2].split(".")[-1]
    if flag in ["com", "org", "int"]:
        # flag is determined by querying medisys for country of source (more reliable but slower, therefore only when necessary)
        temp = urlopen("http://medisys.newsbrief.eu/medisys/web/jsp/sourcedef.jsp?language=en&option={s}".format(s=source)).read()
        res = re.findall(pattern, temp)
        if res:
            flag = res[0].lower()
        else:
            pass

    return {
        "nid": nid,
        "keywords": kws,
        "groups": groups,
        "title": title,
        "link": link,
        "pubdate": pubdate,
        "description": description,
        "source": source,
        "flag": "flags/{f}.gif".format(f=flag),
    }


def main():
    rssgroups = ["FruitandVegetables", "Flowers"]
    for group in rssgroups:
        url = "http://medisys.newsbrief.eu/rss?type=category&id={g}&language=all&duplicates=false".format(g=group)
        fn = "{g}.xml".format(g=group)
        urlretrieve(url, fn)

        et = ElementTree.parse(fn)
        r = et.getroot()

        items = r.find("channel").findall("item")
        for item in items:
            nid = item.find("guid").text
            if not check_if_exists(nid):
                triggers = process_triggers(item, group)
                text = " ".join([tlr.translate(t, src="en", dest="nl").text for t in triggers])
                kws, groups = find_keywords_and_groups(text)

                if kws:
                    newsdict = process_item(item, kws, groups)
                    newsdb.insert_one(newsdict)

if __name__ == '__main__':
    main()
