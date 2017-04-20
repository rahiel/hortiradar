import * as $ from "jquery";
const URLSearchParams = require("url-search-params");

declare const APP_ROOT: string;
declare const keyword_data: any;
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

    let twList = $("ul#tweetsList")
    $.each(data.tweets, function (idx, val) {
        if (idx < 15) { // Display a maximum of 15 tweets
            let li = $(`<li><div id="${val}"></div></li>`).appendTo(twList);

            let tweet = document.getElementById(val);
            twttr.widgets.createTweet(
                val, tweet,
                {
                    conversation : "none",    // or all
                    cards        : "hidden",  // or visible
                    linkColor    : "#cc0000", // default is blue
                    theme        : "light",    // or dark
                    lang         : "nl"
                })
        }
    });

    let urlList = $("ul#urlList")
    $.each(data.URLs, function (idx) {
        if (idx < 15) { // Display a maximum of 15 urls
            let li = $(`<li>${data.URLs[idx].occ}x <a href="${data.URLs[idx].link}">${data.URLs[idx].link}</a></li>`)
                .appendTo(urlList);
        }
    });

    let medList = $("div#mediaDiv")
    $.each(data.photos, function (idx) {
        if(idx < 15) { // Display a maximum of 15 photos
            if (idx % 3 == 2) {
                let li = $('<div id="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span id="text">'+data.photos[idx].occ+'</span></div><br/>')
                    .appendTo(medList);
            }
            else{
                let li = $('<div id="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span id="text">'+data.photos[idx].occ+'</span></div>')
                    .appendTo(medList);
            }
        }
    });

    let words = [];
    $.each(data.tagCloud, function (idx) {
        if (data.tagCloud[idx].text != searchParams.get("product")) {
            words.push({ text: data.tagCloud[idx].text, weight: 50*data.tagCloud[idx].weight**2 });
        } else {
            console.log(data.tagCloud[idx].text)
        }
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

    $.each(data.locations, function (idx) {
        // Create a marker and set its position.
        let marker = new google.maps.Marker({
            map: map,
            position: {lat: data.locations[idx].lat, lng: data.locations[idx].lng}
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
