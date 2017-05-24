from datetime import datetime, timedelta
import re

import CommonMark
import ujson as json
from babel.dates import format_datetime, get_timezone
from flask import Blueprint, render_template, render_template_string, request
from flask_babel import Babel
from flask_mail import Mail
from flask_user import SQLAlchemyAdapter, UserManager, login_required
from redis import StrictRedis
from werkzeug.wrappers import Response

from hortiradar import TOKEN, Tweety, time_format
from hortiradar.database import GROUPS
from hortiradar.website import app, db
from models import User
from processing import cache, floor_time, process_details, process_top


bp = Blueprint("horti", __name__, template_folder="templates", static_folder="static")

# Initialize flask extensions
babel = Babel(app)
mail = Mail(app)

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

tweety = Tweety("http://127.0.0.1:8888", TOKEN)
redis = StrictRedis()

groups = sorted(GROUPS.keys())

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

docs = render_markdown("../../docs/api.md")

def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    else:
        return text[:limit - 1] + "…"

def format_number(number):
    """Format number using , as thousands separator."""
    return "{:,}".format(number)

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

def get_period(request, default_period=""):
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
        start = floor_time(datetime.strptime(start, "%Y-%m-%dT%H:%M"), hour=True)
        end = start + timedelta(hours=1)
        cache_time = 60 * 60 * 12
    else:
        period = "day"
        end = floor_time(datetime.utcnow(), hour=True)
        start = end - timedelta(days=1)
        cache_time = 60 * 60
    return period, start, end, cache_time

def display_datetime(dt):
    """Render UTC datetimes to Amsterdam local time."""
    babel_datetime_format = "EEEE d MMMM HH:mm y"
    dutch_timezone = get_timezone("Europe/Amsterdam")
    return format_datetime(dt, babel_datetime_format, tzinfo=dutch_timezone, locale="nl")

def display_group(group: str):
    """Render an internal group name suitable for display."""
    return {"bloemen": "Bloemen en Planten", "groente_en_fruit": "Groente en Fruit"}.get(group, group)

@bp.route("/")
def home():
    sync_time = redis.get("sync_time")
    if sync_time:
        sync_time = sync_time.decode("utf-8")

    max_amount = request.args.get("k", 10, type=int)
    period, start, end, cache_time = get_period(request, "day")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format), "group": "bloemen"}
    bloemen = cache(process_top, "bloemen", max_amount, params, cache_time=cache_time, path=get_req_path(request))
    params["group"] = "groente_en_fruit"
    groente_en_fruit = cache(process_top, "groente_en_fruit", max_amount, params, cache_time=cache_time, path=get_req_path(request))

    if isinstance(bloemen, Response):
        return bloemen
    if isinstance(groente_en_fruit, Response):
        return groente_en_fruit

    template_data = {
        "bloemen": bloemen,
        "groente_en_fruit": groente_en_fruit,
        "sync_time": sync_time,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "period": period
    }
    return render_template("home.html", title=make_title("BigTU research project"), **template_data)

@bp.route("/widget/<group>")
def top_widget(group):
    """A small widget showing the top 5 in the group."""
    max_amount = 10  # this is 10, so we re-use the cached data from the top 10
    _, start, end, cache_time = get_period(request, "day")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format), "group": group}
    data = cache(process_top, group, max_amount, params, cache_time=cache_time)[:5]
    data = [d["label"] for d in data]
    return render_template("widget.html", data=data)

@bp.route("/groups/")
@bp.route("/groups")
def view_groups():
    return render_template("groups.html", title=make_title("Groepen"), groups=groups)

@bp.route("/groups/<group>")
def view_group(group):
    period, start, end, cache_time = get_period(request, "day")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format), "group": group}
    keywords = cache(tweety.get_keywords, cache_time=cache_time, path=get_req_path(request), **params)
    if isinstance(keywords, Response):
        return keywords
    total = sum([entry["count"] for entry in keywords])
    for keyword in keywords:
        keyword["percentage"] = "{:.2f}".format(keyword["count"] / total * 100)
        keyword["count"] = format_number(keyword["count"])
    nums = range(1, len(keywords) + 1)
    template_data = {
        "nums_keywords": zip(nums, keywords),
        "group": group,
        "disp_group": display_group(group),
        "nums": nums,
        "total": format_number(total),
        "period": period,
        "start": display_datetime(start),
        "end": display_datetime(end)
    }
    return render_template("group.html", title=make_title(template_data["group"]), **template_data)

@bp.route("/keywords/<keyword>")
def view_keyword(keyword):
    period, start, end, cache_time = get_period(request, "week")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = cache(process_details, keyword, params, cache_time=cache_time, path=get_req_path(request))
    if isinstance(keyword_data, Response):
        return keyword_data

    urls = keyword_data["URLs"][:16]
    for url in urls:
        url["display_url"] = shorten(url["link"], 45)
    if not urls:
        urls.append({"occ": 0, "link": "#", "display_url": "Geen URLs gevonden"})
    del keyword_data["URLs"]

    keyword_data["tagCloud"] = keyword_data["tagCloud"][:200]

    photos = keyword_data["photos"][:16]
    if len(photos) > 2:         # TODO: other conditions
        photos = [(photos[i], photos[i+1]) for i in range(0, len(photos)-1, 2)]
    del keyword_data["photos"]

    display_tweets = 11
    keyword_data["tweets"] = keyword_data["tweets"][:display_tweets]

    num_tweets = keyword_data["num_tweets"]
    del keyword_data["num_tweets"]

    graph = keyword_data["graph"]
    del keyword_data["graph"]

    template_data = {
        "keyword": keyword,
        "keyword_data": json.dumps(keyword_data),
        "num_tweets": format_number(num_tweets),
        "urls": urls,
        "graph": json.dumps(graph),
        "photos": photos,
        "display_tweets": display_tweets,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "period": period
    }
    return render_template("keyword.html", title=make_title(keyword), **template_data)

@bp.route("/about")
def about():
    stats = json.loads(redis.get("t:stats"))
    return render_template("about.html", title="Over de Hortiradar", **stats)

@bp.route("/docs/api")
def api():
    return render_template("api.html", title=make_title("API documentatie"), docs=docs)

@bp.route("/loading/<loading_id>", methods=["GET", "POST"])
def loading(loading_id):
    if request.method == "GET":
        return render_template("loading.html", title=make_title("Laden"))
    else:
        loading = redis.get("loading:" + loading_id)
        if loading in [b"done", None]:
            status = "done"
        else:
            status = "loading"
        return jsonify({"status": status})

@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404

@bp.route("/_get_clusters")
def show_clusters():
    # TODO: currently loading in file with clusters, implement caching of clusters
    now = floor_time(datetime.utcnow(), hour=True)
    cluster_file = now.strftime("%Y%m%d_%H_clusters.json")
    with open(cluster_file) as f:
        clusters = json.load(f)
    return jsonify(clusters)

@bp.route("/members")
@login_required
def members_page():
    return render_template_string("""
    {% extends "base.html" %}
    {% block content %}
        <h2>Members page</h2>
        <p>This page can only be accessed by authenticated users.</p><br/>
        <p><a href={{ url_for('home') }}>Home page</a> (anyone)</p>
        <p><a href={{ url_for('members_page') }}>Members page</a> (login required)</p>
    {% endblock %}
    """)

def make_title(page):
    return page + " — Hortiradar"


app.register_blueprint(bp, url_prefix="/hortiradar")

if __name__ == "__main__":
    app.run(debug=True, port=9000)
