/*
 * Premium KPI Visual — renders a single measure value with
 * bespoke executive styling using DOM manipulation.
 * Handles initial empty dataView gracefully (waits for data).
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
    private wrapper: HTMLElement;
    private accentBar: HTMLElement;
    private labelEl: HTMLElement;
    private valueEl: HTMLElement;
    private hasRendered: boolean = false;

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.container = options.element;
        this.container.style.overflow = "hidden";

        // Build DOM structure once
        this.wrapper = document.createElement("div");
        this.wrapper.className = "premium-kpi-wrapper";

        this.accentBar = document.createElement("div");
        this.accentBar.className = "premium-kpi-accent";

        this.labelEl = document.createElement("div");
        this.labelEl.className = "premium-kpi-label";

        this.valueEl = document.createElement("div");
        this.valueEl.className = "premium-kpi-value";
        this.valueEl.textContent = "—";

        this.wrapper.appendChild(this.accentBar);
        this.wrapper.appendChild(this.labelEl);
        this.wrapper.appendChild(this.valueEl);
        this.container.appendChild(this.wrapper);
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const height = options.viewport.height;

            // Extract value from dataView - try multiple formats
            let formatted = "";
            let label = "";
            let hasData = false;

            const dv = options.dataViews?.[0];
            if (dv) {
                // Try single mapping first
                if (dv.single?.value !== undefined && dv.single.value !== null) {
                    const value = Number(dv.single.value);
                    formatted = this.formatValue(value);
                    hasData = true;
                }
                // Try categorical mapping
                else if (dv.categorical?.values?.[0]?.values?.[0] !== undefined &&
                         dv.categorical.values[0].values[0] !== null) {
                    const value = Number(dv.categorical.values[0].values[0]);
                    formatted = this.formatValue(value);
                    hasData = true;
                }

                // Get label from metadata or categorical source
                if (dv.metadata?.columns?.[0]) {
                    label = dv.metadata.columns[0].displayName || "";
                } else if (dv.categorical?.values?.[0]?.source?.displayName) {
                    label = dv.categorical.values[0].source.displayName;
                }
            }

            // Update DOM - always update even if no data yet
            if (hasData) {
                this.labelEl.textContent = label;
                this.valueEl.textContent = formatted;
                this.hasRendered = true;
            } else if (!this.hasRendered) {
                // Show label if available, dash for value
                this.labelEl.textContent = label || "";
                this.valueEl.textContent = "—";
            }

            // Responsive font sizing
            const valueFontSize = Math.min(Math.max(height * 0.35, 18), 48);
            const labelFontSize = Math.min(Math.max(height * 0.12, 9), 13);
            this.valueEl.style.fontSize = `${valueFontSize}px`;
            this.labelEl.style.fontSize = `${labelFontSize}px`;

            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    private formatValue(value: number): string {
        const abs = Math.abs(value);
        if (abs >= 1_000_000) {
            return `\u00A3${(value / 1_000_000).toFixed(1)}M`;
        } else if (abs >= 1_000) {
            return `\u00A3${(value / 1_000).toFixed(0)}K`;
        } else if (abs < 1 && abs > 0) {
            return `${(value * 100).toFixed(1)}%`;
        }
        return value.toLocaleString("en-GB", { maximumFractionDigits: 0 });
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
