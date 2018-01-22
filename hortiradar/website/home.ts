declare const APP_ROOT: string;
declare const bloemen: any;
declare const groente_en_fruit: any;


export function renderChart(data: any, chartContainer: string, title: string) {
    let chart = new CanvasJS.Chart(chartContainer, {
        theme: "theme2",
        title: {
            text: title
        },
        animationEnabled: true,
        data: [{
            type: "column",
            dataPoints: data,
            click: onClick
        }],
        axisX: {
            labelFontSize: 19
        },
        axisY:{
            valueFormatString: "##%",
            labelFontSize: 20,
        }
    });
    chart.render();
}

window.onload = function () {
    if (typeof groente_en_fruit === "undefined" || typeof bloemen === "undefined") {
    	  return;
    }
    renderChart(groente_en_fruit, "chartContainer_fruit", "Top 10 Groente en Fruit");
    renderChart(bloemen, "chartContainer_flower", "Top 10 Bloemen en Planten");
};

function onClick(e) {
    window.open(APP_ROOT + "keywords/" + e.dataPoint.label);
}
