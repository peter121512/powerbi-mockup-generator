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
        color: "rgba(52, 211, 153, 0.6)",
        icon: "ARROW_UP_SVG",
        text: "Active customer base grew 14% YoY with 87% retention across all segments"
    },
    {
        color: "rgba(168, 85, 247, 0.6)",
        icon: "PEOPLE_SVG",
        text: "Enterprise segment delivers highest LTV at £125K with 95% retention rate"
    },
    {
        color: "rgba(251, 146, 60, 0.6)",
        icon: "%",
        text: "Online channel driving 30% of new acquisitions, up from 22% prior year"
    },
    {
        color: "rgba(6, 182, 212, 0.6)",
        icon: "\u25C6",
        text: "Scotland region showing accelerated growth with 18% new customer increase"
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
                } else if (insight.icon === "ARROW_UP_SVG") {
                    html += `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>`;
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
