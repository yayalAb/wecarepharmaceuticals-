/** @odoo-module **/

import { Component, onWillStart, useRef, onMounted, onPatched, onWillUnmount } from "@odoo/owl";
import { loadJS } from "@web/core/assets";

export class ChartRenderer extends Component {
    static template = "wecare_executive_dashboard.ChartRenderer";

    static props = {
        type: String,
        data: Object,
        options: { type: Object, optional: true },
        height: { type: Number, optional: true },
        title: { type: String, optional: true },
        x_title: { type: String, optional: true },
        y_title: { type: String, optional: true },
        onChartClick: { type: Function, optional: true },
    };

    setup() {
        this.chartRef = useRef("chartCanvas");
        this.chartInstance = null;

        onWillStart(async () => {
            if (!window.Chart) {
                try {
                    await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js");
                } catch (e) {
                    console.warn("Could not load external Chart.js CDN, trying fallback:", e);
                }
            }
        });

        onMounted(() => this.renderChart());
        onPatched(() => this.renderChart());
        onWillUnmount(() => this.destroyChart());
    }

    destroyChart() {
        if (this.chartInstance) {
            this.chartInstance.destroy();
            this.chartInstance = null;
        }
    }

    renderChart() {
        this.destroyChart();
        if (!this.chartRef.el || !window.Chart) {
            return;
        }
        if (!this.props.data || !this.props.data.labels || !this.props.data.datasets || !this.props.data.datasets.length) {
            return;
        }

        const ctx = this.chartRef.el.getContext("2d");
        const isDoughnut = this.props.type === "doughnut";
        const isCircular = ["pie", "doughnut"].includes(this.props.type);

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: !!this.props.title,
                    text: this.props.title || "",
                    font: { size: 13, weight: "600" },
                    color: "#0f172a",
                },
                legend: {
                    display: !isDoughnut,
                    position: "top",
                    labels: {
                        boxWidth: 12,
                        font: { size: 11 },
                    },
                },
                tooltip: {
                    enabled: true,
                    backgroundColor: "#0f172a",
                    titleFont: { size: 12 },
                    bodyFont: { size: 12 },
                    padding: 10,
                    cornerRadius: 8,
                },
            },
        };

        if (isDoughnut) {
            defaultOptions.cutout = "72%";
        }

        if (!isCircular) {
            defaultOptions.scales = {
                y: {
                    beginAtZero: true,
                    title: { display: !!this.props.y_title, text: this.props.y_title || "", font: { size: 11 } },
                    grid: { color: "rgba(0, 0, 0, 0.04)" },
                    ticks: { font: { size: 11 } },
                },
                x: {
                    title: { display: !!this.props.x_title, text: this.props.x_title || "", font: { size: 11 } },
                    grid: { display: false },
                    ticks: { font: { size: 11 } },
                },
            };
        }

        const mergedOptions = Object.assign({}, defaultOptions, this.props.options || {});

        this.chartInstance = new window.Chart(ctx, {
            type: this.props.type,
            data: this.props.data,
            options: mergedOptions,
        });
    }
}
