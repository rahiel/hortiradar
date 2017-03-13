import requests


time_format = "%Y-%m-%d-%H-%M-%S"


class Tweety(object):
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.s = requests.Session()

        def wrap_api(method, uri_template, name=None):
            request = eval("self.s." + method)

            def call(*uri_params, **params):
                url = self.base_url + uri_template.format(*uri_params)
                params["token"] = self.token
                data = params.pop("data", None)
                r = request(url, params=params, data=data)
                # TODO: raise exception if request is unsuccessful
                if r.content:
                    return r.content
                else:
                    return r.status_code

            call.__name__ = name
            return call

        self.get_keywords = wrap_api("get", "/keywords", name="get_keywords")
        # tweety.get_keyword("bloemen", start=datetime..., end=datetime...)
        self.get_keyword = wrap_api("get", "/keywords/{}", name="get_keyword")
        self.get_keyword_id = wrap_api("get", "/keywords/{}/ids", name="get_keyword_id")
        self.get_keyword_media = wrap_api("get", "/keywords/{}/media", name="get_keyword_media")
        self.get_keyword_urls = wrap_api("get", "/keywords/{}/urls", name="get_keyword_urls")
        self.get_keyword_texts = wrap_api("get", "/keywords/{}/texts", name="get_keyword_texts")
        self.get_keyword_users = wrap_api("get", "/keywords/{}/users", name="get_keyword_users")
        self.get_keyword_wordcloud = wrap_api("get", "/keywords/{}/wordcloud", name="get_keyword_wordcloud")
        # tweety.get_keyword_series("meloen", step=3600)
        self.get_keyword_series = wrap_api("get", "/keywords/{}/series", name="get_keyword_series")
        self.get_groups = wrap_api("get", "/groups", name="get_groups")
        self.get_group = wrap_api("get", "/groups/{}", name="get_group")
        self.get_tweet = wrap_api("get", "/tweet/{}", name="get_tweet")
        self.delete_tweet = wrap_api("delete", "/tweet/{}", name="delete_tweet")
        #  tweety.patch_tweet(id_str, data=json.dumps({"spam": 1.0}))
        self.patch_tweet = wrap_api("patch", "/tweet/{}", name="patch_tweet")
