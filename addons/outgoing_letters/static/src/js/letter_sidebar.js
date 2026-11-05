/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onPatched, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STATE_LABELS = {
    draft:     "Draft",
    submitted: "Submitted",
    approved:  "Approved",
    printable: "Printable",
};

function hexToRgb(hex) {
    if (!hex) return "30, 41, 59";
    hex = String(hex).replace("#", "").trim();
    if (hex.length === 3) hex = hex.split("").map(c => c + c).join("");
    const num = parseInt(hex, 16);
    if (isNaN(num)) return "30, 41, 59";
    return `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
}

export class LetterSidebarWidget extends Component {
    static template = "outgoing_letters.LetterSidebar";

    static props = {
        record:   { type: Object },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm           = useService("orm");
        this.actionService = useService("action");
        this.state         = useState({ letters: [], loading: true, searchQuery: "" });

        onWillStart(() => this._loadLetters());

        onMounted(() => {
            this._applyLiveStyling();
            this._onToolbarChange = () => this._applyLiveStyling();
            const toolbar = document.querySelector(".ol_style_toolbar");
            if (toolbar) {
                toolbar.addEventListener("input", this._onToolbarChange);
                toolbar.addEventListener("change", this._onToolbarChange);
            }
            // Periodic check to capture asynchronous OWL relational updates
            this._styleTimer = setInterval(() => this._applyLiveStyling(), 300);
        });

        onPatched(() => this._applyLiveStyling());

        onWillUnmount(() => {
            if (this._styleTimer) clearInterval(this._styleTimer);
            const toolbar = document.querySelector(".ol_style_toolbar");
            if (toolbar && this._onToolbarChange) {
                toolbar.removeEventListener("input", this._onToolbarChange);
                toolbar.removeEventListener("change", this._onToolbarChange);
            }
        });

        useEffect(() => {
            this._applyLiveStyling();
        });
    }

    _applyLiveStyling() {
        const data = this.props.record?.data || {};

        // 1. Primary & Secondary Colors
        let pColor = data.primary_color;
        let sColor = data.secondary_color;
        const pEl = document.querySelector('.ol_style_toolbar [name="primary_color"] input');
        if (pEl && pEl.value) pColor = pEl.value;
        const sEl = document.querySelector('.ol_style_toolbar [name="secondary_color"] input');
        if (sEl && sEl.value) sColor = sEl.value;
        pColor = pColor || "#1e293b";
        sColor = sColor || "#475569";

        // 2. Document Layout Name (Folder, Boxed, Bold, Striped, Bubble, Wave, Light)
        let layoutName = "Light";
        if (data.report_layout_id) {
            const lVal = data.report_layout_id;
            if (Array.isArray(lVal)) {
                layoutName = lVal[1] || "Light";
            } else if (typeof lVal === "object" && lVal !== null) {
                layoutName = lVal.display_name || lVal.name || "Light";
            } else if (typeof lVal === "string") {
                layoutName = lVal;
            }
        }
        // Fallback to DOM input / selection text in toolbar
        const layoutEl = document.querySelector('.ol_style_toolbar [name="report_layout_id"] input') ||
                         document.querySelector('.ol_style_toolbar [name="report_layout_id"] .o_field_widget') ||
                         document.querySelector('.ol_style_toolbar [name="report_layout_id"]');
        if (layoutEl) {
            const val = (layoutEl.value || layoutEl.textContent || "").trim();
            if (val) layoutName = val;
        }

        // 3. Background type (Blank, Geometric, Custom)
        let bgType = data.layout_background;
        const bgEl = document.querySelector('.ol_style_toolbar [name="layout_background"] select') ||
                     document.querySelector('.ol_style_toolbar [name="layout_background"] input') ||
                     document.querySelector('.ol_style_toolbar [name="layout_background"]');
        if (bgEl) {
            const val = (bgEl.value || bgEl.textContent || "").trim();
            if (val) bgType = val;
        }
        bgType = bgType || "Blank";
        const bgImg = data.layout_background_image;

        const paper = document.querySelector(".ol_paper");
        if (!paper) return;

        paper.style.setProperty("--ol-p-color", pColor);
        paper.style.setProperty("--ol-s-color", sColor);
        paper.style.setProperty("--ol-p-color-rgb", hexToRgb(pColor));
        paper.style.setProperty("--ol-s-color-rgb", hexToRgb(sColor));

        // Live background reflection on the paper
        paper.classList.remove("ol_bg_geometric", "ol_bg_custom", "ol_bg_blank");
        const bgLower = String(bgType).toLowerCase();
        if (bgLower.includes("custom") && bgImg) {
            paper.classList.add("ol_bg_custom");
            paper.style.backgroundImage = `url(data:image/png;base64,${bgImg})`;
            paper.style.backgroundRepeat = "no-repeat";
            paper.style.backgroundPosition = "center";
            paper.style.backgroundSize = "contain";
        } else if (bgLower.includes("geometric")) {
            paper.classList.add("ol_bg_geometric");
            const pRgb = hexToRgb(pColor);
            const sRgb = hexToRgb(sColor);
            const svgPattern = `<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'>` +
                `<g fill='none' stroke='rgba(${pRgb}, 0.20)' stroke-width='1.2'>` +
                `<polygon points='40,4 76,40 40,76 4,40'/>` +
                `<circle cx='40' cy='40' r='18'/>` +
                `</g>` +
                `<g fill='none' stroke='rgba(${sRgb}, 0.12)' stroke-width='0.8'>` +
                `<polygon points='40,16 64,40 40,64 16,40'/>` +
                `</g>` +
                `</svg>`;
            paper.style.backgroundImage = `url("data:image/svg+xml,${encodeURIComponent(svgPattern)}")`;
            paper.style.backgroundRepeat = "repeat";
            paper.style.backgroundPosition = "top left";
            paper.style.backgroundSize = "80px 80px";
        } else {
            paper.classList.add("ol_bg_blank");
            paper.style.backgroundImage = "none";
        }

        // Live format reflection on the paper (Folder, Boxed, Bold, Striped, Bubble, Wave, Light)
        paper.classList.remove(
            "ol_layout_folder",
            "ol_layout_boxed",
            "ol_layout_bold",
            "ol_layout_striped",
            "ol_layout_bubble",
            "ol_layout_wave",
            "ol_layout_light"
        );
        const lower = String(layoutName).toLowerCase();
        if (lower.includes("folder")) {
            paper.classList.add("ol_layout_folder");
        } else if (lower.includes("boxed")) {
            paper.classList.add("ol_layout_boxed");
        } else if (lower.includes("bold")) {
            paper.classList.add("ol_layout_bold");
        } else if (lower.includes("striped")) {
            paper.classList.add("ol_layout_striped");
        } else if (lower.includes("bubble")) {
            paper.classList.add("ol_layout_bubble");
        } else if (lower.includes("wave")) {
            paper.classList.add("ol_layout_wave");
        } else {
            paper.classList.add("ol_layout_light");
        }
    }

    get currentId() {
        return this.props.record?.resId || 0;
    }

    async _loadLetters() {
        try {
            this.state.letters = await this.orm.searchRead(
                "outgoing.letter",
                [],
                ["name", "date", "state", "title", "content", "approved_by_id"],
                { limit: 100, order: "id desc" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    approverName(val) {
        if (!val) return "";
        if (Array.isArray(val)) return val[1] || "";
        if (typeof val === "object") return val.display_name || val.name || "";
        return String(val);
    }

    get filteredLetters() {
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (!q) return this.state.letters;
        return this.state.letters.filter(l => {
            const name = (l.name || "").toLowerCase();
            const date = (l.date || "").toLowerCase();
            const approver = this.approverName(l.approved_by_id).toLowerCase();
            const title = (l.title || "").toLowerCase();
            const snippet = this.snippet(l.content).toLowerCase();
            const state = (this.stateLabel(l.state) || "").toLowerCase();
            return (
                name.includes(q) ||
                date.includes(q) ||
                approver.includes(q) ||
                title.includes(q) ||
                snippet.includes(q) ||
                state.includes(q)
            );
        });
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    clearSearch() {
        this.state.searchQuery = "";
    }

    stateLabel(state) {
        return STATE_LABELS[state] || state;
    }

    /** Strip HTML tags for a plain-text snippet */
    snippet(html) {
        if (!html) return "";
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        const text = tmp.textContent || "";
        return text.trim().slice(0, 60) || "";
    }

    async openLetter(id) {
        if (id === this.currentId) return;
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "outgoing.letter",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openCompany() {
        if (this.props.record && this.props.record.isDirty) {
            await this.props.record.save();
        }
        let companyId = this.props.record?.data?.company_id?.[0];
        if (!companyId) {
            const companies = await this.orm.search("res.company", [], { limit: 1 });
            companyId = companies[0] || 1;
        }
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Company & Letterhead",
            res_model: "res.company",
            res_id: companyId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openDocumentLayout() {
        return this.openCompany();
    }

    async newLetter() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "outgoing.letter",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("view_widgets").add("letter_sidebar", {
    component: LetterSidebarWidget,
});
