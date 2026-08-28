/*
 * Premium Donut — Executive dark-theme donut chart with integrated center KPI.
 *
 * Renders:
 *   - Title text (top-left, inside panel)
 *   - Donut ring (SVG arcs, left-center area)
 *   - Center KPI (total value + label in the donut hole)
 *   - Legend (right side, colored dots + labels)
 *
 * Data roles:
 *   category — slice categories (e.g. segments, regions)
 *   values   — measure for each slice
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import * as d3 from "d3";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;

interface SliceData {
    category: string;
    value: number;
    color: string;
    percentage: number;
}

const COLORS = ["#3898ff", "#a78bfa", "#34d399", "#fbbf24", "#fb923c", "#f87171", "#06b6d4", "#818cf8"];
const BG_COLOR = "#151d2e";
const BORDER_COLOR = "#1e293b";
const TEXT_PRIMARY = "#ffffff";
const TEXT_MUTED = "#94a3b8";
const TITLE_COLOR = "#e2e8f0";

export class Visual implements IVisual {
    private container: HTMLElement;
    private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;

    constructor(options: VisualConstructorOptions) {
        this.container = options.element;
        this.container.style.overflow = "hidden";

        this.svg = d3.select(this.container)
            .append("svg")
            .style("width", "100%")
            .style("height", "100%");
    }

    public update(options: VisualUpdateOptions) {
        this.svg.selectAll("*").remove();

        const width = options.viewport.width;
        const height = options.viewport.height;
        this.svg.attr("viewBox", `0 0 ${width} ${height}`);

        // Background
        this.svg.append("rect")
            .attr("width", width)
            .attr("height", height)
            .attr("rx", 8)
            .attr("fill", BG_COLOR)
            .attr("stroke", BORDER_COLOR)
            .attr("stroke-width", 1);

        // Parse data
        const dataView = options.dataViews?.[0];
        if (!dataView?.categorical?.categories?.[0]?.values || !dataView?.categorical?.values?.[0]?.values) {
            return;
        }

        const categories = dataView.categorical.categories[0].values as string[];
        const values = dataView.categorical.values[0].values as number[];

        const total = values.reduce((sum, v) => sum + (v || 0), 0);
        const slices: SliceData[] = categories.map((cat, i) => ({
            category: String(cat),
            value: values[i] || 0,
            color: COLORS[i % COLORS.length],
            percentage: total > 0 ? ((values[i] || 0) / total) * 100 : 0,
        }));

        // Get title from the visual container title (passed via PBI)
        // We'll render it ourselves inside the panel
        const title = (dataView.metadata?.columns?.[0]?.queryName || "").split(".")[0] || "";

        // Layout
        const titleHeight = 28;
        const padding = 12;
        const legendWidth = Math.min(width * 0.35, 140);
        const chartArea = width - legendWidth - padding * 2;
        const chartCenterX = padding + chartArea / 2;
        const chartCenterY = titleHeight + (height - titleHeight) / 2;
        const outerRadius = Math.min(chartArea, height - titleHeight - padding) / 2 - 8;
        const innerRadius = outerRadius * 0.62;

        // Title (inside panel, top-left)
        // Read title from the visual's container title property if available
        const titleText = this.getTitle(options);
        if (titleText) {
            this.svg.append("text")
                .attr("x", padding)
                .attr("y", 18)
                .attr("font-family", "Segoe UI Semibold, sans-serif")
                .attr("font-size", "12px")
                .attr("fill", TITLE_COLOR)
                .text(titleText);
        }

        // Donut arcs
        const arcGenerator = d3.arc<d3.PieArcDatum<SliceData>>()
            .innerRadius(innerRadius)
            .outerRadius(outerRadius)
            .padAngle(0.02)
            .cornerRadius(3);

        const pie = d3.pie<SliceData>()
            .value(d => d.value)
            .sort(null);

        const arcs = pie(slices);

        const donutGroup = this.svg.append("g")
            .attr("transform", `translate(${chartCenterX}, ${chartCenterY})`);

        donutGroup.selectAll("path")
            .data(arcs)
            .enter()
            .append("path")
            .attr("d", arcGenerator as any)
            .attr("fill", d => d.data.color)
            .attr("opacity", 0.9);

        // Center KPI — total value (can be suppressed via general.showCenterValue
        // so a caller-supplied overlay can display a different metric instead)
        if (this.getShowCenterValue(options)) {
            const formattedTotal = this.formatValue(total);
            donutGroup.append("text")
                .attr("text-anchor", "middle")
                .attr("dy", "-2px")
                .attr("font-family", "Segoe UI Semibold, sans-serif")
                .attr("font-size", `${Math.max(16, Math.min(22, outerRadius * 0.3))}px`)
                .attr("font-weight", "700")
                .attr("fill", TEXT_PRIMARY)
                .text(formattedTotal);

            // Center label
            const measureName = dataView.categorical.values[0].source.displayName || "Total";
            donutGroup.append("text")
                .attr("text-anchor", "middle")
                .attr("dy", "16px")
                .attr("font-family", "Segoe UI, sans-serif")
                .attr("font-size", "10px")
                .attr("fill", TEXT_MUTED)
                .text(measureName);
        }

        // Legend (right side)
        const legendX = width - legendWidth;
        const legendStartY = titleHeight + 20;
        const legendSpacing = Math.min(30, (height - legendStartY - 10) / slices.length);

        slices.forEach((slice, i) => {
            const ly = legendStartY + i * legendSpacing;

            // Dot
            this.svg.append("circle")
                .attr("cx", legendX + 6)
                .attr("cy", ly)
                .attr("r", 5)
                .attr("fill", slice.color);

            // Label
            this.svg.append("text")
                .attr("x", legendX + 18)
                .attr("y", ly + 4)
                .attr("font-family", "Segoe UI, sans-serif")
                .attr("font-size", "11px")
                .attr("fill", TEXT_MUTED)
                .text(slice.category);

            // Percentage
            this.svg.append("text")
                .attr("x", legendX + legendWidth - 8)
                .attr("y", ly + 4)
                .attr("font-family", "Segoe UI, sans-serif")
                .attr("font-size", "10px")
                .attr("fill", TEXT_MUTED)
                .attr("text-anchor", "end")
                .text(`${slice.percentage.toFixed(1)}%`);
        });
    }

    private getTitle(options: VisualUpdateOptions): string {
        // Read title from objects.general.title property
        const objects = options.dataViews?.[0]?.metadata?.objects;
        if (objects && objects["general"]) {
            const general = objects["general"] as any;
            if (general.title !== undefined) {
                return String(general.title);
            }
        }
        return "";
    }

    private getShowCenterValue(options: VisualUpdateOptions): boolean {
        // Default true (backward compatible). Callers can set
        // general.showCenterValue = false to hide the internal center KPI
        // when an external overlay supplies its own center metric.
        const objects = options.dataViews?.[0]?.metadata?.objects;
        if (objects && objects["general"]) {
            const general = objects["general"] as any;
            if (general.showCenterValue !== undefined) {
                return Boolean(general.showCenterValue);
            }
        }
        return true;
    }

    private formatValue(value: number): string {
        if (value >= 1_000_000) {
            return `${(value / 1_000_000).toFixed(1)}M`;
        } else if (value >= 1_000) {
            return `${(value / 1_000).toFixed(1)}K`;
        }
        return value.toLocaleString();
    }
}
