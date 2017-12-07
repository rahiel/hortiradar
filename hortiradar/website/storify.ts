import * as $ from "jquery";
import * as d3 from "d3";
import { renderGraph } from "./interaction_graph";
import { renderInformation } from "./keyword";
import { timelines } from "d3-timelines";

declare const storify_data: any;
declare const timeline_data: any;
declare const display_tweets: number;
declare const num_stories: number;
declare const timeline_start_ts: number;
declare const timeline_end_ts: number;

window.onload = function () {

    let colorScale = d3.scaleOrdinal(d3.schemeCategory10);

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

    build_timeline(colorScale)

    // make summarytweets clickable
    for (let i = 0; i < num_stories; i++) {
        document.getElementById(`colorstory${i}`)
        .addEventListener("click", function() { change_data(i,colorScale)});

        let storytweet = document.getElementById(`sumtweet${i}`);

        twttr.widgets.createTweet(storify_data[i].summarytweet, storytweet, {
            conversation: "none",
            cards: "hidden",
            theme: "light",
            lang: "nl"
        });
    }

    change_data(0,colorScale)
}

function update_information(data) {

    d3.select('#urls').selectAll('tbody').remove();
    let urltable = d3.select('#urls');
    let tbody = urltable.append('tbody');

    let rows = tbody.selectAll('tr')
      .data(data.urls)
      .enter()
      .append('tr');

    rows.append('td').html(function (d: any) { return d.occ; });
    let cell = rows.append('td')
    cell.append('a')
        .attr('href', function (d: any) { return d.link; } )
        .html(function (d: any) { return d.display_url; });

    d3.select('#tweetlist').selectAll('div.tweetdiv').remove();
    let tweetlist = d3.select('#tweetlist')
      .selectAll('div.tweetdiv')
      .data(data.tweets);

    let newTweet = tweetlist
      .enter()
      .append('div')
      .attr("class","tweetdiv")
      .attr("id",function(d,x){ return "tweet"+x });

    let medList = $('div#mediaDiv').empty()
    for (let idx=0; idx < data.photos.length; idx++) {
      if (idx%2 == 1) {
          let li = $('<div id="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span class="imgText">'+data.photos[idx].occ+'</span></div><br>')
          .appendTo(medList);
        }
        else{
          let li = $('<div id="photoContainer"><img class="twitImage" src="'+data.photos[idx].link+'" /><span class="imgText">'+data.photos[idx].occ+'</span></div>')
          .appendTo(medList);
        }
    }

}

function build_timeline(colorScale) {

    // Add tooltip div
    let infobox = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 1e-6);

    let tlwidth = 900; // TODO: should be made platform aware

    let tlchart = timelines()
    .width(tlwidth*5) // TODO: relative to interval
    .colors(colorScale)
    .stack()
    .showTimeAxisTick()
    .allowZoom(false)
    .itemHeight(15)
    .beginning(timeline_start_ts)
    .ending(timeline_end_ts)
    .tickFormat({
        format: function(d) { return d3.timeFormat("%y-%m-%d %I %p")(d) },
        tickTime: d3.timeHour,
        tickInterval: 6,
        tickSize: 5,
    })
    .rotateTicks(30)
    .hover(function (cluster, i, story) {
        let colors = tlchart.colors();
        infobox
        .attr("style","border-color: "+colors(i))
        .text("Cluster-time: " + d3.timeFormat("%y-%m-%d %I %p")(new Date(cluster.starting_time)) + "\nSummary:" + cluster.summarytweet)
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
    .scroll(function (x, scale) {})
    .display("circle")
    .background(d3.rgb("#EEEEEE"));

    let tlsvg = d3.select("#timelineBgnd").append("svg").attr("width", tlwidth)
    .datum(timeline_data).call(tlchart);
}

function change_data(loc,colorScale) {

    let data = storify_data[loc]

    document.getElementById("numTweets").textContent = data.num_tweets;

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

    renderGraph(data.graph)
    update_information(data)
    renderInformation(data)

}
