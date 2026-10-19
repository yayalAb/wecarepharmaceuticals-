/** @odoo-module **/

import { Component } from "@odoo/owl";

export class DashboardCard extends Component {
    static template = "wecare_executive_dashboard.DashboardCard";
    static defaultProps = {
        iconColor: "blue",
        badgeColor: "gray",
        clickable: false,
    };

    static props = {
        title: String,
        value: [String, Number],
        subtext: { type: String, optional: true },
        icon: { type: String, optional: true },
        iconColor: { type: String, optional: true }, // 'blue', 'green', 'amber', 'sky', 'purple', 'orange', 'teal', 'red'
        badgeText: { type: String, optional: true },
        badgeColor: { type: String, optional: true }, // 'gray', 'blue', 'green', 'amber', 'red', 'cyan'
        clickable: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
    };

    onCardClick() {
        if (this.props.onClick && typeof this.props.onClick === "function") {
            this.props.onClick();
        }
    }
}
