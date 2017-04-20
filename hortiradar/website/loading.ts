import "es6-promise/auto";
import "whatwg-fetch";


declare const APP_ROOT: string;
const URLSearchParams = require("url-search-params");
const searchParams = new URLSearchParams(window.location.search);


function check() {
    fetch(window.location.pathname, {
        method: "POST"
    }).then(function (response) {
        return response.json();
    }).then(function (j) {
        if (j.status === "done") {
            window.location.replace(window.location.origin + searchParams.get("redirect"));
        } else {
            let dots = document.getElementById("title");
            dots.innerHTML = dots.innerHTML + ".";
            setTimeout(() => check(), 1500);
        }
    });
}

check();
