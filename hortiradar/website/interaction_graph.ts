// based on: https://bl.ocks.org/mbostock/2675ff61ea5e063ede2b5d63c08020c7, https://bl.ocks.org/mbostock/4e3925cdc804db257a86fdef3a032a45
// License:	GPL-3.0 (https://opensource.org/licenses/GPL-3.0)
import * as d3 from "d3";

declare const graph: any;

let svg = d3.select("svg");
let width = +svg.attr("width");
let height = +svg.attr("height");

let colorMap = {"retweet": "red", "mention": "green", "reply": "blue"};

svg.append("rect")
    .attr("width", width)
    .attr("height", height)
    .style("fill", "none")
    .style("pointer-events", "all")
    .call(d3.zoom()
          .scaleExtent([1 / 2, 4])
          .on("zoom", zoomed));

// build the arrow.
svg.append("svg:defs").selectAll("marker")
    .data(["end"])      // Different link/path types can be defined here
    .enter().append("svg:marker")    // This section adds in the arrows
    .attr("id", String)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 15)
    .attr("refY", -1.5)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("svg:path")
    .attr("d", "M0,-5L10,0L0,5");

let g = svg.append("g");

function zoomed() {
    g.attr("transform", d3.event.transform);
}

let simulation = d3.forceSimulation()
    .force("link", d3.forceLink().id(function(d) { return d.id; }))
    .force("charge", d3.forceManyBody().distanceMax(300))
    .force("center", d3.forceCenter(width / 2, height / 2));

let link = g.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(graph.edges)
    .enter().append("line")
    .attr("stroke", function(d) { return colorMap[d.value]; })
    .attr("marker-end", "url(#end)");

let node = g.append("g")
    .attr("class", "nodes")
    .selectAll("circle")
    .data(graph.nodes)
    .enter().append("circle")
    .attr("r", 2.5)
    .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));

let text = g.append("g")
    .attr("class", "labels")
    .selectAll("g")
    .data(graph.nodes)
    .enter().append("g");

text.append("text")
    .attr("x", 14)
    .attr("y", ".31em")
    .style("font-family", "sans-serif")
    .style("font-size", "0.7em")
    .text(function(d) { return d.id; });

node.append("title")            // mouseover
    .text(function(d) { return d.id; });

simulation
    .nodes(graph.nodes)
    .on("tick", ticked);

simulation.force("link")
    .links(graph.edges);

function ticked() {
    link
        .attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node
        .attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
    text
        .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
}

function dragstarted(d) {
    if (!d3.event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(d) {
    d.fx = d3.event.x;
    d.fy = d3.event.y;
}

function dragended(d) {
    if (!d3.event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}
