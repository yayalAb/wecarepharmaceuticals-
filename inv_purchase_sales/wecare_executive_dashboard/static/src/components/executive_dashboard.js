/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { DashboardCard } from "./dashboard_card/dashboard_card";
import { ChartRenderer } from "./chart_renderer/chart_renderer";

export class WecareExecutiveDashboard extends Component {
    static template = "wecare_executive_dashboard.MainDashboard";
    static components = { DashboardCard, ChartRenderer };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            date_range: "mtd", // 'today', 'wtd', 'mtd', 'ytd', 'custom'
            date_from: "",
            date_to: "",
            period_label: "",
            customer_type: "all",
            territory_id: "all",
            collection_type: "all",
            filter_options: {
                customer_types: [],
                territories: [],
            },
            company_name: "WeCare Pharmaceuticals",
            currency: { symbol: "Br", position: "after", decimal_places: 0 },
            financial_kpis: {
                sales_this_month: 0,
                sales_selected_period: 0,
                sales_target: 0,
                target_achievement_pct: 0,
                target_variance: 0,
                total_receivables: 0,
                total_receivables_count: 0,
                overdue_receivables: 0,
                overdue_count: 0,
                overdue_pct: 0,
                invoice_count: 0,
            },
            cheque_kpis: {
                received_amount: 0,
                received_count: 0,
                in_clearing_amount: 0,
                in_clearing_count: 0,
                cleared_amount: 0,
                cleared_count: 0,
                bounced_amount: 0,
                bounced_count: 0,
            },
            sales_collection_analysis: {
                actual_sales: 0,
                target_sales: 0,
                achievement_pct: 0,
                collections_by_method: {
                    cheque: 0,
                    cash: 0,
                    bank_transfer: 0,
                    other: 0,
                    total: 0,
                },
                collection_counts: {
                    cheque: 0,
                    cash: 0,
                    bank_transfer: 0,
                    other: 0,
                },
                total_items: 0,
                chart_timeline: {
                    labels: [],
                    sales: [],
                    targets: [],
                },
            },
            action_center: [],
            top_customers: [],
            salesperson_performance: [],
            product_performance: [],
            salesperson_collections: [],
            bank_summary: [],
            cash_summary: {
                total_cash_collected_period: 0,
                cash_journals: [],
            },
            activePerformanceTab: "customers", // 'customers', 'salespeople', 'products', 'collections', 'banks'
            charts: {
                sales_target_timeline: null,
                collection_doughnut: null,
                top_customers_bar: null,
                salesperson_bar: null,
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "wecare.executive.dashboard",
                "get_dashboard_data",
                [],
                {
                    date_range: this.state.date_range,
                    date_from: this.state.date_from || false,
                    date_to: this.state.date_to || false,
                    customer_type: this.state.customer_type,
                    territory_id: this.state.territory_id,
                    collection_type: this.state.collection_type,
                }
            );

            this.state.company_name = data.company_name;
            this.state.currency = data.currency;
            this.state.period_label = data.period_label;
            this.state.date_from = data.date_from;
            this.state.date_to = data.date_to;
            this.state.filter_options = data.filter_options || { customer_types: [], territories: [] };
            this.state.financial_kpis = data.financial_kpis;
            this.state.cheque_kpis = data.cheque_kpis;
            this.state.sales_collection_analysis = data.sales_collection_analysis;
            this.state.action_center = data.action_center;
            this.state.top_customers = data.top_customers;
            this.state.salesperson_performance = data.salesperson_performance;
            this.state.product_performance = data.product_performance;
            this.state.salesperson_collections = data.salesperson_collections;
            this.state.bank_summary = data.bank_summary;
            this.state.cash_summary = data.cash_summary;

