/*
 * Premium Area Chart — Executive dark-theme area chart
 * Smooth gradient fills, subtle glow effects, and premium styling.
 *
 * Data roles:
 *   category — x-axis dimension (e.g. month numbers)
 *   values   — up to 3 measures plotted as area series
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import * as d3 from "d3";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;
import DataView = powerbi.DataView;

interface SeriesData {
    name: string;
    color: string;
    values: { category: string; value: number }[];
}

const SERIES_COLORS = ["#3898ff", "#a78bfa", "#34d399"];
const BG_COLOR = "#151d2e";
const BORDER_COLOR = "#1e293b";
const AXIS_COLOR = "#94a3b8";
const GRID_COLOR = "#1e293b";

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    private defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    private chartGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private legendGroup: d3.Selection<SVGGElement, unknown, null, undefined>;

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.container = options.element;
        this.container.style.overflow = "hidden";
        this.container.style.padding = "0";
        this.container.style.margin = "0";
        this.container.style.background = BG_COLOR;
        this.container.style.border = `1px solid ${BORDER_COLOR}`;
        this.container.style.borderRadius = "8px";
        this.container.style.boxSizing = "border-box";

        this.svg = d3.select(this.container)
            .append("svg")
            .attr("class", "premium-area-chart")
            .style("width", "100%")
            .style("height", "100%");

        this.defs = this.svg.append("defs");
        this.legendGroup = this.svg.append("g").attr("class", "legend");
        this.chartGroup = this.svg.append("g").attr("class", "chart");
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const width = options.viewport.width;
            const height = options.viewport.height;

            this.svg.attr("width", width).attr("height", height);

            const dv = options.dataViews?.[0];
            if (!dv || !dv.categorical || !dv.categorical.categories || !dv.categorical.values) {
                this.chartGroup.selectAll("*").remove();
                this.legendGroup.selectAll("*").remove();
                this.events.renderingFinished(options);
                return;
            }

            const categorical = dv.categorical;
            const categories = categorical.categories[0].values.map(v => String(v));
            const seriesDataArr: SeriesData[] = [];

            const numSeries = Math.min(categorical.values.length, 3);
            for (let i = 0; i < numSeries; i++) {
                const valueColumn = categorical.values[i];
                const seriesValues = valueColumn.values.map((v, idx) => ({
                    category: categories[idx],
                    value: Number(v) || 0
                }));
                seriesDataArr.push({
                    name: valueColumn.source.displayName || `Series ${i + 1}`,
                    color: SERIES_COLORS[i],
                    values: seriesValues
                });
            }

            // Detect currency from format string
            const currency = this.detectCurrency(categorical.values[0]?.source?.format);

            this.render(width, height, categories, seriesDataArr, currency);
            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    private detectCurrency(format: string | undefined): string {
        if (!format) return "£";
        if (format.includes("$")) return "$";
        if (format.includes("€")) return "€";
        if (format.includes("¥")) return "¥";
        if (format.includes("£")) return "£";
        return "£";
    }

    private formatYValue(value: number, currency: string): string {
        const abs = Math.abs(value);
        if (abs >= 1_000_000_000) {
            return `${currency}${(value / 1_000_000_000).toFixed(1)}B`;
        } else if (abs >= 1_000_000) {
            return `${currency}${(value / 1_000_000).toFixed(1)}M`;
        } else if (abs >= 1_000) {
            return `${currency}${(value / 1_000).toFixed(0)}K`;
        } else if (abs >= 1) {
            return `${currency}${value.toFixed(0)}`;
        } else {
            return `${currency}${value.toFixed(2)}`;
        }
    }

    private render(
        width: number,
        height: number,
        categories: string[],
        seriesData: SeriesData[],
        currency: string
    ): void {
        // Clear previous
        this.chartGroup.selectAll("*").remove();
        this.legendGroup.selectAll("*").remove();
        this.defs.selectAll("*").remove();

        // Margins
        const margin = {
            top: 36,
            right: 16,
            bottom: 32,
            left: 56
        };
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        if (chartWidth <= 0 || chartHeight <= 0) return;

        this.chartGroup.attr("transform", `translate(${margin.left},${margin.top})`);

        // Scales
        const xScale = d3.scalePoint<string>()
            .domain(categories)
            .range([0, chartWidth])
            .padding(0.1);

        const allValues = seriesData.flatMap(s => s.values.map(v => v.value));
        const yMin = Math.min(0, d3.min(allValues) || 0);
        const yMax = (d3.max(allValues) || 0) * 1.1;

        const yScale = d3.scaleLinear()
            .domain([yMin, yMax])
            .range([chartHeight, 0])
            .nice();

        // SVG glow filter
        const filter = this.defs.append("filter")
            .attr("id", "glow")
            .attr("x", "-20%")
            .attr("y", "-20%")
            .attr("width", "140%")
            .attr("height", "140%");
        filter.append("feGaussianBlur")
            .attr("stdDeviation", "3")
            .attr("result", "coloredBlur");
        const feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        // Gridlines (horizontal, dashed)
        const yTicks = yScale.ticks(5);
        this.chartGroup.selectAll(".grid-line")
            .data(yTicks)
            .enter()
            .append("line")
            .attr("class", "grid-line")
            .attr("x1", 0)
            .attr("x2", chartWidth)
            .attr("y1", d => yScale(d))
            .attr("y2", d => yScale(d))
            .attr("stroke", GRID_COLOR)
            .attr("stroke-dasharray", "4,4")
            .attr("stroke-width", 1);

        // Gradient definitions for each series
        seriesData.forEach((series, i) => {
            const gradId = `area-gradient-${i}`;
            const gradient = this.defs.append("linearGradient")
                .attr("id", gradId)
                .attr("x1", "0%")
                .attr("y1", "0%")
                .attr("x2", "0%")
                .attr("y2", "100%");
            gradient.append("stop")
                .attr("offset", "0%")
                .attr("stop-color", series.color)
                .attr("stop-opacity", 0.4);
            gradient.append("stop")
                .attr("offset", "100%")
                .attr("stop-color", series.color)
                .attr("stop-opacity", 0);
        });

        // Area generator
        const areaGen = d3.area<{ category: string; value: number }>()
            .x(d => xScale(d.category) || 0)
            .y0(chartHeight)
            .y1(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        // Line generator
        const lineGen = d3.line<{ category: string; value: number }>()
            .x(d => xScale(d.category) || 0)
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        // Draw areas and lines
        seriesData.forEach((series, i) => {
            // Area fill
            this.chartGroup.append("path")
                .datum(series.values)
                .attr("d", areaGen)
                .attr("fill", `url(#area-gradient-${i})`)
                .attr("stroke", "none");

            // Line with glow
            this.chartGroup.append("path")
                .datum(series.values)
                .attr("d", lineGen)
                .attr("fill", "none")
                .attr("stroke", series.color)
                .attr("stroke-width", 2)
                .attr("filter", "url(#glow)");
        });

        // X-axis labels
        const xAxisGroup = this.chartGroup.append("g")
            .attr("transform", `translate(0,${chartHeight})`);

        xAxisGroup.selectAll(".x-label")
            .data(categories)
            .enter()
            .append("text")
            .attr("class", "x-label")
            .attr("x", d => xScale(d) || 0)
            .attr("y", 18)
            .attr("text-anchor", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", "10px")
            .attr("font-family", "'Segoe UI', sans-serif")
            .text(d => d);

        // Y-axis labels
        const yAxisGroup = this.chartGroup.append("g");

        yAxisGroup.selectAll(".y-label")
            .data(yTicks)
            .enter()
            .append("text")
            .attr("class", "y-label")
            .attr("x", -8)
            .attr("y", d => yScale(d))
            .attr("text-anchor", "end")
            .attr("dominant-baseline", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", "10px")
            .attr("font-family", "'Segoe UI', sans-serif")
            .text(d => this.formatYValue(d, currency));

        // Legend at top-left
        this.legendGroup.attr("transform", `translate(${margin.left}, 12)`);

        seriesData.forEach((series, i) => {
            const legendItem = this.legendGroup.append("g")
                .attr("transform", `translate(${i * 110}, 0)`);

            legendItem.append("circle")
                .attr("cx", 5)
                .attr("cy", 5)
                .attr("r", 4)
                .attr("fill", series.color);

            legendItem.append("text")
                .attr("x", 14)
                .attr("y", 5)
                .attr("dominant-baseline", "middle")
                .attr("fill", AXIS_COLOR)
                .attr("font-size", "10px")
                .attr("font-family", "'Segoe UI', sans-serif")
                .text(series.name.length > 12 ? series.name.substring(0, 12) + "…" : series.name);
        });
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
