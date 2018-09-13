import * as $ from "jquery";
import * as d3 from "d3";
import * as _ from "lodash";

declare const APP_ROOT: string;
declare const peaks: any;
declare const num_peaks: number;
declare const text_dt: string;


if (typeof peaks !== "undefined") {
    window.onload = function () { main(); };
}


function dateToString(date) {
    // this function was copied with permission from the author from: https://github.com/rahiel/archiveror/blob/aef7d9afe7ac5612bd4f8f27a42694fa33e9649c/src/utils.js#L56
    let y = date.getUTCFullYear();
    let m = (date.getUTCMonth() + 1).toString().padStart(2, "0");
    let d = date.getUTCDate().toString().padStart(2, "0");
    let H = date.getUTCHours().toString().padStart(2, "0");
    let M = date.getUTCMinutes().toString().padStart(2, "0");
    let timestamp = `${y}-${m}-${d}T${H}:${M}`;
    return timestamp;
}


function main() {

    let colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    // Add tooltip div
    let infobox = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 1e-6);

    // TODO: instead of tooltip, set Wikipedia summary and maybe in the future Google results in a modal!

    for (let j = 0; j < peaks.length; j++){
        renderPeak(j,peaks[j][0],peaks[j][1],colorScale(j % 10));
    }

}

function renderPeak(loc, kw, data, color) {
    let title = d3.select("#title"+loc).text(kw);

    const format = d3.format(",d")

    let test = d3.select("div#treemapContainer"+loc).node();
    let width = test.getBoundingClientRect().width;
    let height = test.getBoundingClientRect().height;

    let treemap = d3.treemap()
        .tile(d3.treemapResquarify)
        .size([width, height])
        .round(true)
        .paddingInner(1);

    let root = d3.hierarchy(data["treemap"])
        .eachBefore(function(d) { d.data.id = (d.parent ? d.parent.data.id + "." : "") + d.data.name; })
        .sum(sumBySize)
        .sort(function(a, b) { return b.height - a.height || b.value - a.value; });

    treemap(root);

    let svg = d3.select("svg#treemap"+loc)
        svg.attr("width",width)
        svg.attr("heigt",height)

    let cell = svg.selectAll("g")
        .data(root.leaves())
        .enter().append("g")
            .attr("transform", function(d) { return "translate(" + d.x0 + "," + d.y0 + ")"; });

    cell.append("rect")
        .attr("id", function(d) { return d.data.id; })
        .attr("width", function(d) { return d.x1 - d.x0; })
        .attr("height", function(d) { return d.y1 - d.y0; })
        .attr("fill", color);

    cell.append("clipPath")
        .attr("id", function(d) { return "clip-" + d.data.id; })
            .append("use")
            .attr("xlink:href", function(d) { return "#" + d.data.id; });

    cell.append("text")
        .attr("clip-path", function(d) { return "url(#clip-" + d.data.id + ")"; })
        .selectAll("tspan")
        .data(function(d) { return d.data.name.split(/(?=[A-Z][^A-Z])/g); })
        .enter().append("tspan")
        .attr("x", 4)
        .attr("y", function(d, i) { return 13 + i * 10; })
        .text(function(d) { return d; });

    cell.append("title")
        .text(function(d) { return d.data.id + "\n" + format(d.value); });

    cell.on("click", atClick);

    let timeSeries = [];
    for (let i = 0; i < data["actual"].length; i++) {
        let p = data["actual"][i];
        let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        };
        timeSeries.push(point);
    }

    let p = data["actual"][data["actual"].length-1];
    let stripLineDate = new Date(Date.UTC(p.year, p.month-1, p.day, p.hour))
    let endPoint = [{
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        }];


    let timeSeries2 = [];
    let timeSeries3 = [];
    for (let i = 0; i < data["circadian"].length; i++) {
        let p = data["circadian"][i];
        let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: p.count
        };
        timeSeries2.push(point);
        if (i >= data["actual"].length-1) {
          let point = {
            x: new Date(Date.UTC(p.year, p.month-1, p.day, p.hour)),
            y: data["threshold"][i].count
          };
          timeSeries3.push(point);
        }
    }

    let chart = new CanvasJS.Chart("splineContainer"+loc, {
        title: {text: ""},
        animationEnabled: true,
        axisX: {
            valueFormatString: "HH:00 D-M-YYYY",
            interval: 12,
            intervalType: "hour",
            stripLines: [{
              value: stripLineDate,
              lineDashType: "dash",
              color: "#CCCCCC"
            }],
            labelAngle: 50
        },
        axisY : {
            title: "Aantal tweets"
        },
        toolTip : {
            shared: true
        },
        data: [{
            name: "Hortiradar ("+kw+")",
            type: "line",
            markerType: null,
            dataPoints: timeSeries,
            color: color,
            click: onClickSpline
        },{
            name: "Daily rhythm ("+kw+")",
            type: "line",
            lineDashType: "dash",
            markerType: null,
            dataPoints: timeSeries2,
            color: color,
        },{
            name: "Threshold ("+kw+")",
            type: "line",
            markerType: null,
            lineDashType: "dash",
            dataPoints: timeSeries3,
            color: "#000000",
        }]
    });
    chart.render();

    function onClickSpline(e,kw) {
        let start = dateToString(e.dataPoint.x)
        window.open(APP_ROOT + "keywords/" + kw + "?start=" + start + "&period=hour");
    }

}

function sumBySize(d) {
    return d.size;
}

var infobox = d3.select("body").append("div")
    .attr("class", "tooltip")
    .style("opacity", 1e-6);

function atClick(d) {
    if (d.data.summary !== "") {
        infobox
        .html(d.data.summary)
        .style("left", (d3.event.pageX ) + "px")
        .style("top", (d3.event.pageY) + "px");

        infobox
        .transition()
        .duration(100)
        .style("opacity",1);
    } else {
        infobox.transition()
        .style("opacity",1e-6);
    }
}
