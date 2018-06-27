import * as $ from "jquery";
import * as d3 from "d3";
import { renderGraph } from "./interaction_graph";
import { timelines } from "d3-timelines";
import { showPictures, showLink, renderTweets } from "./keyword";

declare const storify_data: any;
declare const timeline_data: any;
declare const display_tweets: number;
declare const num_stories: number;
declare const timeline_start_ts: number;
declare const timeline_end_ts: number;

declare const APP_ROOT: string;


if (typeof storify_data !== "undefined") {
    window.onload = function () { main(); };
}

// the different kind of tweets we show at the tweets section on the keyword page
const enum tweetButton {
    sample = "sample",
    retweets = "retweets",
    interactions = "interactions",
};

function main() {
    
    let colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    build_timeline(colorScale)

    fill_summary_column(colorScale)

    fill_story_information(0,colorScale)

}

function fill_story_information(loc,colorScale) {

    let data = storify_data[loc]

    let start = new Date(data.startStory)
    let end = new Date(data.endStory)

    document.getElementById("numTweets").textContent = data.num_tweets;
    document.getElementById("numTweets2").textContent = data.num_tweets;
    document.getElementById("numTweets3").textContent = data.num_tweets;
    document.getElementById("numTweets4").textContent = data.num_tweets;
    document.getElementById("polarity").textContent = data.polarity;
    document.getElementById("polarity-face").textContent = data.polarityface;
    document.getElementById("startStory").textContent = start.toLocaleDateString();
    document.getElementById("endStory").textContent = end.toLocaleDateString();

    d3.select("#storyColor")
    .attr('style','width: 100%; height: 25px; border-radius: 8px; background-color: '+colorScale(loc));

    d3.select("#storySummary").selectAll('div').remove();

    let displaySummary = d3.select("#storySummary")
    .selectAll('div')
    .data([data.summarytweet])
    .enter()
    .append('div')
    .attr('id','sumtweetdiv');

    let storytweet = document.getElementById('sumtweetdiv');
    twttr.widgets.createTweet(data.summarytweet, storytweet, {
        conversation: "none",
        cards: "hidden",
        theme: "light",
        lang: "nl",
        align: "center"
    });

    renderInformation(data);
    renderGraph(data.graph);
    renderTweets(data.tweets);
    showPictures();
    showLink();

}

function fill_summary_column(colorScale) {

    let storylist = d3.select('#stories')
    .selectAll('div.group')
    .data(storify_data);

    let newStory = storylist
    .enter()
    .append('div')
    .attr('id',function(d,x){ return "colorstory"+x})
    .attr('class','group');

    newStory
    .append('div')
    .attr('class','colorstory')
    .attr('style', function(d, x) { return "background-color: " + colorScale(x); });

    newStory
    .append('div')
    .attr("id",function(d,x){ return "sumtweet"+x });

    for (let i = 0; i < num_stories; i++) {
        // make colorbar clickable to show information
        document.getElementById(`colorstory${i}`)
        .addEventListener("click", function() { fill_story_information(i,colorScale)});

        // add clickable summary tweet
        let storytweet = document.getElementById(`sumtweet${i}`);
        twttr.widgets.createTweet(storify_data[i].summarytweet, storytweet, {
            conversation: "none",
            cards: "hidden",
            theme: "light",
            lang: "nl"
        });
    }
}

function build_timeline(colorScale) {

    // Add tooltip div
    let infobox = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 1e-6);

    let tlwidth = 900; // TODO: should be made platform aware
    let tlheight = 470-20*(15-num_stories); // Adjust height of the timeline based on the number of stories it displays (max = 15 stories)

    let tlchart = timelines()
    .stack()
    .colors(colorScale)
    .itemHeight(20)
    .margin({left:10, right:60, top:0, bottom:0})
    .beginning(timeline_start_ts)
    .ending(timeline_end_ts)
    .tickFormat({
        format: function(d) { return d3.timeFormat("%y-%m-%d %I %p")(d) },
        tickTime: d3.timeHour,
        tickInterval: 3,
        tickSize: 5,
    })
    .rotateTicks(30)
    .hover(function (cluster, i, story) {
        let colors = tlchart.colors();
        infobox
        .attr("style","border-color: "+colors(i))
        .html("<b><i>Cluster-time:</i></b> " + d3.timeFormat("%y-%m-%d %I %p")(new Date(cluster.starting_time)) + "<br /><b><i>Summary:</i></b> " + cluster.summarytweet)
        .style("left", (d3.event.pageX ) + "px")
        .style("top", (d3.event.pageY) + "px");
    })
    .mouseover(function (cluster, i, story) {
        infobox.transition()
        .duration(100)
        .style("opacity",1);
    })
    .mouseout(function (cluster, i, story) {
        infobox.transition()
        .style("opacity",1e-6);
    })
    .showToday()
    .showTodayFormat({marginTop: 0, marginBottom: 0, width: 5, color: d3.rgb("#CCCCCC")})
    .fullLengthBackgrounds()
    .background(d3.rgb("#EEEEEE"));

    let tlsvg = d3.select("#timelineStorify").append("svg").attr("width", tlwidth).attr("height", tlheight)
    .datum(timeline_data).call(tlchart);
}

function renderInformation(data) {
    
    let timeSeries = [];
    for (let i = 0; i < data.timeSeries.length; i++) {
        let p = data.timeSeries[i];
        let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        };
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

    let medList = $('div#mediaDiv').empty()
    for (let idx=0; idx < data.photos.length; idx++) {
        if (idx%2 == 1) {
            let li = $('<div class="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span class="imgText">'+data.photos[idx].occ+'</span></div><br>')
            .appendTo(medList);
        } else {
            let li = $('<div class="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span class="imgText">'+data.photos[idx].occ+'</span></div>')
            .appendTo(medList);
        }
    }

    if (data.urls.length !== 0) {
        d3.select('#urls').selectAll('tbody').remove();
        let table = d3.select('#urls');
        let tbody = table.append('tbody');
        let rows = tbody.selectAll('tr')
            .data(data.urls)
            .enter()
            .append('tr');

        rows.append('td').html(function (d: {link: string; occ: string; display_url: string; }) { return d.occ; });
        let cell = rows.append('td')
        let content = cell.append('a')
            .attr('class', "full-link")
            .attr('target', "_blank")
            .attr('href', function (d: {link: string; occ: string; display_url: string; }) { return d.link; } )
        content.append('i')
            .attr('class', "fa fa-external-link")
            .attr('aria-hidden', "true")
        cell.append('a')
            .attr('class',"link")
            .html(function (d: {link: string; occ: string; display_url: string; }) { return d.display_url; });
    } else {
        let linkList = $('div#linkDiv').empty()
        let nolinks = $('<p>Er zijn geen links gevonden.</p>')
            .appendTo(linkList);
    }

    if (data.hashtags.length !== 0) {
        d3.select('#hashtags').selectAll('tbody').remove();
        let table = d3.select('#hashtags');
        let tbody = table.append('tbody');
        let rows = tbody.selectAll('tr')
            .data(data.hashtags)
            .enter()
            .append('tr');

        rows.append('td').html(function (d: {ht: string, occ: string; }) { return d.occ; });
        rows.append('td').html(function (d: {ht: string, occ: string; }) { return d.ht; });
    } else {
        let linkList = $('div#htDiv').empty()
        let nolinks = $('<p>Er zijn geen hashtags gevonden.</p>')
            .appendTo(linkList);
    }

}