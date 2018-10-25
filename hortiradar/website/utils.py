import re
from datetime import datetime, timedelta

import CommonMark
import ujson as json
from babel.dates import format_datetime, get_timezone
from werkzeug.wrappers import Response


def render_markdown(filename):
    parser = CommonMark.Parser()
    renderer = CommonMark.HtmlRenderer()
    with open(filename) as f:
            doc = f.read()
    ast = parser.parse(doc)
    doc = renderer.render(ast)
    # add internal links
    find_section = lambda x: re.search(r"<h([2-6])>(?:<.+>)?(.+?)(?:<.+>)?<\/h\1>", x)
    sub = lambda x: x.lower().replace(" ", "-").translate({ord(c): "" for c in "{}/"})
    section = find_section(doc)
    while section:
        start, end = section.span()
        gr = section.groups()
        sec = '<h{0} id="{1}">{2}</h{0}>'.format(gr[0], sub(gr[1]), gr[1])
        doc = doc[:start] + sec + doc[end:]
        section = find_section(doc)
    return doc

def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    else:
        return text[:limit - 1] + "…"

def jsonify(*args, **kwargs):
    if args and kwargs:
        raise ValueError
    if len(args) == 1:
        data = args[0]
    elif len(args) > 1:
        data = list(args)
    if kwargs:
        data = dict(kwargs)
    return Response(json.dumps(data), status=200, mimetype="application/json")

def get_req_path(request):
    """The path that the user requested with get parameters."""
    return request.url[len(request.url_root) - 1:]

def floor_time(dt, *, hour=False, day=False):
    if hour:
        return dt - timedelta(minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    elif day:
        return dt - timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    else:
        return Exception("Missing keyword argument")

def get_period(request, default_period=""):
    time_format = "%Y-%m-%dT%H:%M"
    period = request.args.get("period", default_period, type=str)
    if period in ["day", "week", "month"]:
        if period == "day":
            end = floor_time(datetime.utcnow(), hour=True)
            start = end - timedelta(days=1)
            cache_time = 60 * 60
        elif period == "week":
            end = floor_time(datetime.utcnow(), hour=True)
            start = end - timedelta(weeks=1)
            cache_time = 60 * 60
        elif period == "month":
            end = floor_time(datetime.utcnow(), day=True)
            start = end - timedelta(days=30)
            cache_time = 60 * 60 * 24
    elif period == "hour":
        # when clicking on data points in the time series
        start = request.args.get("start", "", type=str)
        start = floor_time(datetime.strptime(start, time_format), hour=True)
        end = start + timedelta(hours=1)
        cache_time = 60 * 60 * 12
    elif period == "custom":
        start = request.args.get("start", "", type=str)
        start = datetime.strptime(start, time_format)
        end = request.args.get("end", "", type=str)
        end = datetime.strptime(end, time_format)
        cache_time = 60 * 60 * 12
    else:
        period = "day"
        end = floor_time(datetime.utcnow(), hour=True)
        start = end - timedelta(days=1)
        cache_time = 60 * 60
    return period, start, end, cache_time

def display_polarity(polarity):
    if polarity > 0.5:
        polarity_face = "😃"    # U+1F603: grinning face with big eyes
    elif polarity > 0.1:
        polarity_face = "🙂"    # U+1F642: slightly smiling face
    elif polarity > -0.1:
        polarity_face = "😐"    # U+1F610: neutral face
    elif polarity > -0.5:
        polarity_face = "🙁"    # U+1F641: slightly frowning face
    else:
        polarity_face = "🤮"    # U+1F92E: face vomiting
    return polarity_face

def display_number(number):
    """Format number using , as thousands separator."""
    return "{:,}".format(number)

def display_datetime(dt):
    """Render UTC datetimes to Amsterdam local time."""
    babel_datetime_format = "EEEE d MMMM HH:mm y"
    dutch_timezone = get_timezone("Europe/Amsterdam")
    return format_datetime(dt, babel_datetime_format, tzinfo=dutch_timezone, locale="nl")

def display_group(group: str) -> str:
    """Render an internal group name suitable for display."""
    return {"bloemen": "Bloemen en Planten", "groente_en_fruit": "Groente en Fruit"}.get(group, group)

def display_pos(pos: str) -> str:
    return display_pos.p.get(pos, pos)
display_pos.p = {
    "ADJ": "bijvoeglijk naamwoord",
    "BW": "bijwoord",
    "LET": "leesteken",
    "LID": "lidwoord",
    "N": "zelfstandig naamwoord",
    "SPEC": "eigennaam / onbekend",
    "TSW": "tussenwerpsel",
    "TW": "telwoord",
    "VG": "voegwoord",
    "VNW": "voornaamwoord",
    "VZ": "voorzetsel",
    "WW": "werkwoord"
}

def parse_pos(text: str) -> str:
    return parse_pos.p.get(text, text)
parse_pos.p = {v: k for (k, v) in display_pos.p.items()}

def get_roles(current_user):
    return [r.name for r in current_user.roles]

def make_title(page):
    return page + " — Hortiradar"
