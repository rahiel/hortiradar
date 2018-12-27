from calendar import timegm
from datetime import datetime
from random import choice
from string import ascii_letters
from time import sleep

import ujson as json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import Babel
from flask_mail import Mail
from flask_user import SQLAlchemyAdapter, UserManager, current_user, login_required, roles_required
from redis import StrictRedis
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.wrappers import Response
from wtforms.validators import AnyOf

from hortiradar import TOKEN, Tweety, time_format
from hortiradar.database import lemmatize
from hortiradar.website import app, db

from forms import GroupForm, RoleForm
from models import Role, User
from processing import cache, process_details, process_news, process_stories, process_tokens, process_top
from utils import (
    display_datetime, display_group, display_number, display_polarity, display_pos, get_period, get_req_path, get_roles,
    is_deluxe, jsonify, make_title, parse_pos, render_markdown, shorten)


bp = Blueprint("horti", __name__, template_folder="templates", static_folder="static")

# Initialize flask extensions
babel = Babel(app)
mail = Mail(app)

# Setup Flask-User
db_adapter = SQLAlchemyAdapter(db, User)        # Register the User model
user_manager = UserManager(db_adapter, app)     # Initialize Flask-User

tweety = Tweety("http://127.0.0.1:8888", TOKEN)
redis = StrictRedis()
docs = render_markdown("../../docs/api.md")


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
    groups = cache(tweety.get_groups)
    if isinstance(groups, Response):
        return groups
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
        keyword["count"] = display_number(keyword["count"])
    nums = range(1, len(keywords) + 1)
    template_data = {
        "nums_keywords": zip(nums, keywords),
        "group": group,
        "disp_group": display_group(group),
        "nums": nums,
        "total": display_number(total),
        "period": period,
        "start": display_datetime(start),
        "end": display_datetime(end)
    }
    return render_template("group.html", title=make_title(template_data["disp_group"]), **template_data)

@bp.route("/groups/<group>/top")
def top(group):
    max_amount = request.args.get("k", 10, type=int)
    period, start, end, cache_time = get_period(request, "day")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format), "group": group}
    data = cache(process_top, group, max_amount, params, cache_time=cache_time, path=get_req_path(request))

    if isinstance(data, Response):
        return data

    if len(data) < max_amount:
        max_amount = len(data)

    template_data = {
        "data": data,
        "group": group,
        "disp_group": display_group(group),
        "max_amount": str(max_amount),
        "period": period,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "title": make_title("Top {} {}".format(max_amount, display_group(group)))
    }
    return render_template("top.html", **template_data)

@bp.route("/groups/<group>/keywords")
def view_keywords_in_group(group):
    """Show a list of all the keywords in the group."""
    keywords = cache(tweety.get_group, group, cache_time=60 * 60, path=get_req_path(request))
    if isinstance(keywords, Response):
        return keywords
    if keywords:
        keywords.sort(key=lambda x: x["lemma"])
        for k in keywords:
            k["pos"] = display_pos(k["pos"])
    template_data = {
        "disp_group": display_group(group),
        "title": make_title("Trefwoorden in {}".format(display_group(group))),
        "keywords": keywords,
        "total": len(keywords)
    }
    return render_template("group_keywords.html", **template_data)

