odoo.define('cash_flow_statement_report.cash_flow_report', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var Context = require('web.Context');
var session = require('web.session');

var cashFlowReportWidget = AbstractAction.extend({
    hasControlPanel: true,

    events: {
        'click .js_cashflow_report_date_filter': 'filter_click',
        'click .js_cashflow_report_journal_filter': 'posted_click'
    },

    init: function(parent, action) {
       this.actionManager = parent;
        this.report_model = action.context.model;
        if (this.report_model === undefined) {
            this.report_model = 'cash.flow.statement';
        }
        this.financial_id = false;
        if (action.context.id) {
            this.financial_id = action.context.id;
        }
        this.odoo_context = action.context;
        this.report_options = action.params && action.params.options;
        this.ignore_session = action.params && action.params.ignore_session;
        if ((this.ignore_session === 'read' || this.ignore_session === 'both') !== true) {
            var persist_key = 'report:'+this.report_model+':'+this.financial_id+':'+session.company_id;
            this.report_options = JSON.parse(sessionStorage.getItem(persist_key)) || this.report_options;
        }
        return this._super.apply(this, arguments);
    },
    willStart: async function () {
        const reportsInfoPromise = this._rpc({
            model: this.report_model,
            method: 'get_cash_flow_information',
            args: [this.financial_id,''],
            context: this.odoo_context,
        }).then(res => this.parse_reports_informations(res));
        const parentPromise = this._super(...arguments);
        return Promise.all([reportsInfoPromise, parentPromise]);
    },
    start: async function() {
        this.renderButtons();
        this.controlPanelProps.cp_content = {
            $searchview_buttons: this.$searchview_buttons,

        };
        await this._super(...arguments);
        this.render_template();
    },
    parse_reports_informations: function(values) {
        this.$searchview_buttons = $(values.searchview_html);
        this.main_html = values.main_html;
        this.report_options = values.options;
        this.render_options();
    },

    render_options: function(values) {
        if ((this.ignore_session === 'write' || this.ignore_session === 'both') !== true) {
            var persist_key = 'report:'+this.report_model+':'+this.financial_id+':'+session.company_id;
            sessionStorage.setItem(persist_key, JSON.stringify(this.report_options));
        }
    },

    filter_click: function(e) {
        var date_filter = e.target.attributes['data-filter'].value;
        this.report_options['date_filter'] = date_filter;
        console.log('event', this.report_options)
        this.render_values()
    },

    posted_click: function(e) {
        var journal_filter = e.target.attributes['data-filter'].value;
        this.report_options['entry'] = journal_filter;
        console.log('event', this.report_options)
        this.render_values()
    },

    render_template: function() {
        this.$('.o_content').html(this.main_html);
    },

    update_cp: function() {
        var status = {
            cp_content: {
                $searchview_buttons: this.$searchview_buttons,
            },
        };
        return this.updateControlPanel(status);
    },

    render_values: function() {
        var self = this;
        return this._rpc({
                model: this.report_model,
                method: 'get_cash_flow_information',
                args: [this.financial_id, this.report_options],
                context: self.odoo_context,
            })
            .then(function(result){
                self.parse_reports_informations(result);
                self.render_template();
                return self.update_cp();
            });
    }

});

core.action_registry.add('cash_flow', cashFlowReportWidget);

return cashFlowReportWidget;

});