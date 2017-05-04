from datetime import datetime, timedelta
import re

import CommonMark
import ujson as json
from babel.dates import format_datetime
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
from processing import cache, get_process_top_params, process_details, process_top, round_time


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

@bp.route("/")
def home():
    sync_time = redis.get("sync_time")
    if sync_time:
        sync_time = sync_time.decode("utf-8")
    return render_template("home.html", title=make_title("BigTU research project"), sync_time=sync_time)

@bp.route("/widget/<group>")
def top_widget(group):
    """A small widget showing the top 5 in the group."""
    max_amount = request.args.get("k", 10, type=int)  # this is 10, so we re-use the cached data from the top 10
    data = cache(process_top, group, max_amount)[:5]
    data = [d["label"] for d in data]
    return render_template("widget.html", data=data)

@bp.route("/groups/")
@bp.route("/groups")
def view_groups():
    return render_template("groups.html", title=make_title("Groepen"), groups=groups)

@bp.route("/groups/<group>")
def view_group(group):
    params = get_process_top_params(group)
    keywords = cache(tweety.get_keywords, path=get_req_path(request), **params)
    if isinstance(keywords, Response):
        return keywords
    total = sum([entry["count"] for entry in keywords])
    for keyword in keywords:
        keyword["percentage"] = "{:.2f}".format(keyword["count"] / total * 100)
    nums = range(1, len(keywords) + 1)
    template_data = {"nums_keywords": zip(nums, keywords), "group": group, "nums": nums, "total": total}
    return render_template("group.html", title=make_title(group), **template_data)

@bp.route("/keywords/<keyword>")
def view_keyword(keyword):
    period = request.args.get("period", "", type=str)
    if period:
        end = datetime.utcnow()
        if period == "day":
            start = end - timedelta(days=1)
        elif period == "week":
            start = end - timedelta(weeks=1)
        elif period == "month":
            start = end - timedelta(days=30)
        end = round_time(end)
        start = round_time(start)
    else:
        period = "week"         # default
        interval = request.args.get("interval", 60 * 60 * 24 * 7, type=int)
        end = request.args.get("end", "", type=str)
        if end:
            end = datetime.strptime(end, "%Y-%m-%d %H:%M") + timedelta(hours=1)
        else:
            end = round_time(datetime.utcnow())
        start = end + timedelta(seconds=-interval)
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = cache(process_details, keyword, params, path=get_req_path(request))
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

    num_tweets = 11
    keyword_data["tweets"] = keyword_data["tweets"][:num_tweets]

    keyword_data = json.dumps(keyword_data)
    babel_datetime_format = "EEEE d MMMM HH:mm y"
    template_data = {
        "keyword": keyword,
        "keyword_data": keyword_data,
        "urls": urls,
        "photos": photos,
        "num_tweets": num_tweets,
        "start": format_datetime(start, babel_datetime_format, locale="nl"),
        "end": format_datetime(end, babel_datetime_format, locale="nl"),
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

@bp.route("/_add_top_k/<group>")
def show_top(group):
    """Visualize a top k result file"""
    max_amount = request.args.get("k", 10, type=int)
    data = cache(process_top, group, max_amount)
    return jsonify(result=data)

@bp.route("/_get_clusters")
def show_clusters():
    # TODO: currently loading in file with clusters, implement caching of clusters
    now = round_time(datetime.utcnow())
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