@bp.route("/groups/<group>/edit", methods=["GET", "POST"])
@login_required
def edit_group(group):
    roles = get_roles(current_user)
    if ("g:" + group) not in roles and "admin" not in roles:
        flash("U heeft geen rechten om de groep \"{}\" aan te passen.".format(display_group(group)), "error")
        return redirect(url_for("horti.home"))
    if request.method == "GET":
        keywords = cache(tweety.get_group, group, cache_time=60 * 60, path=get_req_path(request))
        if isinstance(keywords, Response):
            return keywords
        if keywords:
            keywords.sort(key=lambda x: x["lemma"])
            for k in keywords:
                k["pos"] = display_pos(k["pos"])
        template_data = {
            "keywords": keywords,
            "group": group,
            "disp_group": display_group(group),
            "title": make_title("{} aanpassen".format(group))
        }
        return render_template("edit_group.html", **template_data)
    elif request.method == "POST":
        data = json.loads(request.data)
        keywords = data["keywords"]
        if data["action"] == "delete":
            for k in keywords:
                k["pos"] = parse_pos(k["pos"])
            keywords = [(k["lemma"], k["pos"]) for k in keywords]

            current_keywords = json.loads(tweety.get_group(group))
            current_keywords = [(k["lemma"], k["pos"]) for k in current_keywords]

            new_keywords = set(current_keywords) - set(keywords)
            new_keywords = [{"lemma": k[0], "pos": k[1]} for k in new_keywords]

            tweety.put_group(group, data=json.dumps(new_keywords))
            cache(tweety.get_group, group, cache_time=60 * 60, force_refresh=True)
            return jsonify({"status": "ok"})
        elif data["action"] == "add":
            keywords = [(k["lemma"], k["pos"]) for k in keywords]
            user_lemmas = [k[0] for k in keywords]

            key = "".join([choice(ascii_letters) for _ in range(11)])
            lemmatize.apply_async((key, user_lemmas), queue="workers")

            current_keywords = json.loads(tweety.get_group(group))
            current_keywords = [(k["lemma"], k["pos"]) for k in current_keywords]

            processed_lemmas = None
            while processed_lemmas is None:
                processed_lemmas = redis.get(key)
                sleep(0.1)
            processed_lemmas = json.loads(processed_lemmas)

            diff = {}
            for (p, u) in zip(processed_lemmas, user_lemmas):
                if u != p:
                    diff[u] = p
            if diff:
                return jsonify({"status": "diff", "diff": diff})

            new_keywords = set(current_keywords) | set(keywords)
            new_keywords = [{"lemma": k[0], "pos": k[1]} for k in new_keywords]

            tweety.put_group(group, data=json.dumps(new_keywords))
            cache(tweety.get_group, group, cache_time=60 * 60, force_refresh=True)
            return jsonify({"status": "ok"})

@bp.route("/keywords/<keyword>")
def view_keyword(keyword):
    deluxe = is_deluxe(current_user)  # users in the "deluxe" group can specify their own time period

    period, start, end, cache_time = get_period(request, "week")
    if period == "custom":
        if not deluxe:
            flash("Deze functionaliteit is alleen beschikbaar voor goedgekeurde gebruikers.", "error")
            return redirect(url_for("horti.home"))
        if (end - start).days > 31:
            flash("Periode langer dan een maand is niet toegestaan", "error")
            return redirect(url_for("horti.home"))
        if start > end:
            flash("De einddatum moet na de begindatum zijn.", "error")
            return redirect(url_for("horti.home"))
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = cache(process_details, keyword, params, cache_time=cache_time, path=get_req_path(request))
    if isinstance(keyword_data, Response):
        return keyword_data

    urls = keyword_data["URLs"][:16]
    for url in urls:
        url["display_url"] = shorten(url["link"], 80)
    del keyword_data["URLs"]

    keyword_data["tagCloud"] = keyword_data["tagCloud"][:200]

    photos = enumerate(keyword_data["photos"])  # number of photo's is limited in processing.py
    del keyword_data["photos"]

    display_tweets = 11
    max_tweets = 200
    keyword_data["tweets"] = keyword_data["tweets"][:max_tweets]
    keyword_data["retweets"] = keyword_data["retweets"][:display_tweets]
    keyword_data["interaction_tweets"] = keyword_data["interaction_tweets"][:max_tweets]

    num_tweets = keyword_data["num_tweets"]
    del keyword_data["num_tweets"]

    graph = keyword_data["graph"]
    del keyword_data["graph"]

    polarity = keyword_data["polarity"]
    del keyword_data["polarity"]

    polarity_face = display_polarity(polarity)

    gtrends_period = {"day": "now 1-d", "week": "now 7-d", "month": "today 1-m"}.get(period, "now 1-d")
    period_name = {"day": "dag", "week": "week", "month": "maand"}.get(period, "dag")

    news = []
    for item in keyword_data["news"]:
        item["pubdate"] = display_datetime(item["pubdate"])
        del item["nid"]
        news.append(item)
    del keyword_data["news"]

    template_data = {
        "keyword": keyword,
        "keyword_data": json.dumps(keyword_data),
        "deluxe": deluxe,
        "num_tweets": display_number(num_tweets),
        "urls": urls,
        "graph": json.dumps(graph),
        "photos": photos,
        "display_tweets": display_tweets,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "period": period,
        "period_name": period_name,
        "polarity": polarity,
        "polarity_face": polarity_face,
        "gtrends_period": gtrends_period,
        "news": news
    }
    return render_template("keyword.html", title=make_title(keyword), **template_data)

