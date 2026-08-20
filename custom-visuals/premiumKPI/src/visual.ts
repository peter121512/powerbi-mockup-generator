/*
 * Premium KPI Visual — renders a single measure value with
 * bespoke executive styling using DOM manipulation (no innerHTML).
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

        this.wrapper.appendChild(this.accentBar);
        this.wrapper.appendChild(this.labelEl);
        this.wrapper.appendChild(this.valueEl);
        this.container.appendChild(this.wrapper);
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const height = options.viewport.height;

            // Extract value from dataView
            let formatted = "—";
            let label = "";

            const dv = options.dataViews?.[0];
            if (dv?.single?.value !== undefined) {
                const value = Number(dv.single.value);
                formatted = this.formatValue(value);
            }

            if (dv?.metadata?.columns?.[0]) {
                label = dv.metadata.columns[0].displayName || "";
            }

            // Update DOM
            this.labelEl.textContent = label;
            this.valueEl.textContent = formatted;

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
            return `£${(value / 1_000_000).toFixed(1)}M`;
        } else if (abs >= 1_000) {
            return `£${(value / 1_000).toFixed(0)}K`;
        } else if (abs < 1 && abs > 0) {
            return `${(value * 100).toFixed(1)}%`;
        }
        return value.toLocaleString("en-GB", { maximumFractionDigits: 0 });
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
