/*
 * Premium KPI Visual v2 — Executive dark-theme KPI card
 * Matches Mockup 1 reference: dark surface, accent icon, large value,
 * delta indicator, optional sparkline.
 *
 * Data roles:
 *   measure   — primary KPI value (required)
 *   delta     — comparison percentage (optional)
 *   sparkline — time series values for mini chart (optional, future)
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;
    private card: HTMLElement;
    private iconCircle: HTMLElement;
    private iconText: HTMLElement;
    private contentArea: HTMLElement;
    private labelEl: HTMLElement;
    private valueEl: HTMLElement;
    private deltaArea: HTMLElement;
    private deltaArrow: HTMLElement;
    private deltaValue: HTMLElement;
    private deltaContext: HTMLElement;
    private hasRendered: boolean = false;

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.container = options.element;
        this.container.style.overflow = "hidden";
        this.container.style.padding = "0";
        this.container.style.margin = "0";

        // Card wrapper
        this.card = document.createElement("div");
        this.card.className = "kpi-card";

        // Left: icon circle
        this.iconCircle = document.createElement("div");
        this.iconCircle.className = "kpi-icon-circle";
        this.iconText = document.createElement("span");
        this.iconText.className = "kpi-icon-text";
        this.iconText.textContent = "$";
        this.iconCircle.appendChild(this.iconText);

        // Center: label + value stack
        this.contentArea = document.createElement("div");
        this.contentArea.className = "kpi-content";

        this.labelEl = document.createElement("div");
        this.labelEl.className = "kpi-label";

        this.valueEl = document.createElement("div");
        this.valueEl.className = "kpi-value";
        this.valueEl.textContent = "—";

        this.contentArea.appendChild(this.labelEl);
        this.contentArea.appendChild(this.valueEl);

        // Right: delta area
        this.deltaArea = document.createElement("div");
        this.deltaArea.className = "kpi-delta";

        this.deltaArrow = document.createElement("span");
        this.deltaArrow.className = "kpi-delta-arrow";

        this.deltaValue = document.createElement("span");
        this.deltaValue.className = "kpi-delta-value";

        this.deltaContext = document.createElement("div");
        this.deltaContext.className = "kpi-delta-context";
        this.deltaContext.textContent = "vs. prior period";

        this.deltaArea.appendChild(this.deltaArrow);
        this.deltaArea.appendChild(this.deltaValue);
        this.deltaArea.appendChild(this.deltaContext);

        // Assemble
        this.card.appendChild(this.iconCircle);
        this.card.appendChild(this.contentArea);
        this.card.appendChild(this.deltaArea);
        this.container.appendChild(this.card);
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const viewport = options.viewport;
            const dv = options.dataViews?.[0];

            let value = "";
            let label = "";
            let deltaText = "";
            let deltaPositive = true;
            let hasData = false;
            let hasDelta = false;

            if (dv) {
                // Primary measure — try single first, then categorical
                if (dv.single?.value !== undefined && dv.single.value !== null) {
                    value = this.formatValue(Number(dv.single.value));
                    hasData = true;
                } else if (dv.categorical?.values?.[0]?.values?.[0] !== undefined) {
                    value = this.formatValue(Number(dv.categorical.values[0].values[0]));
                    hasData = true;
                }

                // Label from metadata
                if (dv.metadata?.columns?.[0]) {
                    label = dv.metadata.columns[0].displayName || "";
                } else if (dv.categorical?.values?.[0]?.source?.displayName) {
                    label = dv.categorical.values[0].source.displayName;
                }

                // Delta — second measure if available
                if (dv.categorical?.values?.[1]?.values?.[0] !== undefined) {
                    const deltaNum = Number(dv.categorical.values[1].values[0]);
                    deltaPositive = deltaNum >= 0;
                    deltaText = (deltaPositive ? "+" : "") + deltaNum.toFixed(1) + "%";
                    hasDelta = true;
                }
            }

            // Update DOM
            if (hasData) {
                this.labelEl.textContent = this.friendlyLabel(label);
                this.valueEl.textContent = value;
                this.hasRendered = true;
            } else if (!this.hasRendered) {
                this.labelEl.textContent = "";
                this.valueEl.textContent = "—";
            }

            // Delta display
            if (hasDelta) {
                this.deltaArea.style.display = "flex";
                this.deltaArrow.textContent = deltaPositive ? "▲" : "▼";
                this.deltaArrow.className = "kpi-delta-arrow " + (deltaPositive ? "positive" : "negative");
                this.deltaValue.textContent = deltaText;
                this.deltaValue.className = "kpi-delta-value " + (deltaPositive ? "positive" : "negative");
            } else {
                this.deltaArea.style.display = "none";
            }

            // Icon — derive from label
            this.iconText.textContent = this.getIcon(label);

            // Responsive sizing
            const scale = Math.min(viewport.width / 280, viewport.height / 120);
            const valueFontSize = Math.min(Math.max(24 * scale, 16), 36);
            const labelFontSize = Math.min(Math.max(11 * scale, 9), 13);
            this.valueEl.style.fontSize = `${valueFontSize}px`;
            this.labelEl.style.fontSize = `${labelFontSize}px`;

            // Icon circle size
            const iconSize = Math.min(Math.max(32 * scale, 24), 44);
            this.iconCircle.style.width = `${iconSize}px`;
            this.iconCircle.style.height = `${iconSize}px`;
            this.iconText.style.fontSize = `${iconSize * 0.45}px`;

            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    private formatValue(value: number): string {
        const abs = Math.abs(value);
        if (abs >= 1_000_000_000) {
            return `£${(value / 1_000_000_000).toFixed(2)}B`;
        } else if (abs >= 1_000_000) {
            return `£${(value / 1_000_000).toFixed(1)}M`;
        } else if (abs >= 1_000) {
            return `£${(value / 1_000).toFixed(0)}K`;
        } else if (abs < 1 && abs > 0) {
            return `${(value * 100).toFixed(1)}%`;
        }
        return value.toLocaleString("en-GB", { maximumFractionDigits: 0 });
    }

    private getIcon(label: string): string {
        const l = (label || "").toLowerCase();
        if (l.includes("revenue") || l.includes("sales") || l.includes("total")) return "$";
        if (l.includes("profit") || l.includes("margin")) return "%";
        if (l.includes("customer") || l.includes("growth")) return "↑";
        if (l.includes("order") || l.includes("count")) return "#";
        if (l.includes("satisfaction") || l.includes("nps")) return "★";
        if (l.includes("cost")) return "¢";
        return "◆";
    }

    private friendlyLabel(label: string): string {
        if (!label) return "";
        // Split camelCase: "TotalRevenue" -> "Total Revenue"
        // Also split PascalCase and preserve acronyms
        return label
            .replace(/([a-z])([A-Z])/g, "$1 $2")
            .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
            .replace(/Pct$/, "%")
            .replace(/Pct /, "% ");
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
