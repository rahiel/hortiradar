import json

import requests


class Tweety(object):
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.s = requests.Session()

        def _wrap_api(method, uri_template):
            request = eval("self.s." + method)

            def call(*uri_params, **params):
                url = self.base_url + uri_template.format(*uri_params)
                params["token"] = self.token
                data = params.pop("data", None)
                r = request(url, params=params, data=data)
                if r.content:
                    return json.loads(r.content)
                else:
                    return r.status_code

            return call

        self.get_keywords = _wrap_api("get", "/keywords")
        # tweety.get_keyword("bloemen", start=datetime..., end=datetime...)
        self.get_keyword = _wrap_api("get", "/keywords/{}")
        self.get_keyword_id = _wrap_api("get", "/keywords/{}/ids")
        self.get_keyword_media = _wrap_api("get", "/keywords/{}/media")
        self.get_keyword_urls = _wrap_api("get", "/keywords/{}/urls")
        self.get_keyword_texts = _wrap_api("get", "/keywords/{}/texts")
        self.get_keyword_users = _wrap_api("get", "/keywords/{}/users")
        self.get_keyword_wordcloud = _wrap_api("get", "/keywords/{}/wordcloud")
        # tweety.get_keyword_series("meloen", step=3600)
        self.get_keyword_series = _wrap_api("get", "/keywords/{}/series")
        self.get_tweet = _wrap_api("get", "/tweet/{}")
        self.delete_tweet = _wrap_api("delete", "/tweet/{}")
        # tweety.patch_tweet, required kwargs: data
        self.patch_tweet = _wrap_api("patch", "/tweet/{}")
