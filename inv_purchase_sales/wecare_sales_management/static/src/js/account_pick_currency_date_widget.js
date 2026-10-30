import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { Component, xml } from "@odoo/owl";

export class AccountPickCurrencyDateWidget extends Component {
    static props = {
        ...standardWidgetProps,
        "*": true,
    };
    static template = xml`<span class="o_account_pick_currency_date d-none"/>`;
}

export const accountPickCurrencyDateWidget = {
    component: AccountPickCurrencyDateWidget,
};

registry.category("view_widgets").add("account_pick_currency_date", accountPickCurrencyDateWidget);
