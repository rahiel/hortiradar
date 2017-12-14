require("waypoints/lib/noframework.waypoints.min");
declare const Waypoint: any;

declare const tweets: string[];
declare const retweets: string[];

let container = document.getElementById("container");
let renderedTweets = 0;


function renderTweets(n) {
    for (let i = 0; i < n; i++) {
        let tweetDiv = document.createElement("div");
        twttr.widgets.createTweet(tweets[renderedTweets + i], tweetDiv, {
            theme: "light",
            lang: "nl",
            align: "center",
            dnt: true,
        });
        container.appendChild(tweetDiv);
    }
    renderedTweets += n;
}

function render() {
    renderTweets(Math.min(14, tweets.length - renderedTweets));
    if (renderedTweets >= tweets.length) {
        document.getElementById("bottom").innerText = "Alles Geladen";
        waypoint.destroy();
    }
}

let waypoint = new Waypoint({
    element: document.getElementById("bottom"),
    offset: "bottom-in-view",
    handler: function() {
        render();
    }
})
