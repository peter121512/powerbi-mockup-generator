/*
 * Premium Chart Visual — renders a bar/column chart with
 * bespoke executive styling using SVG rendering.
 * Supports category + measure data binding.
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;
import ISelectionManager = powerbi.extensibility.ISelectionManager;
import ISelectionId = powerbi.visuals.ISelectionId;

interface DataPoint {
    category: string;
    value: number;
    selectionId: ISelectionId;
}

export class Visual implements IVisual {
    private events: IVisualEventService;
    private host: powerbi.extensibility.visual.IVisualHost;
    private container: HTMLElement;
    private svg: SVGElement;
    private selectionManager: ISelectionManager;

    // Design tokens
    private readonly MARGIN = { top: 40, right: 20, bottom: 50, left: 60 };
    private readonly BAR_COLOR = "#1B3A5C";
    private readonly BAR_HOVER_COLOR = "#2A5A8C";
    private readonly GRID_COLOR = "#E8E8F0";
    private readonly TEXT_PRIMARY = "#1A1A2E";
    private readonly TEXT_SECONDARY = "#4A4A6A";
    private readonly FONT_FAMILY = "'Segoe UI', -apple-system, sans-serif";

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.host = options.host;
        this.container = options.element;
        this.container.style.overflow = "hidden";
        this.selectionManager = options.host.createSelectionManager();

        // Create SVG element
        this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        this.svg.setAttribute("class", "premium-chart-svg");
        this.container.appendChild(this.svg);
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const width = options.viewport.width;
            const height = options.viewport.height;
            this.svg.setAttribute("width", String(width));
            this.svg.setAttribute("height", String(height));

            // Clear previous content
            while (this.svg.firstChild) {
                this.svg.removeChild(this.svg.firstChild);
            }

            // Extract data
            const dataPoints = this.extractData(options);
            if (dataPoints.length === 0) {
                this.renderEmpty(width, height);
                this.events.renderingFinished(options);
                return;
            }

            // Get measure name for title
            const dv = options.dataViews?.[0];
            const measureName = dv?.categorical?.values?.[0]?.source?.displayName || "Value";

            // Render chart
            this.renderBarChart(dataPoints, width, height, measureName);

            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    private extractData(options: VisualUpdateOptions): DataPoint[] {
        const dv = options.dataViews?.[0];
        if (!dv?.categorical?.categories?.[0]?.values || !dv?.categorical?.values?.[0]?.values) {
            return [];
        }

        const categories = dv.categorical.categories[0].values;
        const values = dv.categorical.values[0].values;
        const points: DataPoint[] = [];

        for (let i = 0; i < categories.length; i++) {
            const selectionId = this.host.createSelectionIdBuilder()
                .withCategory(dv.categorical.categories[0], i)
                .createSelectionId();

            points.push({
                category: String(categories[i] || ""),
                value: Number(values[i] || 0),
                selectionId: selectionId,
            });
        }

        return points;
    }

    private renderEmpty(width: number, height: number): void {
        const text = this.createSVGText(
            width / 2, height / 2, "No data", 12, this.TEXT_SECONDARY, "middle"
        );
        this.svg.appendChild(text);
    }

    private renderBarChart(data: DataPoint[], width: number, height: number, title: string): void {
        const m = this.MARGIN;
        const plotWidth = width - m.left - m.right;
        const plotHeight = height - m.top - m.bottom;

        if (plotWidth <= 0 || plotHeight <= 0) return;

        // Title
        const titleEl = this.createSVGText(
            m.left, 24, title, 11, this.TEXT_PRIMARY, "start", "600"
        );
        this.svg.appendChild(titleEl);

        // Scale
        const maxVal = Math.max(...data.map(d => d.value), 0);
        const yScale = (v: number) => plotHeight - (v / (maxVal || 1)) * plotHeight;
        const barWidth = Math.max(4, (plotWidth / data.length) * 0.65);
        const barGap = (plotWidth / data.length) - barWidth;

        // Gridlines (3 horizontal)
        for (let i = 0; i <= 3; i++) {
            const yPos = m.top + (plotHeight / 3) * i;
            const line = this.createSVGLine(m.left, yPos, m.left + plotWidth, yPos, this.GRID_COLOR, 1);
            this.svg.appendChild(line);

            // Y-axis labels
            const val = maxVal - (maxVal / 3) * i;
            const label = this.formatAxis(val);
            const labelEl = this.createSVGText(
                m.left - 8, yPos + 4, label, 9, this.TEXT_SECONDARY, "end"
            );
            this.svg.appendChild(labelEl);
        }

        // Bars
        data.forEach((d, i) => {
            const x = m.left + i * (barWidth + barGap) + barGap / 2;
            const barHeight = (d.value / (maxVal || 1)) * plotHeight;
            const y = m.top + plotHeight - barHeight;

            const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            rect.setAttribute("x", String(x));
            rect.setAttribute("y", String(y));
            rect.setAttribute("width", String(barWidth));
            rect.setAttribute("height", String(Math.max(0, barHeight)));
            rect.setAttribute("fill", this.BAR_COLOR);
            rect.setAttribute("rx", "2");
            rect.style.cursor = "pointer";
            rect.style.transition = "fill 0.15s ease";

            // Hover effect
            rect.addEventListener("mouseenter", () => rect.setAttribute("fill", this.BAR_HOVER_COLOR));
            rect.addEventListener("mouseleave", () => rect.setAttribute("fill", this.BAR_COLOR));

            // Selection
            rect.addEventListener("click", (e) => {
                this.selectionManager.select(d.selectionId, (e as MouseEvent).ctrlKey);
            });

            this.svg.appendChild(rect);

            // X-axis label (rotate if many)
            if (data.length <= 12 || i % Math.ceil(data.length / 10) === 0) {
                const labelX = x + barWidth / 2;
                const labelY = m.top + plotHeight + 16;
                const catLabel = d.category.length > 8 ? d.category.substring(0, 7) + "…" : d.category;
                const catEl = this.createSVGText(
                    labelX, labelY, catLabel, 9, this.TEXT_SECONDARY, "middle"
                );
                this.svg.appendChild(catEl);
            }
        });
    }

    private formatAxis(value: number): string {
        if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
        if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`;
        return String(Math.round(value));
    }

    private createSVGText(
        x: number, y: number, text: string, fontSize: number,
        color: string, anchor: string, weight: string = "400"
    ): SVGTextElement {
        const el = document.createElementNS("http://www.w3.org/2000/svg", "text");
        el.setAttribute("x", String(x));
        el.setAttribute("y", String(y));
        el.setAttribute("font-size", String(fontSize));
        el.setAttribute("fill", color);
        el.setAttribute("font-family", this.FONT_FAMILY);
        el.setAttribute("font-weight", weight);
        el.setAttribute("text-anchor", anchor);
        el.textContent = text;
        return el;
    }

    private createSVGLine(
        x1: number, y1: number, x2: number, y2: number,
        color: string, width: number
    ): SVGLineElement {
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", String(x1));
        line.setAttribute("y1", String(y1));
        line.setAttribute("x2", String(x2));
        line.setAttribute("y2", String(y2));
        line.setAttribute("stroke", color);
        line.setAttribute("stroke-width", String(width));
        return line;
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
