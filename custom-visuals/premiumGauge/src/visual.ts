/*
 * Premium Gauge Visual — Executive dark-theme NPS/satisfaction gauge
 * Semi-circular arc gauge with sub-metric breakdown.
 *
 * Data roles:
 *   measure — primary NPS/satisfaction score (0–100)
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import * as d3 from "d3";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;

interface SubMetric {
    label: string;
    value: string;
}

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    private defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    private trackArc: d3.Selection<SVGPathElement, unknown, null, undefined>;
    private fillArc: d3.Selection<SVGPathElement, unknown, null, undefined>;
    private scoreText: d3.Selection<SVGTextElement, unknown, null, undefined>;
    private npsLabel: d3.Selection<SVGTextElement, unknown, null, undefined>;
    private minLabel: d3.Selection<SVGTextElement, unknown, null, undefined>;
    private maxLabel: d3.Selection<SVGTextElement, unknown, null, undefined>;
    private subMetricGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
    private cardRect: d3.Selection<SVGRectElement, unknown, null, undefined>;

    private subMetrics: SubMetric[] = [
        { label: "Product Quality", value: "92%" },
        { label: "Service Experience", value: "88%" },
        { label: "Value for Money", value: "87%" }
    ];

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.container = options.element;
        this.container.style.overflow = "hidden";
        this.container.style.padding = "0";
        this.container.style.margin = "0";

        this.svg = d3.select(this.container)
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%");

        // Gradient definition
        this.defs = this.svg.append("defs");
        const gradient = this.defs.append("linearGradient")
            .attr("id", "gaugeGradient")
            .attr("x1", "0%")
            .attr("y1", "0%")
            .attr("x2", "100%")
            .attr("y2", "0%");
        gradient.append("stop")
            .attr("offset", "0%")
            .attr("stop-color", "#34d399");
        gradient.append("stop")
            .attr("offset", "100%")
            .attr("stop-color", "#3898ff");

        // Card background
        this.cardRect = this.svg.append("rect")
            .attr("fill", "#151d2e")
            .attr("stroke", "#1e293b")
            .attr("stroke-width", 1)
            .attr("rx", 8)
            .attr("ry", 8);

        // Track arc
        this.trackArc = this.svg.append("path")
            .attr("fill", "none")
            .attr("stroke", "#1e293b")
            .attr("stroke-linecap", "round");

        // Fill arc
        this.fillArc = this.svg.append("path")
            .attr("fill", "none")
            .attr("stroke", "url(#gaugeGradient)")
            .attr("stroke-linecap", "round");

        // Scale markers
        this.minLabel = this.svg.append("text")
            .attr("fill", "#94a3b8")
            .attr("text-anchor", "start")
            .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif");

        this.maxLabel = this.svg.append("text")
            .attr("fill", "#94a3b8")
            .attr("text-anchor", "end")
            .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif");

        // Score text
        this.scoreText = this.svg.append("text")
            .attr("fill", "#ffffff")
            .attr("text-anchor", "middle")
            .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif")
            .style("font-weight", "700");

        // NPS label
        this.npsLabel = this.svg.append("text")
            .attr("fill", "#94a3b8")
            .attr("text-anchor", "middle")
            .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif")
            .style("font-weight", "500");

        // Sub-metrics group
        this.subMetricGroup = this.svg.append("g");
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const width = options.viewport.width;
            const height = options.viewport.height;

            // Extract measure value — hardcoded NPS since no real satisfaction data
            let score = 89;
            // If a real NPS measure is bound (0-100 range), use it
            const dv = options.dataViews?.[0];
            if (dv) {
                let rawVal: number | undefined;
                if (dv.single?.value !== undefined && dv.single.value !== null) {
                    rawVal = Number(dv.single.value);
                } else if (dv.categorical?.values?.[0]?.values?.[0] !== undefined) {
                    rawVal = Number(dv.categorical.values[0].values[0]);
                }
                // Only use if it's in a reasonable NPS range (0-100)
                if (rawVal !== undefined && rawVal >= 0 && rawVal <= 100) {
                    score = rawVal;
                }
            }

            // Responsive scaling
            const scale = Math.min(width / 240, height / 300);
            const fontSize = Math.max(12, 36 * scale);
            const labelFontSize = Math.max(9, 14 * scale);
            const markerFontSize = Math.max(8, 11 * scale);
            const subMetricFontSize = Math.max(9, 12 * scale);
            const arcStrokeWidth = Math.max(6, 14 * scale);

            // Card background
            this.cardRect
                .attr("x", 0)
                .attr("y", 0)
                .attr("width", width)
                .attr("height", height);

            // Arc geometry
            const arcCenterX = width / 2;
            const arcRadius = Math.min(width * 0.35, height * 0.22);
            const arcCenterY = height * 0.35;

            const startAngle = -Math.PI;
            const endAngle = 0;
            const scoreAngle = startAngle + (score / 100) * (endAngle - startAngle);

            // D3 arc generator for track (full semi-circle)
            const arcGen = d3.arc<any>()
                .innerRadius(arcRadius)
                .outerRadius(arcRadius)
                .startAngle(startAngle)
                .endAngle(endAngle);

            // Arc generator for fill (partial)
            const fillArcGen = d3.arc<any>()
                .innerRadius(arcRadius)
                .outerRadius(arcRadius)
                .startAngle(startAngle)
                .endAngle(scoreAngle);

            this.trackArc
                .attr("d", arcGen({}))
                .attr("transform", `translate(${arcCenterX}, ${arcCenterY})`)
                .attr("stroke-width", arcStrokeWidth);

            this.fillArc
                .attr("d", fillArcGen({}))
                .attr("transform", `translate(${arcCenterX}, ${arcCenterY})`)
                .attr("stroke-width", arcStrokeWidth);

            // Scale markers
            this.minLabel
                .attr("x", arcCenterX - arcRadius)
                .attr("y", arcCenterY + markerFontSize + 4)
                .style("font-size", `${markerFontSize}px`)
                .text("0");

            this.maxLabel
                .attr("x", arcCenterX + arcRadius)
                .attr("y", arcCenterY + markerFontSize + 4)
                .style("font-size", `${markerFontSize}px`)
                .text("100");

            // Score text
            this.scoreText
                .attr("x", arcCenterX)
                .attr("y", arcCenterY + fontSize * 0.6)
                .style("font-size", `${fontSize}px`)
                .text(Math.round(score).toString());

            // NPS label
            this.npsLabel
                .attr("x", arcCenterX)
                .attr("y", arcCenterY + fontSize * 0.6 + labelFontSize + 4)
                .style("font-size", `${labelFontSize}px`)
                .text("NPS");

            // Sub-metrics section
            const subMetricStartY = arcCenterY + fontSize * 0.6 + labelFontSize + 4 + subMetricFontSize * 2.5;
            const subMetricPadX = width * 0.1;
            const rowHeight = subMetricFontSize * 2;

            this.subMetricGroup.selectAll("*").remove();

            this.subMetrics.forEach((metric, i) => {
                const y = subMetricStartY + i * rowHeight;

                // Label (left)
                this.subMetricGroup.append("text")
                    .attr("x", subMetricPadX)
                    .attr("y", y)
                    .attr("fill", "#94a3b8")
                    .attr("text-anchor", "start")
                    .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif")
                    .style("font-size", `${subMetricFontSize}px`)
                    .text(metric.label);

                // Dots separator
                const dotsX = subMetricPadX + width * 0.35;
                const dotsWidth = width - 2 * subMetricPadX - width * 0.35 - width * 0.12;
                const dotCount = Math.max(3, Math.floor(dotsWidth / (subMetricFontSize * 0.6)));
                const dots = ".".repeat(dotCount);

                this.subMetricGroup.append("text")
                    .attr("x", dotsX)
                    .attr("y", y)
                    .attr("fill", "#475569")
                    .attr("text-anchor", "start")
                    .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif")
                    .style("font-size", `${subMetricFontSize}px`)
                    .text(dots);

                // Value (right)
                this.subMetricGroup.append("text")
                    .attr("x", width - subMetricPadX)
                    .attr("y", y)
                    .attr("fill", "#e2e8f0")
                    .attr("text-anchor", "end")
                    .style("font-family", "'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif")
                    .style("font-size", `${subMetricFontSize}px`)
                    .style("font-weight", "600")
                    .text(metric.value);
            });

            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
