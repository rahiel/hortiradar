import { renderChart } from "./home";


declare const data: any;
declare const max_amount, group: string;

renderChart(data, "chartContainer", `Top ${max_amount} ${group}`);