@bp.route("/news/<keyword>")
def view_news(keyword):
    period, start, end, cache_time = get_period(request, "week")
    news_data = cache(process_news, keyword, start, end, cache_time=cache_time, path=get_req_path(request))
    if isinstance(news_data, Response):
        return news_data

    period_name = {"day": "dag", "week": "week", "month": "maand"}.get(period, "dag")
    news = []
    for item in news_data:
        item["pubdate"] = display_datetime(item["pubdate"])
        del item["nid"]
        news.append(item)

    template_data = {
        "keyword": keyword,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "period": period,
        "period_name": period_name,
        "news": news
    }
    return render_template("news.html", title=make_title(keyword), **template_data)

@bp.route("/anomalies/<group>")
def view_anomalies(group):
    keywords = cache(tweety.get_group, group, cache_time=60 * 60, path=get_req_path(request))
    if isinstance(keywords, Response):
        return keywords

    keywords = [k["lemma"] for k in keywords]
    anomalies = json.loads(redis.get("anomalies"))
    anomalies = [a for a in anomalies if a[0] in keywords]
    start = datetime.strptime(json.loads(redis.get("anomalies_start")), time_format)
    end = datetime.strptime(json.loads(redis.get("anomalies_end")), time_format)

    template_data = {
        "peaks": anomalies,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "num_peaks": len(anomalies)
    }
    return render_template("anomaly.html", title=make_title("Piekdetectie"), **template_data)

@bp.route("/keywords/<keyword>/occurrences")
def view_token_co_occurrences(keyword):
    period, start, end, cache_time = get_period(request, "week")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = cache(process_tokens, keyword, params, cache_time=cache_time, path=get_req_path(request))
    if isinstance(keyword_data, Response):
        return keyword_data

    occurrences = []
    for k in keyword_data["occurrences"]:
        if k["text"] != keyword:
            k["pos"] = parse_pos(k["pos"].split("(")[0])
            occurrences.append(k)

    nums = range(1, len(occurrences) + 1)
    template_data = {
        "keyword": keyword,
        "period": period,
        "start": display_datetime(start),
        "end": display_datetime(end),
        "occurrences": zip(nums, occurrences)
    }
    return render_template("occurrences.html", title=make_title(keyword), **template_data)

@bp.route("/keywords/<keyword>/tweets")
def view_tweets_about_keyword(keyword):
    period, start, end, cache_time = get_period(request, "week")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    keyword_data = cache(process_details, keyword, params, cache_time=cache_time, path=get_req_path(request))
    if isinstance(keyword_data, Response):
        return keyword_data

    num_tweets = keyword_data["num_tweets"]
    tweets = keyword_data["tweets"]
    retweets = keyword_data["retweets"]

    template_data = {
        "keyword": keyword,
        "num_tweets": num_tweets,
        "num_unique_tweets": len(tweets),
        "tweets": tweets,
        "retweets": retweets,
        "period": period,
        "start": display_datetime(start),
        "end": display_datetime(end)
    }
    return render_template("tweets.html", title=make_title(keyword), **template_data)

def filter_story(story, display_tweets):
    story["urls"] = story["URLs"][:16]
    for url in story["urls"]:
        url["display_url"] = shorten(url["link"], 45)
    del story["URLs"]

    story["tagCloud"] = story["tagCloud"][:200]
    story["photos"] = story["photos"][:16]

    story["polarityface"] = display_polarity(story["polarity"])
    return story

