import * as $ from "jquery";
import { showLink } from "./keyword";

const URLSearchParams = require("url-search-params");

declare const APP_ROOT: string;
declare const news: any;
const searchParams = new URLSearchParams(window.location.search);


window.onload = function () { main(); };

function main() {
    $("body").scrollspy({ target: "#toc" });
    showLink();

    // navigate to fragment identifier
    let hash = searchParams.get("hash");
    if (hash != null) {
        window.location.hash = hash;
    }
}