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
        color: "rgba(52, 211, 153, 0.2)",
        icon: "\u2191",
        text: "Revenue up 12.4% driven by strong performance in Enterprise and Healthcare"
    },
    {
        color: "rgba(168, 85, 247, 0.2)",
        icon: "\uD83D\uDC65",
        text: "Customer base expanded by 18.6% with particular strength in Asia Pacific"
    },
    {
        color: "rgba(251, 146, 60, 0.2)",
        icon: "%",
        text: "Operating margin increased 0.6pp through discipline on operational costs"
    },
    {
        color: "rgba(6, 182, 212, 0.2)",
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
                html += `<span class="insight-icon">${insight.icon}</span>`;
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
