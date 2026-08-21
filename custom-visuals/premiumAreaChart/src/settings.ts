/*
 * Premium Area Chart — no formatting pane settings needed for initial build.
 */
"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";

export class VisualFormattingSettingsModel extends formattingSettings.Model {
    cards = [];
}