@bp.route("/clustering/<group>")
def view_stories(group):
    period, start, end, cache_time = get_period(request, "week")
    params = {"start": start.strftime(time_format), "end": end.strftime(time_format)}
    story_data = cache(process_stories, group, params, cache_time=cache_time, path=get_req_path(request))

    if isinstance(story_data, Response):
        return story_data

    active_stories, closed_stories = story_data

    storify_data = []
    timeline_data = []

    timeline_start = timegm(start.timetuple()) * 1000
    timeline_end = timegm(end.timetuple()) * 1000

    display_tweets = 11
    display_active_stories = 10
    display_closed_stories = 5

    for story in active_stories:
        if not (len(storify_data) < display_active_stories):
            break
        story = filter_story(story, display_tweets)
        timeline_info = {"label": len(storify_data), "times": story["cluster_details"]}
        del story["cluster_details"]

        storify_data.append(story)
        timeline_data.append(timeline_info)

    for story in closed_stories:
        if not (len(storify_data) < display_active_stories + display_closed_stories):
            break
        story = filter_story(story, display_tweets)
        timeline_info = {"label": len(storify_data), "times": story["cluster_details"]}
        del story["cluster_details"]

        storify_data.append(story)
        timeline_data.append(timeline_info)

    template_data = {
        "group": display_group(group),
        "storify_data": json.dumps(storify_data),
        "timeline_data": json.dumps(timeline_data),
        "timeline_start_ts": timeline_start,
        "timeline_end_ts": timeline_end,
        "display_tweets": display_tweets,
        "num_stories": min(display_active_stories + display_closed_stories, len(storify_data)),
        "start": display_datetime(start),
        "end": display_datetime(end),
        "period": period
    }
    return render_template("storify.html", title=make_title(group), **template_data)

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
    elif request.method == "POST":
        loading = redis.get("loading:" + loading_id)
        if loading in [b"done", None]:
            status = "done"
        else:
            status = "loading"
        return jsonify({"status": status})

@app.errorhandler(404)
def page_not_found(error):
    return render_template("page_not_found.html"), 404

@bp.route("/admin", methods=("GET", "POST"))
@roles_required("admin")
def admin():
    role_form = RoleForm()
    users = User.query.all()
    usernames = [u.username for u in users]
    role_form.username.validators.append(AnyOf(usernames, message="Username not found."))
    if role_form.validate_on_submit():
        form = role_form
        user = User.query.filter(User.username == form.username.data).one()

        try:
            role = Role.query.filter(Role.name == form.role.data).one()
        except NoResultFound:
            role = Role(name=form.role.data)
            db.session.add(role)

        if form.action.data == "add":
            if role not in user.roles:
                user.roles.append(role)
                db.session.add(user)
        elif form.action.data == "remove":
            if role in user.roles:
                user.roles.remove(role)
                db.session.add(user)

        db.session.commit()
        return redirect(url_for("horti.admin"))

    group_form = GroupForm()
    if group_form.validate_on_submit():
        form = group_form
        name = form.name.data
        if form.action.data == "add":
            tweety.post_groups(name=name)
        elif form.action.data == "remove":
            tweety.delete_group(name)
        groups = cache(tweety.get_groups, force_refresh=True)
        return redirect(url_for("horti.admin"))

    # display groups
    have_groups = False
    while not have_groups:
        groups = cache(tweety.get_groups)
        if not isinstance(groups, Response):
            have_groups = True
            groups.sort()
        sleep(0.2)

    # display roles
    roles = {}
    for user in users:
        roles[user.username] = ", ".join(sorted([r.name for r in user.roles]))

    template_data = {
        "role_form": role_form,
        "users": users,
        "roles": roles,
        "groups": groups,
        "group_form": group_form
    }
    return render_template("admin.html", title=make_title("Admin"), **template_data)

@bp.route("/profile")
@login_required
def profile():
    roles = get_roles(current_user)
    groups = [n[2:] for n in roles if n.startswith("g:")]
    labels = [display_group(g) for g in groups]
    has_group = len(groups) > 0
    is_admin = "admin" in roles
    has_confirmed_email = current_user.has_confirmed_email()
    template_data = {
        "groups": [(val, labels[i]) for (i, val) in enumerate(groups)],
        "has_group": has_group,
        "has_confirmed_email": has_confirmed_email,
        "is_admin": is_admin
    }
    return render_template("profile.html", title=make_title("Profiel"), **template_data)


app.register_blueprint(bp, url_prefix="/hortiradar")

if __name__ == "__main__":
    app.run(debug=True, port=9000)
