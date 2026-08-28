/*
 * Premium Area Chart — Executive dark-theme area chart
 * Smooth gradient fills, subtle glow effects, and premium styling.
 * Includes internal Monthly/Quarterly/Annual toggle buttons.
 * Fully responsive — all margins, fonts, toggles, and legend scale with viewport.
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

interface DataPoint {
    year: number;
    month: number;
    quarter: number;
    values: number[];
}

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

// Reference design dimensions (for scaling calculations)
const REF_WIDTH = 640;
const REF_HEIGHT = 240;

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    private defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    private chartGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private legendGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private toggleGroup: d3.Selection<SVGGElement, unknown, null, undefined>;

    private rawData: DataPoint[] = [];
    private seriesNames: string[] = [];
    private currentGranularity: Granularity = "Monthly";
    private lastOptions: VisualUpdateOptions | null = null;
    private currentTitle: string = "";

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

            // Draw internal title (reads from objects.general.title)
            this.svg.selectAll(".internal-title").remove();
            const titleText = this.getInternalTitle(options);
            this.currentTitle = titleText || "";
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
                this.legendGroup.selectAll("*").remove();
                this.toggleGroup.selectAll("*").remove();
                this.events.renderingFinished(options);
                return;
            }

            const categorical = dv.categorical;

            // Parse categories - may be hierarchical (Year + Month) or single (Month)
            let years: number[] = [];
            let months: number[] = [];
            const numRows = categorical.categories[0].values.length;

            if (categorical.categories.length >= 2) {
                // Hierarchical: first is Year, second is Month
                years = categorical.categories[0].values.map(v => Number(v));
                months = categorical.categories[1].values.map(v => Number(v));
            } else {
                // Single category - assume months, no year info
                months = categorical.categories[0].values.map(v => Number(v));
                years = months.map(() => 0); // unknown year
            }

            // Parse values
            const numSeries = Math.min(categorical.values.length, 3);
            this.seriesNames = [];
            this.rawData = [];

            for (let i = 0; i < numSeries; i++) {
                this.seriesNames.push(categorical.values[i].source.displayName || `Series ${i + 1}`);
            }

            for (let row = 0; row < numRows; row++) {
                const dp: DataPoint = {
                    year: years[row],
                    month: months[row],
                    quarter: Math.ceil(months[row] / 3),
                    values: [],
                };
                for (let i = 0; i < numSeries; i++) {
                    dp.values.push(Number(categorical.values[i].values[row]) || 0);
                }
                this.rawData.push(dp);
            }

            // Sort by year then month
            this.rawData.sort((a, b) => a.year !== b.year ? a.year - b.year : a.month - b.month);

            // Detect currency
            const currency = this.detectCurrency(categorical.values[0]?.source?.format);

            // Render toggle buttons
            this.renderToggle(width, height);

            // Aggregate and render
            this.renderAggregated(width, height, currency);
            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    /** Read title text from objects.general.title */
    private getInternalTitle(options: VisualUpdateOptions): string {
        const objects = options.dataViews?.[0]?.metadata?.objects;
        if (objects && objects["general"]) {
            const general = objects["general"] as any;
            if (general.title !== undefined) return String(general.title);
        }
        return "";
    }

    /** Compute a scale factor relative to reference design size */
    private scaleFactor(width: number, height: number): number {
        const sw = width / REF_WIDTH;
        const sh = height / REF_HEIGHT;
        return Math.min(sw, sh);
    }

    /** Scale a pixel value proportionally, clamped between min and max */
    private scaled(baseValue: number, width: number, height: number, min?: number, max?: number): number {
        const s = this.scaleFactor(width, height);
        const v = baseValue * s;
        if (min !== undefined && v < min) return min;
        if (max !== undefined && v > max) return max;
        return v;
    }

    private renderAggregated(width: number, height: number, currency: string): void {
        // Aggregate based on granularity
        const grouped = new Map<string, number[]>();
        const sortKeys: string[] = [];

        this.rawData.forEach(dp => {
            let key: string;
            let sortKey: string;

            if (this.currentGranularity === "Monthly") {
                const monthAbbr = this.MONTH_ABBR[(dp.month - 1)] || String(dp.month);
                if (dp.year > 0) {
                    const yearShort = String(dp.year).slice(-2);
                    key = `${monthAbbr} '${yearShort}`;
                    sortKey = `${dp.year}-${String(dp.month).padStart(2, "0")}`;
                } else {
                    key = monthAbbr;
                    sortKey = String(dp.month).padStart(2, "0");
                }
            } else if (this.currentGranularity === "Quarterly") {
                if (dp.year > 0) {
                    key = `Q${dp.quarter} '${String(dp.year).slice(-2)}`;
                    sortKey = `${dp.year}-Q${dp.quarter}`;
                } else {
                    key = `Q${dp.quarter}`;
                    sortKey = `Q${dp.quarter}`;
                }
            } else {
                // Annual
                key = dp.year > 0 ? String(dp.year) : "Total";
                sortKey = String(dp.year);
            }

            if (!grouped.has(key)) {
                grouped.set(key, new Array(this.seriesNames.length).fill(0));
                sortKeys.push(sortKey + "|" + key);
            }
            const vals = grouped.get(key)!;
            dp.values.forEach((v, i) => { vals[i] += v; });
        });

        // Sort by sortKey
        sortKeys.sort();
        const categories: string[] = sortKeys.map(sk => sk.split("|")[1]);

        // Build series data
        const seriesData: SeriesData[] = this.seriesNames.map((name, i) => ({
            name,
            color: SERIES_COLORS[i],
            values: categories.map(cat => ({ category: cat, value: grouped.get(cat)![i] })),
        }));

        this.render(width, height, categories, seriesData, currency);
    }

    private renderToggle(width: number, height: number): void {
        this.toggleGroup.selectAll("*").remove();

        const s = this.scaleFactor(width, height);
        const labels: Granularity[] = ["Monthly", "Quarterly", "Annual"];

        // Scale toggle button dimensions
        const btnWidth = Math.max(40, Math.min(68, 68 * s));
        const btnHeight = Math.max(16, Math.min(22, 22 * s));
        const btnGap = Math.max(2, 4 * s);
        const fontSize = Math.max(7, Math.min(9, 9 * s));
        const totalWidth = labels.length * btnWidth + (labels.length - 1) * btnGap;
        const rightPadding = Math.max(8, 16 * s);
        const topPadding = Math.max(4, 8 * s);
        const startX = width - totalWidth - rightPadding;
        const startY = topPadding;

        // Hide toggles entirely if viewport too small
        if (width < 200) return;

        labels.forEach((label, i) => {
            const x = startX + i * (btnWidth + btnGap);
            const isActive = label === this.currentGranularity;

            const g = this.toggleGroup.append("g")
                .attr("class", "toggle-btn")
                .style("cursor", "pointer")
                .on("click", () => {
                    this.currentGranularity = label;
                    if (this.lastOptions) {
                        const w = this.lastOptions.viewport.width;
                        const h = this.lastOptions.viewport.height;
                        const currency = this.detectCurrency(
                            this.lastOptions.dataViews?.[0]?.categorical?.values?.[0]?.source?.format
                        );
                        this.renderToggle(w, h);
                        this.renderAggregated(w, h, currency);
                    }
                });

            // Button background
            g.append("rect")
                .attr("x", x)
                .attr("y", startY)
                .attr("width", btnWidth)
                .attr("height", btnHeight)
                .attr("rx", Math.min(4, 4 * s))
                .attr("ry", Math.min(4, 4 * s))
                .attr("fill", isActive ? ACTIVE_BTN : INACTIVE_BTN)
                .attr("stroke", isActive ? ACTIVE_BTN : INACTIVE_BORDER)
                .attr("stroke-width", 1);

            // Button text — use shorter labels at small sizes
            const displayLabel = btnWidth < 50 ? label.charAt(0) : label;
            g.append("text")
                .attr("x", x + btnWidth / 2)
                .attr("y", startY + btnHeight / 2)
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "central")
                .attr("fill", isActive ? "#ffffff" : AXIS_COLOR)
                .attr("font-size", `${fontSize}px`)
                .attr("font-weight", "600")
                .attr("font-family", "'Segoe UI', sans-serif")
                .text(displayLabel);
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

        const s = this.scaleFactor(width, height);

        // Responsive margins — scale with viewport but enforce minimums
        const margin = {
            top: Math.max(28, Math.min(42, 42 * s)),
            right: Math.max(8, Math.min(16, 16 * s)),
            bottom: Math.max(20, Math.min(32, 32 * s)),
            left: Math.max(36, Math.min(56, 56 * s)),
        };

        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;

        if (chartWidth <= 20 || chartHeight <= 20) return;

        this.chartGroup.attr("transform", `translate(${margin.left},${margin.top})`);

        // Responsive font sizes
        const axisFontSize = Math.max(7, Math.min(10, 10 * s));
        const legendFontSize = Math.max(7, Math.min(10, 10 * s));
        const lineWidth = Math.max(1.5, Math.min(2.5, 2 * s));

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
        filter.append("feGaussianBlur").attr("stdDeviation", String(Math.max(1.5, 3 * s))).attr("result", "coloredBlur");
        const feMerge = filter.append("feMerge");
        feMerge.append("feMergeNode").attr("in", "coloredBlur");
        feMerge.append("feMergeNode").attr("in", "SourceGraphic");

        // Gridlines — fewer at small sizes
        const numTicks = Math.max(3, Math.min(5, Math.floor(chartHeight / 40)));
        const yTicks = yScale.ticks(numTicks);
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
                .attr("stroke-width", lineWidth)
                .attr("filter", "url(#glow)");
        });

        // X-axis labels — adaptive density based on available width
        const labelCharWidth = axisFontSize * 0.65;
        const avgLabelWidth = 6 * labelCharWidth; // ~6 chars per label
        const maxLabels = Math.max(3, Math.floor(chartWidth / (avgLabelWidth + 8)));
        const labelStep = Math.max(1, Math.ceil(categories.length / maxLabels));

        this.chartGroup.append("g")
            .attr("transform", `translate(0,${chartHeight})`)
            .selectAll(".x-label")
            .data(categories).enter()
            .append("text")
            .attr("x", d => xScale(d) || 0)
            .attr("y", Math.max(12, 18 * s))
            .attr("text-anchor", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", `${axisFontSize}px`)
            .attr("font-family", "'Segoe UI', sans-serif")
            .text((d, i) => i % labelStep === 0 ? d : "");

        // Y-axis labels
        this.chartGroup.append("g")
            .selectAll(".y-label")
            .data(yTicks).enter()
            .append("text")
            .attr("x", -Math.max(4, 8 * s))
            .attr("y", d => yScale(d))
            .attr("text-anchor", "end")
            .attr("dominant-baseline", "middle")
            .attr("fill", AXIS_COLOR)
            .attr("font-size", `${axisFontSize}px`)
            .attr("font-family", "'Segoe UI', sans-serif")
            .text(d => this.formatYValue(d, currency));

        // Legend — responsive positioning and visibility
        const showLegend = height > 120 && width > 250;
        if (showLegend) {
            const legendY = Math.max(10, 14 * s);

            // Offset the legend horizontally so it clears the internal title.
            // The title is drawn at x=10 with a 12px semibold font; estimate its
            // rendered width and start the legend after it (plus an 18px gap).
            // If there is no title, fall back to the chart's left margin.
            const titleFontPx = 12;
            const titleWidth = this.currentTitle
                ? this.currentTitle.length * titleFontPx * 0.58
                : 0;
            const legendStartX = titleWidth > 0
                ? Math.max(margin.left, 10 + titleWidth + 18)
                : margin.left;
            this.legendGroup.attr("transform", `translate(${legendStartX}, ${legendY})`);

            const legendSpacing = Math.max(80, Math.min(120, 120 * s));
            const legendDotR = Math.max(3, Math.min(4, 4 * s));

            seriesData.forEach((series, i) => {
                const legendItem = this.legendGroup.append("g")
                    .attr("transform", `translate(${i * legendSpacing}, 0)`);
                legendItem.append("circle")
                    .attr("cx", 5).attr("cy", 5).attr("r", legendDotR)
                    .attr("fill", series.color);

                const maxNameLen = Math.floor((legendSpacing - 20) / (legendFontSize * 0.55));
                const displayName = series.name.length > maxNameLen
                    ? series.name.substring(0, maxNameLen) + "…"
                    : series.name;

                legendItem.append("text")
                    .attr("x", legendDotR * 2 + 8).attr("y", 5)
                    .attr("dominant-baseline", "middle")
                    .attr("fill", AXIS_COLOR)
                    .attr("font-size", `${legendFontSize}px`)
                    .attr("font-family", "'Segoe UI', sans-serif")
                    .text(displayName);
            });
        }

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
                .attr("r", Math.max(3, 4 * s)).attr("fill", series.color)
                .attr("stroke", "#fff").attr("stroke-width", Math.max(1, 1.5 * s))
                .style("opacity", 0).style("pointer-events", "none")
        );

        const tooltipFontSize = Math.max(7, Math.min(9, 9 * s));
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

                const lineHeight = Math.max(11, 14 * s);
                const boxWidth = Math.max(100, Math.min(140, 140 * s));
                const boxHeight = (seriesData.length + 1) * lineHeight + Math.max(6, 10 * s);
                let tipX = nearestX + 12;
                if (tipX + boxWidth > chartWidth) tipX = nearestX - boxWidth - 12;
                const tipY = 20;

                tooltipBg.attr("x", tipX).attr("y", tipY).attr("width", boxWidth).attr("height", boxHeight);
                tooltipGroup.selectAll("text").remove();

                const catLabel = nearestCat;
                tooltipGroup.append("text")
                    .attr("x", tipX + 8).attr("y", tipY + lineHeight)
                    .attr("fill", "#e2e8f0").attr("font-size", `${tooltipFontSize}px`)
                    .attr("font-weight", "bold").attr("font-family", "'Segoe UI', sans-serif")
                    .text(catLabel);

                seriesData.forEach((series, si) => {
                    const val = series.values[nearestIdx]?.value || 0;
                    const cy = yScale(val);
                    tooltipDots[si].attr("cx", nearestX).attr("cy", cy).style("opacity", 1);
                    tooltipGroup.append("text")
                        .attr("x", tipX + 8).attr("y", tipY + lineHeight + (si + 1) * lineHeight)
                        .attr("fill", series.color).attr("font-size", `${tooltipFontSize}px`)
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
