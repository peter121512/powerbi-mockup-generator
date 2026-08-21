/*
 * Premium Insights Visual — Executive Key Insights panel
 * Renders a dark card with colored icon circles and insight text rows.
 * Data role "measure" exists only to trigger rendering; its value is unused.
 */
"use strict";

import powerbi from "powerbi-visuals-api";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;
import IVisualEventService = powerbi.extensibility.IVisualEventService;

interface InsightRow {
    color: string;
    icon: string;
    text: string;
}

const INSIGHTS: InsightRow[] = [
    {
        color: "rgba(52, 211, 153, 0.35)",
        icon: "\u2191",
        text: "Revenue up 12.4% driven by strong performance in Enterprise and Healthcare"
    },
    {
        color: "rgba(168, 85, 247, 0.35)",
        icon: "PEOPLE_SVG",
        text: "Customer base expanded by 18.6% with particular strength in Asia Pacific"
    },
    {
        color: "rgba(251, 146, 60, 0.35)",
        icon: "%",
        text: "Operating margin increased 0.6pp through discipline on operational costs"
    },
    {
        color: "rgba(6, 182, 212, 0.35)",
        icon: "\u25C6",
        text: "Product innovation pipeline contributing to sustained growth momentum"
    }
];

export class Visual implements IVisual {
    private events: IVisualEventService;
    private container: HTMLElement;

    constructor(options: VisualConstructorOptions) {
        this.events = options.host.eventService;
        this.container = options.element;
        this.container.style.overflow = "hidden";
        this.container.style.padding = "0";
        this.container.style.margin = "0";
    }

    public update(options: VisualUpdateOptions) {
        this.events.renderingStarted(options);

        try {
            const viewport = options.viewport;

            // Build HTML
            let html = `<div class="insights-card" style="width:${viewport.width}px;height:${viewport.height}px;">`;
            html += `<div class="insights-title">\uD83D\uDCA1 Key Insights</div>`;
            html += `<div class="insights-rows">`;

            for (const insight of INSIGHTS) {
                html += `<div class="insight-row">`;
                html += `<div class="insight-circle" style="background:${insight.color};">`;
                if (insight.icon === "PEOPLE_SVG") {
                    html += `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`;
                } else {
                    html += `<span class="insight-icon">${insight.icon}</span>`;
                }
                html += `</div>`;
                html += `<div class="insight-text">${insight.text}</div>`;
                html += `</div>`;
            }

            html += `</div></div>`;

            this.container.innerHTML = html;

            this.events.renderingFinished(options);
        } catch (error) {
            this.events.renderingFailed(options, String(error));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return { cards: [] };
    }
}
