/*
 * Premium Area Chart — Executive dark-theme area chart
 * Smooth gradient fills, subtle glow effects, and premium styling.
 * Includes internal Monthly/Quarterly/Annual toggle buttons.
 *
 * Data roles:
 *   category — x-axis dimension (e.g. month numbers 1-12)
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

interface SeriesData {
    name: string;
    color: string;
    values: { category: string; value: number }[];
}

type Granularity = "Monthly" | "Quarterly" | "Annual";

const SERIES_COLORS = ["#3898ff", "#a78bfa", "#34d399"];
const BG_COLOR = "#151d2e";
const BORDER_COLOR = "#1e293b";
const AXIS_COLOR = "#94a3b8";
const GRID_COLOR = "#1e293b";
const ACTIVE_BTN = "#3898ff";
const INACTIVE_BTN = "#1e293b";
const INACTIVE_BORDER = "#334155";

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    private defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    private chartGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private legendGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private toggleGroup: d3.Selection<SVGGElement, unknown, null, undefined>;

    private currentGranularity: Granularity = "Monthly";
    private lastOptions: VisualUpdateOptions | null = null;

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
        this.toggleGroup = this.svg.append("g").attr("class", "toggle");
        this.legendGroup = this.svg.append("g").attr("class", "legend");
        this.chartGroup = this.svg.append("g").attr("class", "chart");
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);
        this.lastOptions = options;

        try {
            const width = options.viewport.width;
            const height = options.viewport.height;

            this.svg.attr("width", width).attr("height", height);

            const dv = options.dataViews?.[0];
            if (!dv || !dv.categorical || !dv.categorical.categories || !dv.categorical.values) {
                this.chartGroup.selectAll("*").remove();
                this.legendGroup.selectAll("*").remove();
                this.toggleGroup.selectAll("*").remove();
                this.events.renderingFinished(options);
                return;
            }

            const categorical = dv.categorical;
            const categories = categorical.categories[0].values.map(v => String(v));
            const rawSeries: SeriesData[] = [];

            const numSeries = Math.min(categorical.values.length, 3);
            for (let i = 0; i < numSeries; i++) {
                const valueColumn = categorical.values[i];
                const seriesValues = valueColumn.values.map((v, idx) => ({
                    category: categories[idx],
                    value: Number(v) || 0
                }));
                rawSeries.push({
                    name: valueColumn.source.displayName || `Series ${i + 1}`,
                    color: SERIES_COLORS[i],
                    values: seriesValues
                });
            }

            // Aggregate based on current granularity
            const aggregatedSeries = this.aggregateData(rawSeries, this.currentGranularity);
            const aggregatedCategories = aggregatedSeries.length > 0
                ? aggregatedSeries[0].values.map(v => v.category)
                : [];

            // Detect currency
            const currency = this.detectCurrency(categorical.values[0]?.source?.format);

            // Render toggle buttons
            this.renderToggle(width);

            // Render chart
            this.render(width, height, aggregatedCategories, aggregatedSeries, currency);
            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    private aggregateData(rawSeries: SeriesData[], granularity: Granularity): SeriesData[] {
        if (granularity === "Monthly") {
            return rawSeries; // No aggregation needed
        }

        return rawSeries.map(series => {
            const grouped = new Map<string, number>();

            series.values.forEach(point => {
                const monthNum = parseInt(point.category, 10);
                let key: string;

                if (granularity === "Quarterly") {
                    if (!isNaN(monthNum) && monthNum >= 1 && monthNum <= 12) {
                        const quarter = Math.ceil(monthNum / 3);
                        key = `Q${quarter}`;
                    } else {
                        key = point.category;
                    }
                } else {
                    // Annual — sum everything into one point
                    key = "Total";
                }

                grouped.set(key, (grouped.get(key) || 0) + point.value);
            });

            const values: { category: string; value: number }[] = [];
            grouped.forEach((value, category) => {
                values.push({ category, value });
            });

            // Sort quarters
            if (granularity === "Quarterly") {
                values.sort((a, b) => {
                    const qa = parseInt(a.category.replace("Q", ""), 10);
                    const qb = parseInt(b.category.replace("Q", ""), 10);
                    return qa - qb;
                });
            }

            return { name: series.name, color: series.color, values };
        });
    }

    private renderToggle(width: number): void {
        this.toggleGroup.selectAll("*").remove();

        const labels: Granularity[] = ["Monthly", "Quarterly", "Annual"];
        const btnWidth = 68;
        const btnHeight = 22;
        const btnGap = 4;
        const totalWidth = labels.length * btnWidth + (labels.length - 1) * btnGap;
        const startX = width - totalWidth - 16;
        const startY = 8;

        labels.forEach((label, i) => {
            const x = startX + i * (btnWidth + btnGap);
            const isActive = label === this.currentGranularity;

            const g = this.toggleGroup.append("g")
                .attr("class", "toggle-btn")
                .style("cursor", "pointer")
                .on("click", () => {
                    this.currentGranularity = label;
                    if (this.lastOptions) {
                        this.update(this.lastOptions);
                    }
                });

            // Button background
            g.append("rect")
                .attr("x", x)
                .attr("y", startY)
                .attr("width", btnWidth)
                .attr("height", btnHeight)
                .attr("rx", 4)
                .attr("ry", 4)
                .attr("fill", isActive ? ACTIVE_BTN : INACTIVE_BTN)
                .attr("stroke", isActive ? ACTIVE_BTN : INACTIVE_BORDER)
                .attr("stroke-width", 1);

            // Button text
            g.append("text")
                .attr("x", x + btnWidth / 2)
                .attr("y", startY + btnHeight / 2)
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "central")
                .attr("fill", isActive ? "#ffffff" : AXIS_COLOR)
                .attr("font-size", "9px")
                .attr("font-weight", "600")
                .attr("font-family", "'Segoe UI', sans-serif")
                .text(label);
        });
    }

    private detectCurrency(format: string | undefined): string {
        if (!format) return "£";
        if (format.includes("$")) return "$";
        if (format.includes("€")) return "€";
        if (format.includes("¥")) return "¥";
        if (format.includes("£")) return "£";
        return "£";
    }

    private readonly MONTH_ABBR: string[] = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];

    private formatCategory(value: string): string {
        const num = parseInt(value, 10);
        if (!isNaN(num) && num >= 1 && num <= 12 && this.currentGranularity === "Monthly") {
            return this.MONTH_ABBR[num - 1];
        }
        return value;
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
        this.chartGroup.selectAll("*").remove();
        this.legendGroup.selectAll("*").remove();
        this.defs.selectAll("*").remove();

        const margin = { top: 42, right: 16, bottom: 32, left: 56 };
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
            .attr("x", "-20%").attr("y", "-20%")
            .attr("width", "140%").attr("height", "140%");
        filter.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
        const feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        // Gridlines
        const yTicks = yScale.ticks(5);
        this.chartGroup.selectAll(".grid-line")
            .data(yTicks).enter()
            .append("line")
            .attr("x1", 0).attr("x2", chartWidth)
            .attr("y1", d => yScale(d)).attr("y2", d => yScale(d))
            .attr("stroke", GRID_COLOR)
            .attr("stroke-dasharray", "4,4")
            .attr("stroke-width", 1);

        // Gradients
        seriesData.forEach((series, i) => {
            const gradient = this.defs.append("linearGradient")
                .attr("id", `area-gradient-${i}`)
                .attr("x1", "0%").attr("y1", "0%")
                .attr("x2", "0%").attr("y2", "100%");
            gradient.append("stop").attr("offset", "0%")
                .attr("stop-color", series.color).attr("stop-opacity", 0.4);
            gradient.append("stop").attr("offset", "100%")
                .attr("stop-color", series.color).attr("stop-opacity", 0);
        });

        // Generators
        const areaGen = d3.area<{ category: string; value: number }>()
            .x(d => xScale(d.category) || 0)
            .y0(chartHeight)
            .y1(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        const lineGen = d3.line<{ category: string; value: number }>()
            .x(d => xScale(d.category) || 0)
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX);

        // Draw areas and lines
        seriesData.forEach((series, i) => {
            this.chartGroup.append("path")
                .datum(series.values)
                .attr("d", areaGen)
                .attr("fill", `url(#area-gradient-${i})`)
                .attr("stroke", "none");

            this.chartGroup.append("path")
                .datum(series.values)
                .attr("d", lineGen)
                .attr("fill", "none")
                .attr("stroke", series.color)
                .attr("stroke-width", 2)
                .attr("filter", "url(#glow)");
        });

        // X-axis labels
        this.chartGroup.append("g")
            .attr("transform", `translate(0,${chartHeight})`)
            .selectAll(".x-label")
            .data(categories).enter()
            .append("text")
            .attr("x", d => xScale(d) || 0)
            .attr("y", 18)
            .attr("text-anchor", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", "10px")
            .attr("font-family", "'Segoe UI', sans-serif")
            .text(d => this.formatCategory(d));

        // Y-axis labels
        this.chartGroup.append("g")
            .selectAll(".y-label")
            .data(yTicks).enter()
            .append("text")
            .attr("x", -8)
            .attr("y", d => yScale(d))
            .attr("text-anchor", "end")
            .attr("dominant-baseline", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", "10px")
            .attr("font-family", "'Segoe UI', sans-serif")
            .text(d => this.formatYValue(d, currency));

        // Legend
        this.legendGroup.attr("transform", `translate(${margin.left}, 14)`);
        seriesData.forEach((series, i) => {
            const legendItem = this.legendGroup.append("g")
                .attr("transform", `translate(${i * 120}, 0)`);
            legendItem.append("circle")
                .attr("cx", 5).attr("cy", 5).attr("r", 4)
                .attr("fill", series.color);
            legendItem.append("text")
                .attr("x", 14).attr("y", 5)
                .attr("dominant-baseline", "middle")
                .attr("fill", AXIS_COLOR)
                .attr("font-size", "10px")
                .attr("font-family", "'Segoe UI', sans-serif")
                .text(series.name.length > 14 ? series.name.substring(0, 14) + "…" : series.name);
        });

        // ===== TOOLTIP =====
        const tooltipLine = this.chartGroup.append("line")
            .attr("y1", 0).attr("y2", chartHeight)
            .attr("stroke", "#475569").attr("stroke-width", 1)
            .attr("stroke-dasharray", "4,2")
            .style("opacity", 0).style("pointer-events", "none");

        const tooltipGroup = this.chartGroup.append("g")
            .style("opacity", 0).style("pointer-events", "none");

        const tooltipBg = tooltipGroup.append("rect")
            .attr("rx", 4).attr("ry", 4)
            .attr("fill", "#1e293b").attr("stroke", "#334155").attr("stroke-width", 1);

        const tooltipDots = seriesData.map(series =>
            this.chartGroup.append("circle")
                .attr("r", 4).attr("fill", series.color)
                .attr("stroke", "#fff").attr("stroke-width", 1.5)
                .style("opacity", 0).style("pointer-events", "none")
        );

        const self = this;
        this.chartGroup.append("rect")
            .attr("width", chartWidth).attr("height", chartHeight)
            .attr("fill", "transparent")
            .style("cursor", "crosshair")
            .on("mousemove", function(event: MouseEvent) {
                const [mx] = d3.pointer(event, this);
                const domain = xScale.domain();
                let nearestIdx = 0;
                let nearestDist = Infinity;
                domain.forEach((cat, idx) => {
                    const dist = Math.abs(mx - (xScale(cat) || 0));
                    if (dist < nearestDist) { nearestDist = dist; nearestIdx = idx; }
                });

                const nearestCat = domain[nearestIdx];
                const nearestX = xScale(nearestCat) || 0;

                tooltipLine.attr("x1", nearestX).attr("x2", nearestX).style("opacity", 1);

                const lineHeight = 14;
                const boxWidth = 140;
                const boxHeight = (seriesData.length + 1) * lineHeight + 10;
                let tipX = nearestX + 12;
                if (tipX + boxWidth > chartWidth) tipX = nearestX - boxWidth - 12;
                const tipY = 20;

                tooltipBg.attr("x", tipX).attr("y", tipY).attr("width", boxWidth).attr("height", boxHeight);
                tooltipGroup.selectAll("text").remove();

                const catLabel = self.formatCategory(nearestCat);
                tooltipGroup.append("text")
                    .attr("x", tipX + 8).attr("y", tipY + 14)
                    .attr("fill", "#e2e8f0").attr("font-size", "9px")
                    .attr("font-weight", "bold").attr("font-family", "'Segoe UI', sans-serif")
                    .text(catLabel);

                seriesData.forEach((series, si) => {
                    const val = series.values[nearestIdx]?.value || 0;
                    const cy = yScale(val);
                    tooltipDots[si].attr("cx", nearestX).attr("cy", cy).style("opacity", 1);
                    tooltipGroup.append("text")
                        .attr("x", tipX + 8).attr("y", tipY + 14 + (si + 1) * lineHeight)
                        .attr("fill", series.color).attr("font-size", "9px")
                        .attr("font-family", "'Segoe UI', sans-serif")
                        .text(`${series.name}: ${self.formatYValue(val, currency)}`);
                });

                tooltipGroup.style("opacity", 1);
            })
            .on("mouseleave", function() {
                tooltipLine.style("opacity", 0);
                tooltipGroup.style("opacity", 0);
                tooltipDots.forEach(d => d.style("opacity", 0));
            });
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