            this.prepareChartData(data);
        } catch (error) {
            console.error("Failed to load dashboard data:", error);
            this.notification.add(_t("Failed to load Executive Dashboard data."), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    prepareChartData(data) {
        const sc = data.sales_collection_analysis || {};
        const timeline = sc.chart_timeline || {};

        // 1. Sales vs Target Timeline Chart
        if (timeline.labels && timeline.labels.length) {
            this.state.charts.sales_target_timeline = {
                labels: timeline.labels,
                datasets: [
                    {
                        label: _t("Actual Sales"),
                        data: timeline.sales,
                        backgroundColor: "#1a73e8",
                        borderColor: "#1a73e8",
                        borderRadius: 6,
                    },
                    {
                        label: _t("Target"),
                        data: timeline.targets,
                        backgroundColor: "#10b981",
                        borderColor: "#10b981",
                        borderRadius: 6,
                        type: "line",
                        tension: 0.35,
                        pointRadius: 4,
                    },
                ],
            };
        } else {
            this.state.charts.sales_target_timeline = null;
        }

        // 2. Collection by Method Doughnut (Matching screenshot "Portfolio & Occupancy" Donut)
        const cm = sc.collections_by_method || {};
        const cmLabels = [_t("Cheque"), _t("Cash"), _t("Bank Transfer"), _t("Telebirr / Other")];
        const cmValues = [cm.cheque || 0, cm.cash || 0, cm.bank_transfer || 0, cm.other || 0];
        const hasCollections = cmValues.some((v) => v > 0);

        if (hasCollections) {
            this.state.charts.collection_doughnut = {
                labels: cmLabels,
                datasets: [
                    {
                        data: cmValues,
                        // Blue, Green, Amber, Coral palette matching screenshot
                        backgroundColor: ["#003f88", "#f97316", "#22c55e", "#eab308"],
                        borderWidth: 2,
                        borderColor: "#ffffff",
                    },
                ],
            };
        } else {
            // Default placeholder ring if zero
            this.state.charts.collection_doughnut = {
                labels: cmLabels,
                datasets: [
                    {
                        data: [1, 1, 1, 1],
                        backgroundColor: ["#e2e8f0", "#e2e8f0", "#e2e8f0", "#e2e8f0"],
                        borderWidth: 2,
                        borderColor: "#ffffff",
                    },
                ],
            };
        }

        // 3. Top Customers Bar Chart
        if (data.top_customers && data.top_customers.length) {
            const top5 = data.top_customers.slice(0, 6);
            this.state.charts.top_customers_bar = {
                labels: top5.map((c) => (c.name.length > 16 ? c.name.substring(0, 14) + "..." : c.name)),
                datasets: [
                    {
                        label: _t("Sales in Period"),
                        data: top5.map((c) => c.sales_amount),
                        backgroundColor: "#1a73e8",
                        borderRadius: 6,
                    },
                    {
                        label: _t("Outstanding"),
                        data: top5.map((c) => c.outstanding_balance),
                        backgroundColor: "#f43f5e",
                        borderRadius: 6,
                    },
                ],
            };
        } else {
            this.state.charts.top_customers_bar = null;
        }

        // 4. Salesperson Bar Chart
        if (data.salesperson_performance && data.salesperson_performance.length) {
            const topSp = data.salesperson_performance.slice(0, 6);
            this.state.charts.salesperson_bar = {
                labels: topSp.map((sp) => sp.name),
                datasets: [
                    {
                        label: _t("Target"),
                        data: topSp.map((sp) => sp.target),
                        backgroundColor: "#cbd5e1",
                        borderRadius: 6,
                    },
                    {
                        label: _t("Actual Sales"),
                        data: topSp.map((sp) => sp.actual),
                        backgroundColor: "#10b981",
                        borderRadius: 6,
                    },
                ],
            };
        } else {
            this.state.charts.salesperson_bar = null;
        }
    }

    // -------------------------------------------------------------------------
    // Formatters
    // -------------------------------------------------------------------------
    formatCurrency(amount) {
        if (amount === undefined || amount === null || isNaN(amount)) {
            return `0 ${this.state.currency?.symbol || "Br"}`;
        }
        const num = Math.round(Number(amount));
        const formatted = num.toLocaleString();
        const symbol = this.state.currency?.symbol || "Br";
        const pos = this.state.currency?.position || "after";
        return pos === "before" ? `${symbol} ${formatted}` : `${formatted} ${symbol}`;
    }

    formatNumber(num) {
        if (num === undefined || num === null || isNaN(num)) {
            return "0";
        }
        return Number(num).toLocaleString();
    }

    // -------------------------------------------------------------------------
    // Filter & Event Handlers
    // -------------------------------------------------------------------------
    async setDatePreset(presetKey) {
        this.state.date_range = presetKey;
        await this.loadData();
    }

    async onFilterChange(filterKey, ev) {
        this.state[filterKey] = ev.target.value;
        await this.loadData();
    }

    async onApplyCustomDate() {
        if (!this.state.date_from || !this.state.date_to) {
            this.notification.add(_t("Please select both start and end dates."), {
                type: "warning",
            });
            return;
        }
        if (this.state.date_from > this.state.date_to) {
            this.notification.add(_t("Start date cannot be after end date."), {
                type: "warning",
            });
            return;
        }
        this.state.date_range = "custom";
        await this.loadData();
    }

    async refresh() {
        await this.loadData();
    }

    onSelectTab(tabKey) {
        this.state.activePerformanceTab = tabKey;
    }

    // -------------------------------------------------------------------------
    // Drill-Down Actions
    // -------------------------------------------------------------------------
    openActionCenter(item) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: item.action_name || item.title,
            res_model: item.action_model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: item.action_domain || [],
            target: "current",
        });
    }

    openSalesInvoices() {
        const domain = [
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
            ["invoice_date", ">=", this.state.date_from],
            ["invoice_date", "<=", this.state.date_to],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Sales Invoices for Period"),
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    openTotalReceivables() {
        const domain = [
            ["move_type", "=", "out_invoice"],
            ["state", "=", "posted"],
            ["payment_state", "in", ["not_paid", "partial"]],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Total Outstanding Receivables"),
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    openOverdueReceivables() {
        const actionItem = this.state.action_center.find((a) => a.id === "overdue_invoices");
        if (actionItem) {
            this.openActionCenter(actionItem);
        }
    }

    openChequeRegisterByState(state, title) {
        const domain = [
            ["payment_type", "=", "inbound"],
            ["state", "=", state],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: title || _t("Cheques"),
            res_model: "wecare.cheque.register",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    openPartnerRecord(partnerId, partnerName) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: partnerName,
            res_model: "res.partner",
            res_id: partnerId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openProductRecord(productId, productName) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: productName,
            res_model: "product.product",
            res_id: productId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSalesPlans() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Sales Plans & Targets"),
            res_model: "wecare.sales.plan",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "approved"]],
            target: "current",
        });
    }

    printDashboard() {
        window.print();
    }
}

registry.category("actions").add("wecare_executive_dashboard.main_view", WecareExecutiveDashboard);
