import "es6-promise/auto";
import "whatwg-fetch";

const URLSearchParams = require("url-search-params");
const searchParams = new URLSearchParams(window.location.search);


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
            window.location.replace(window.location.origin + window.location.pathname + "?d=success");
        }
    });
}
document.getElementById("deleteButton").onclick = deleteKeywords;

if (searchParams.get("d") === "success") {
    let alert = document.getElementById("success");
    alert.textContent = "De geselecteerde trefwoorden zijn succesvol verwijderd.";
    alert.style.display = "block";
}

let lemma = document.getElementsByClassName("lemma-group")[0];
let newLemma = lemma.cloneNode(true);


function addForm() {
    let form = document.getElementById("lemmaForm");
    let addFormButton = document.getElementById("addFormButton");
    form.insertBefore(newLemma.cloneNode(true), addFormButton);
}
document.getElementById("addFormButton").onclick = addForm;


function addKeywords() {
    let data = [];
    let forms = document.getElementsByClassName("lemma-group");
    for (let form of forms) {
        let lemma = form.getElementsByClassName("lemma")[0].value;
        if (lemma.length > 0) {
            let woordsoort = form.getElementsByClassName("woordsoort")[0].value;
            data.push({"lemma": lemma, "pos": woordsoort});
        }
    }

    fetch(window.location.pathname, {
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({action: "add", keywords: data}),
    }).then(function (response) {
        return response.json();
    }).then(function (j) {
        if (j.status === "ok") {
            window.location.replace(window.location.origin + window.location.pathname + "?a=success");
        }
    });

}
document.getElementById("addKeywordsButton").onclick = addKeywords;


if (searchParams.get("a") === "success") {
    let alert = document.getElementById("success");
    alert.textContent = "De trefwoorden zijn succesvol toegevoegd.";
    alert.style.display = "block";
}
