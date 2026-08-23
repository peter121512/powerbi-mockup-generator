/*
 * Premium Waterfall / Bridge Chart — Executive dark-theme waterfall visualization
 * Floating bars with connector lines, responsive sizing, and premium styling.
 * Designed for cash flow summaries, P&L bridges, and variance analysis.
 *
 * Data roles:
 *   category — labels (e.g. 'Opening', 'Operating CF', 'Investing CF', 'Financing CF', 'Closing')
 *   values   — numeric value for each category
 *
 * Bar type logic:
 *   - Contains 'opening' or 'start' (case insensitive) → anchor bar (starts at 0)
 *   - Contains 'closing' or 'total' or 'end' (case insensitive) → total bar (starts at 0)
 *   - Otherwise → change bar (floating, cumulative positioning)
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import * as d3 from "d3";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;

// === Design tokens (dark executive theme) ===
const BG_COLOR = "#151d2e";
const BORDER_COLOR = "#1e293b";
const POSITIVE_COLOR = "#34d399";
const NEGATIVE_COLOR = "#f87171";
const TOTAL_COLOR = "#3898ff";
const GRID_COLOR = "#1e293b";
const AXIS_COLOR = "#94a3b8";
const VALUE_LABEL_COLOR = "#e2e8f0";
const CONNECTOR_COLOR = "#475569";
const FONT_FAMILY = "'Segoe UI', sans-serif";

// Reference design dimensions (for scaling calculations)
const REF_WIDTH = 600;
const REF_HEIGHT = 300;

type BarType = "anchor" | "change" | "total";

interface WaterfallBar {
    category: string;
    value: number;
    type: BarType;
    start: number;   // y-start (bottom of bar)
    end: number;     // y-end (top of bar)
}

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    private defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    private chartGroup: d3.Selection<SVGGElement, unknown, null, undefined>;

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
            .attr("class", "premium-waterfall-chart")
            .style("width", "100%")
            .style("height", "100%");

        this.defs = this.svg.append("defs");
        this.chartGroup = this.svg.append("g").attr("class", "chart");
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const width = options.viewport.width;
            const height = options.viewport.height;

            this.svg.attr("width", width).attr("height", height);

            // Draw internal title
            this.svg.selectAll(".internal-title").remove();
            const titleText = this.getInternalTitle(options);
            if (titleText) {
                this.svg.append("text")
                    .attr("class", "internal-title")
                    .attr("x", 10)
                    .attr("y", 18)
                    .attr("font-family", "Segoe UI Semibold, sans-serif")
                    .attr("font-size", "12px")
                    .attr("fill", "#e2e8f0")
                    .text(titleText);
            }

            const dv = options.dataViews?.[0];
            if (!dv || !dv.categorical || !dv.categorical.categories || !dv.categorical.values) {
                this.chartGroup.selectAll("*").remove();
                this.events.renderingFinished(options);
                return;
            }

            const categorical = dv.categorical;
            const categories = categorical.categories[0].values.map(v => String(v));
            const values = categorical.values[0].values.map(v => Number(v) || 0);

            // Detect currency from format string
            const currency = this.detectCurrency(categorical.values[0]?.source?.format);

            // Build waterfall bar data
            const bars = this.computeWaterfallBars(categories, values);

            // Render
            this.render(width, height, bars, currency);
            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    /**
     * Determine bar type from category label
     */
    private getBarType(category: string): BarType {
        const lower = category.toLowerCase();
        if (lower.includes("opening") || lower.includes("start")) {
            return "anchor";
        }
        if (lower.includes("closing") || lower.includes("total") || lower.includes("end")) {
            return "total";
        }
        return "change";
    }

    /**
     * Compute waterfall bar positions using cumulative logic
     */
    /** Read title text from objects.general.title */
    private getInternalTitle(options: VisualUpdateOptions): string {
        const objects = options.dataViews?.[0]?.metadata?.objects;
        if (objects && objects["general"]) {
            const general = objects["general"] as any;
            if (general.title !== undefined) return String(general.title);
        }
        return "";
    }

    private computeWaterfallBars(categories: string[], values: number[]): WaterfallBar[] {
        const bars: WaterfallBar[] = [];
        let runningTotal = 0;

        for (let i = 0; i < categories.length; i++) {
            const category = categories[i];
            const value = values[i];
            const type = this.getBarType(category);

            if (type === "anchor") {
                // Anchor bar: starts at 0, goes to value
                bars.push({
                    category,
                    value,
                    type,
                    start: 0,
                    end: value,
                });
                runningTotal = value;
            } else if (type === "total") {
                // Total bar: starts at 0, goes to the running total (or the value if explicit)
                const totalValue = value !== 0 ? value : runningTotal;
                bars.push({
                    category,
                    value: totalValue,
                    type,
                    start: 0,
                    end: totalValue,
                });
            } else {
                // Change bar: floating from runningTotal
                const start = runningTotal;
                const end = runningTotal + value;
                bars.push({
                    category,
                    value,
                    type,
                    start,
                    end,
                });
                runningTotal = end;
            }
        }

        return bars;
    }

    /** Compute a scale factor relative to reference design size */
    private scaleFactor(width: number, height: number): number {
        const sw = width / REF_WIDTH;
        const sh = height / REF_HEIGHT;
        return Math.min(sw, sh);
    }

    private detectCurrency(format: string | undefined): string {
        if (!format) return "£";
        if (format.includes("$")) return "$";
        if (format.includes("€")) return "€";
        if (format.includes("¥")) return "¥";
        if (format.includes("£")) return "£";
        return "£";
    }

    private formatValue(value: number, currency: string): string {
        const abs = Math.abs(value);
        const sign = value < 0 ? "-" : "";
        if (abs >= 1_000_000_000) {
            return `${sign}${currency}${(abs / 1_000_000_000).toFixed(1)}B`;
        } else if (abs >= 1_000_000) {
            return `${sign}${currency}${(abs / 1_000_000).toFixed(1)}M`;
        } else if (abs >= 1_000) {
            return `${sign}${currency}${(abs / 1_000).toFixed(0)}K`;
        } else if (abs >= 1) {
            return `${sign}${currency}${abs.toFixed(0)}`;
        } else {
            return `${sign}${currency}${abs.toFixed(2)}`;
        }
    }

    private getBarColor(bar: WaterfallBar): string {
        if (bar.type === "anchor" || bar.type === "total") {
            return TOTAL_COLOR;
        }
        return bar.value >= 0 ? POSITIVE_COLOR : NEGATIVE_COLOR;
    }

    private render(width: number, height: number, bars: WaterfallBar[], currency: string): void {
        this.chartGroup.selectAll("*").remove();
        this.defs.selectAll("*").remove();

        const s = this.scaleFactor(width, height);

        // Responsive margins
        const margin = {
            top: Math.max(24, Math.min(40, 40 * s)),
            right: Math.max(12, Math.min(24, 24 * s)),
            bottom: Math.max(32, Math.min(52, 52 * s)),
            left: Math.max(44, Math.min(64, 64 * s)),
        };

        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        if (chartWidth <= 40 || chartHeight <= 40) return;

        this.chartGroup.attr("transform", `translate(${margin.left},${margin.top})`);

        // Responsive font sizes
        const axisFontSize = Math.max(8, Math.min(11, 11 * s));
        const valueFontSize = Math.max(7, Math.min(10, 10 * s));

        // Compute Y domain from bar start/end values
        const allYValues = bars.flatMap(b => [b.start, b.end]);
        const yMin = Math.min(0, d3.min(allYValues) || 0);
        const yMax = Math.max(0, d3.max(allYValues) || 0);
        const yPadding = (yMax - yMin) * 0.15;

        const yScale = d3.scaleLinear()
            .domain([yMin - yPadding, yMax + yPadding])
            .range([chartHeight, 0])
            .nice();

        // X scale — band scale for bars
        const xScale = d3.scaleBand()
            .domain(bars.map(b => b.category))
            .range([0, chartWidth])
            .padding(0.35);

        const barWidth = xScale.bandwidth();

        // Gridlines
        const numTicks = Math.max(3, Math.min(6, Math.floor(chartHeight / 50)));
        const yTicks = yScale.ticks(numTicks);

        this.chartGroup.selectAll(".grid-line")
            .data(yTicks).enter()
            .append("line")
            .attr("x1", 0)
            .attr("x2", chartWidth)
            .attr("y1", (d: number) => yScale(d))
            .attr("y2", (d: number) => yScale(d))
            .attr("stroke", GRID_COLOR)
            .attr("stroke-dasharray", "4,4")
            .attr("stroke-width", 1);

        // Zero baseline
        this.chartGroup.append("line")
            .attr("x1", 0)
            .attr("x2", chartWidth)
            .attr("y1", yScale(0))
            .attr("y2", yScale(0))
            .attr("stroke", AXIS_COLOR)
            .attr("stroke-width", 0.5)
            .attr("stroke-opacity", 0.4);

        // Connector lines between bars
        for (let i = 0; i < bars.length - 1; i++) {
            const currentBar = bars[i];
            const nextBar = bars[i + 1];

            // Connector goes from the end of current bar to the start of next bar
            const connectorY = currentBar.end;
            const x1 = (xScale(currentBar.category) || 0) + barWidth;
            const x2 = xScale(nextBar.category) || 0;

            this.chartGroup.append("line")
                .attr("x1", x1)
                .attr("x2", x2)
                .attr("y1", yScale(connectorY))
                .attr("y2", yScale(connectorY))
                .attr("stroke", CONNECTOR_COLOR)
                .attr("stroke-width", 1)
                .attr("stroke-dasharray", "3,3");
        }

        // Bars
        bars.forEach((bar) => {
            const x = xScale(bar.category) || 0;
            const yTop = yScale(Math.max(bar.start, bar.end));
            const yBottom = yScale(Math.min(bar.start, bar.end));
            const barHeight = Math.max(1, yBottom - yTop);
            const color = this.getBarColor(bar);
            const cornerRadius = Math.max(2, Math.min(4, 4 * s));

            // Bar rect
            this.chartGroup.append("rect")
                .attr("x", x)
                .attr("y", yTop)
                .attr("width", barWidth)
                .attr("height", barHeight)
                .attr("rx", cornerRadius)
                .attr("ry", cornerRadius)
                .attr("fill", color)
                .attr("fill-opacity", 0.85);

            // Subtle glow/border effect
            this.chartGroup.append("rect")
                .attr("x", x)
                .attr("y", yTop)
                .attr("width", barWidth)
                .attr("height", barHeight)
                .attr("rx", cornerRadius)
                .attr("ry", cornerRadius)
                .attr("fill", "none")
                .attr("stroke", color)
                .attr("stroke-width", 1)
                .attr("stroke-opacity", 0.5);

            // Value label above/below bar
            const labelY = bar.end >= bar.start
                ? yTop - Math.max(4, 6 * s)
                : yBottom + valueFontSize + Math.max(4, 6 * s);

            this.chartGroup.append("text")
                .attr("x", x + barWidth / 2)
                .attr("y", labelY)
                .attr("text-anchor", "middle")
                .attr("fill", VALUE_LABEL_COLOR)
                .attr("font-size", `${valueFontSize}px`)
                .attr("font-weight", "600")
                .attr("font-family", FONT_FAMILY)
                .text(this.formatValue(bar.value, currency));
        });

        // X-axis labels (category)
        this.chartGroup.append("g")
            .attr("transform", `translate(0,${chartHeight})`)
            .selectAll(".x-label")
            .data(bars)
            .enter()
            .append("text")
            .attr("x", (d: WaterfallBar) => (xScale(d.category) || 0) + barWidth / 2)
            .attr("y", Math.max(14, 20 * s))
            .attr("text-anchor", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", `${axisFontSize}px`)
            .attr("font-family", FONT_FAMILY)
            .text((d: WaterfallBar) => {
                // Truncate long labels if bar is narrow
                const maxChars = Math.max(4, Math.floor(barWidth / (axisFontSize * 0.5)));
                return d.category.length > maxChars
                    ? d.category.substring(0, maxChars - 1) + "…"
                    : d.category;
            });

        // Y-axis labels
        this.chartGroup.append("g")
            .selectAll(".y-label")
            .data(yTicks)
            .enter()
            .append("text")
            .attr("x", -Math.max(6, 10 * s))
            .attr("y", (d: number) => yScale(d))
            .attr("text-anchor", "end")
            .attr("dominant-baseline", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", `${axisFontSize}px`)
            .attr("font-family", FONT_FAMILY)
            .text((d: number) => this.formatValue(d, currency));
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
