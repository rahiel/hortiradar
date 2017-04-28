import * as $ from "jquery";
const URLSearchParams = require("url-search-params");

declare const APP_ROOT: string;
declare const keyword_data: any;
declare const num_tweets: number;
const searchParams = new URLSearchParams(window.location.search);


window.onload = function () {
    let data = keyword_data;
    let contents = [];
    let timeSeries = [];
    let query_interval;

    if (searchParams.get("end") === null) {
        query_interval = 60*60*24*7;
    } else {
        query_interval = 60*60;
    }

    for (let p of data.timeSeries) {
        timeSeries.push({
            x: new Date(p.year, p.month-1, p.day, p.hour),
            y: p.value
        });
    }

    let chart = new CanvasJS.Chart("splineContainer", {
        // title:{
        //   text: "Time Series of tweets for "+Url.get.product
        // },
        animationEnabled: true,   // change to true
        axisX: {
            valueFormatString: "YYYY-MM-DD HH",
            interval: 6,
            intervalType: "hour",
            labelAngle: 50
        },
        data: [{
            type: "line", //change it to line, area, column, pie, etc
            dataPoints: timeSeries,
            click: onClick
        }]
    });
    chart.render();

    for (let i = 0; i < num_tweets; i++) {
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
    $("#wordcloudDiv").jQCloud(words, {
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
        let year = String(e.dataPoint.x.getFullYear())
        let month = String(e.dataPoint.x.getMonth() + 1)
        let day = String(e.dataPoint.x.getDate())
        let hour = String(e.dataPoint.x.getHours())
        let end = year + "-" + month + "-" + day + " " + hour + ":00";
        window.open(window.location.href + "&end=" + end)
    }
}
