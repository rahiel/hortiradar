import * as $ from "jquery";
import * as _ from "lodash";
const flatpickr = require("flatpickr");
const fp_Dutch = require("flatpickr/dist/l10n/nl.js").default.nl;
const URLSearchParams = require("url-search-params");
const WordCloud = require("wordcloud");

import { renderGraph } from "./interaction_graph";

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
    renderTimeSeries(keyword_data);
    renderInformation(keyword_data);
    renderGraph(graph);
    renderSampleTweets();
    $("body").scrollspy({ target: "#toc" });
    pickPeriod();
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

function renderTimeSeries(data) {
    const peaks: Array<[number, Array<string>]> = data.peaks;
    const [peaks_i, peaks_summary] = _.unzip(peaks);
    let timeSeries = [];
    for (let i = 0; i < data.timeSeries.length; i++) {
        let p = data.timeSeries[i];
        let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        };
        if (peaks_i && peaks_i.includes(i)) {
            point["markerColor"] = "red";
            point["markerSize"] = 6;
            let peak_num = peaks_i.indexOf(i);
            point["toolTipContent"] = "{x}: {y}<br>Trefwoorden: " + peaks_summary[peak_num];
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

    function onClick(e) {
        let start = dateToString(e.dataPoint.x)
        window.open(window.location.pathname + "?start=" + start + "&period=hour");
    }
}

export function dateToString(date) {
    // this function was copied with permission from the author from: https://github.com/rahiel/archiveror/blob/aef7d9afe7ac5612bd4f8f27a42694fa33e9649c/src/utils.js#L56
    let y = date.getUTCFullYear();
    let m = (date.getUTCMonth() + 1).toString().padStart(2, "0");
    let d = date.getUTCDate().toString().padStart(2, "0");
    let H = date.getUTCHours().toString().padStart(2, "0");
    let M = date.getUTCMinutes().toString().padStart(2, "0");
    let timestamp = `${y}-${m}-${d}T${H}:${M}`;
    return timestamp;
}

export function renderInformation(data) {

    const maxCount = _.maxBy(data.tagCloud, (x) => x["count"])["count"];
    const options = {
        list: data.tagCloud.map(x => [x.text, x.count]),
        gridSize: Math.round(16 * $("#wordCloudDiv").width() / 1024),
        weightFactor: function (count) {
            return Math.max(12, Math.round(30 * Math.log(count) / Math.log(maxCount)));
        },
        fontFamily: "Times, serif",
        color: "random-dark",
        rotateRatio: 0,
        rotationSteps: 0,
        backgroundColor: "#fff"
    }
    WordCloud(document.getElementById("wordCloudDiv"), options);

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

}

export function renderTweets(tweets, conversation = false) {
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

export function showPictures() {
    // clicking on pictures shows them in a modal

    function click(event: MouseEvent) {
        let url = this.querySelector("img").src;  // `this` is a photoContainer div
        let img = document.createElement("img");
        img.src = url;
        img.classList.add("img-in-modal");
        document.getElementById("img-modal-body").appendChild(img);
        $("#imgModal").modal("show");
    }

    let images = document.getElementsByClassName("photoContainer") as HTMLCollectionOf<HTMLDivElement>;
    for (let image of images) {
        image.onclick = click;
    }

    $("#imgModal").on("hidden.bs.modal", function (e) {
        document.getElementById("img-modal-body").innerHTML = "";
    });
}

export function showLink() {

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
        let iframeURL = <HTMLAnchorElement>document.getElementById("iframe-url");
        iframeURL.textContent = href;
        iframeURL.href = href;
        iframeURL.target = "_blank";
        $("#iframeModal").modal("show");
    }

    let links = document.getElementsByClassName("link") as HTMLCollectionOf<HTMLAnchorElement>;
    for (let link of links) {
        link.onclick = click;
    }

    $("#iframeModal").on("hidden.bs.modal", function (e) {
        document.getElementById("iframe-container").innerHTML = "";
    });

}

function pickPeriod() {
    let addPeriodButton = document.getElementById("addPeriodButton");
    if (addPeriodButton == undefined) return;
    addPeriodButton.onclick = function () {
        document.getElementById("customPeriod").style.display = "block";
    };

    const options = {
        enableTime: true,
        locale: fp_Dutch,
        time_24hr: true,
        weekNumbers: true,
    };
    let [startPick, endPick] = flatpickr(".flatpickr", options);

    document.getElementById("analyseCustomPeriodButton").onclick = function () {
        let startDate = startPick.selectedDates[0];
        let endDate = endPick.selectedDates[0]

        let warning = document.getElementById("periodWarning");
        if ((endDate - startDate) < 0) {
            warning.textContent = "De einddatum moet na de begindatum zijn.";
            warning.style.display = "block";
            return;
        } else if ((endDate - startDate) / (1000 * 60 * 60 * 24) > 31) {
            warning.textContent = "Uw periode is langer dan een maand, verkort uw periode.";
            warning.style.display = "block";
            return;
        } else warning.style.display = "none";

        let start = dateToString(startPick.selectedDates[0]);
        let end = dateToString(endPick.selectedDates[0]);
        window.open(window.location.pathname + `?start=${start}&end=${end}&period=custom`);
    };
}
