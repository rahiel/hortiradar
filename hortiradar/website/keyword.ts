import * as $ from "jquery";
import { renderGraph } from "./interaction_graph";

import * as _ from "lodash";
const URLSearchParams = require("url-search-params");

declare const APP_ROOT: string;
declare const keyword_data: any;
declare const graph: any;
declare const display_tweets: number;
const searchParams = new URLSearchParams(window.location.search);


if (typeof keyword_data !== "undefined") {
    window.onload = function () { main(); };
}

// the different kind of tweets we show at the tweets section on the keyword page
const enum tweetButton {
    sample = "sample",
    retweets = "retweets",
    interactions = "interactions",
};

function main() {
    renderInformation(keyword_data);
    renderGraph(graph);
    renderSampleTweets();
    $("body").scrollspy({ target: "#toc" });
    showPictures();
    showLink();

    document.getElementById(tweetButton.sample).onclick = renderSampleTweets;
    document.getElementById(tweetButton.retweets).onclick = renderRetweets;
    document.getElementById(tweetButton.interactions).onclick = renderInteractionTweets;

    // navigate to fragment identifier
    let hash = searchParams.get("hash");
    if (hash != null) {
        window.location.hash = hash;
    }
}

export function renderInformation(data) {
    let timeSeries = [];
    const peaks = data.peaks;
    for (let i = 0; i < data.timeSeries.length; i++) {
        let p = data.timeSeries[i];
        let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        };
        if (peaks.includes(i)) {
            point["markerColor"] = "red";
            point["markerSize"] = 6;
            point["toolTipContent"] = "{x}: {y}";
        }
        timeSeries.push(point);
    }

    let chart = new CanvasJS.Chart("splineContainer", {
        title: {text: ""},
        animationEnabled: true,
        axisX: {
            valueFormatString: "HH:00 D-M-YYYY",
            interval: 6,
            intervalType: "hour",
            labelAngle: 50
        },
        axisY : {
            title: "Aantal tweets"
        },
        data: [{
            type: "line",
            dataPoints: timeSeries,
            click: onClick
        }]
    });
    chart.render();

    let words = [];
    $.each(data.tagCloud, function (index) {
        words.push({ text: data.tagCloud[index].text, weight: data.tagCloud[index].weight });
    });
    $("#wordcloudDiv").empty().jQCloud(words, {
        autoResize: false
    });

    // Create a map object and specify the DOM element for display.
    let map = new google.maps.Map(document.getElementById("mapDiv"), {
        center: {lat: data.centerloc.lat, lng: data.centerloc.lng},
        disableDefaultUI: true,
        zoom: 6
    });

    $.each(data.locations, function (index) {
        // Create a marker and set its position.
        let marker = new google.maps.Marker({
            map: map,
            position: {lat: data.locations[index].lat, lng: data.locations[index].lng}
        });
    });

    function onClick(e) {
        let year = String(e.dataPoint.x.getUTCFullYear())
        let month = String(e.dataPoint.x.getUTCMonth() + 1)
        let day = String(e.dataPoint.x.getUTCDate())
        let hour = String(e.dataPoint.x.getUTCHours())
        let start = year + "-" + month + "-" + day + "T" + hour + ":00";
        window.open(window.location.pathname + "?start=" + start + "&period=hour");
    }

}

function renderTweets(tweets, conversation = false) {
    // clear all tweets
    for (let i = 0; i < display_tweets; i++) {
        document.getElementById(`tweet${i}`).innerHTML = "";
    }

    let stopcriterion = Math.min(display_tweets, tweets.length) // if there are less than display_tweets in the dataset
    for (let i = 0; i < stopcriterion; i++) {
        let tweet = document.getElementById(`tweet${i}`);
        let options = {
            cards: "hidden",
            theme: "light",
            lang: "nl",
            dnt: true,
        };
        if (conversation === false) {
            options["conversation"] = "none";
        }
        twttr.widgets.createTweet(tweets[i], tweet, options);
    }
}

function renderSampleTweets() {
    let tweets = _.sampleSize(keyword_data.tweets, display_tweets);
    renderTweets(tweets);
    highlightTweetButton(tweetButton.sample);
}

function renderRetweets() {
    renderTweets(keyword_data.retweets);
    highlightTweetButton(tweetButton.retweets);
}

function renderInteractionTweets() {
    let tweets = _.sampleSize(keyword_data.interaction_tweets, display_tweets);
    renderTweets(tweets, true);
    highlightTweetButton(tweetButton.interactions);
}

function highlightTweetButton(button: tweetButton) {
    // highlight the active button
    let tweetButtons = [tweetButton.sample, tweetButton.retweets, tweetButton.interactions];
    for (let b of tweetButtons) {
        if (b === button) {
            document.getElementById(b).classList.add("btn-primary");
            document.getElementById(b).classList.remove("btn-default");
        } else {
            document.getElementById(b).classList.add("btn-default");
            document.getElementById(b).classList.remove("btn-primary");
        }
    }
}

function showPictures() {
    // clicking on pictures shows them in a modal

    function click(event: MouseEvent) {
        let url = this.querySelector("img").src;  // `this` is a photoContainer div
        let img = document.createElement("img");
        img.src = url;
        img.classList.add("img-in-modal");
        document.getElementById("img-modal-body").appendChild(img);
        $("#imgModal").modal("show");
    }

    let images = document.getElementsByClassName("photoContainer");
    for (let image of images) {
        image.onclick = click;
    }

    $("#imgModal").on("hidden.bs.modal", function (e) {
        document.getElementById("img-modal-body").innerHTML = "";
    });
}

function showLink() {

    function click(event: MouseEvent) {
        let url = new URL(this.parentNode.querySelector(".full-link").href);
        let href = url.href;
        if (url.protocol === "http:") {
            url.protocol = "https:";
        }

        let html;
        let video_id;
        if (url.hostname === "www.youtube.com") {
            video_id = new URLSearchParams(url.search).get("v");
        } else if (url.hostname === "youtu.be") {
            video_id = url.pathname.substring(1);
        }
        if (video_id) {
            html = `<iframe class="iframe-in-modal" src="https://www.youtube.com/embed/${video_id}?rel=0" frameborder="0" sandbox="allow-same-origin allow-scripts" allow="encrypted-media" allowfullscreen></iframe>`;
        }

        let status_id;
        if (url.hostname === "twitter.com") {
            let re = /twitter\.com\/.*\/status\/(\d+)/;
            let match = url.href.match(re);
            if (match) {
                status_id = match[1];
                let options = {
                    align: "center",
                    lang: "nl",
                    dnt: true,
                };
                twttr.widgets.createTweet(status_id, document.getElementById("iframe-container"), options);
            }
        }

        let iframe;
        if (html) {
            let elem = document.createElement("div");
            elem.innerHTML = html;
            iframe = elem.firstChild;
        } else if (!status_id) {
            iframe = document.createElement("iframe");
            iframe.src = url.href;
            iframe.sandbox = "";
            iframe.classList.add("iframe-in-modal");
        }

        if (iframe) {
            document.getElementById("iframe-container").appendChild(iframe);
        }
        document.getElementById("iframe-url").textContent = href;
        document.getElementById("iframe-url").href = href;
        document.getElementById("iframe-url").target = "_blank";
        $("#iframeModal").modal("show");
    }

    let links = document.getElementsByClassName("link");
    for (let link of links) {
        link.onclick = click;
    }

    $("#iframeModal").on("hidden.bs.modal", function (e) {
        document.getElementById("iframe-container").innerHTML = "";
    });

}
