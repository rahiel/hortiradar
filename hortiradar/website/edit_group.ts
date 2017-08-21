import "es6-promise/auto";
import "whatwg-fetch";

const URLSearchParams = require("url-search-params");


function deleteKeywords() {
    let data = [];
    let keywords = document.getElementsByClassName("keyword");
    for (let keyword of keywords) {
        let checked = keyword.getElementsByClassName("delete")[0].checked;
        if (checked) {
            let lemma = keyword.getElementsByClassName("lemma")[0].textContent;
            let pos = keyword.getElementsByClassName("pos")[0].textContent;
            data.push({"lemma": lemma, "pos": pos});
        }
    }

    fetch(window.location.pathname, {
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({action: "delete", keywords: data}),
    }).then(function (response) {
        return response.json();
    }).then(function (j) {
        if (j.status === "ok") {
            window.location.replace(window.location.origin + window.location.pathname + "?m=success");
        }
    });
}


const searchParams = new URLSearchParams(window.location.search);
if (searchParams.get("m") === "success") {
    let alert = document.getElementById("success")
    alert.textContent = "De geselecteerde trefwoorden zijn succesvol verwijderd."
    alert.style.display = "block";
}

document.getElementById("deleteButton").onclick = deleteKeywords;
