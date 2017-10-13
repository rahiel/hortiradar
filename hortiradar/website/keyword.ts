import * as $ from "jquery";
import { render_graph } from "./interaction_graph";
const URLSearchParams = require("url-search-params");

declare const APP_ROOT: string;
declare const keyword_data: any;
declare const graph: any;
declare const display_tweets: number;
const searchParams = new URLSearchParams(window.location.search);


window.onload = function () {
    render_information(keyword_data);
    render_graph(graph);
}

export function render_information(data) {
    let timeSeries = [];
    for (let p of data.timeSeries) {
        timeSeries.push({
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        });
    }

    let chart = new CanvasJS.Chart("splineContainer", {
        title: {text: ""},
        animationEnabled: true,
        axisX: {
            valueFormatString: "D-M-YYYY HH:00",
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

    let stopcriterion = Math.min(display_tweets,data.tweets.length) // if there are less than display_tweets in the dataset
    for (let i = 0; i < stopcriterion; i++) {
        let tweet = document.getElementById(`tweet${i}`);
        twttr.widgets.createTweet(data.tweets[i], tweet, {
            conversation: "none",
            cards: "hidden",
            theme: "light",
            lang: "nl",
        });
    }

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

// navigate to fragment identifier
let hash = searchParams.get("hash");
if (hash != null) {
    window.location.hash = hash;
}
