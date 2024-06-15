odoo.define('cash_flow_statement_report.cash_flow_report', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var Context = require('web.Context');
var session = require('web.session');
var QWeb = core.qweb;

var cashFlowReportWidget = AbstractAction.extend({
    hasControlPanel: true,

    events: {
        'click .js_cashflow_report_date_filter': 'filter_click',
        'click .js_cashflow_report_comparison_filter': 'comparison_click',
        'click .js_cashflow_report_journal_filter': 'posted_click',
        'click [action]': 'trigger_action',
        'click .inner_click': 'prevent_menu',
        'click #custom_filter_btn': 'custom_filter_apply',
        'click .comparison_previous_period_filter_btn': 'comparison_previous_period_filter_apply',
        'click .comparison_same_period_last_year_filter_btn': 'comparison_same_period_last_year_filter_apply',
        'click .inner_click_previous_period': 'prevent_menu_previous_click',
        'click .inner_click_last_year_previous_period': 'prevent_menu_last_year_previous_click',
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
            $buttons: this.$buttons,

        };
        await this._super(...arguments);
        this.render_template();
    },
    parse_reports_informations: function(values) {
        this.buttons = values.buttons;
        this.$searchview_buttons = $(values.searchview_html);
        this.main_html = values.main_html;
        this.report_options = values.options;
        this.render_options();
    },

    renderButtons: function(){
        this.$buttons = $(QWeb.render("cash_flow_report.buttons", {buttons: this.buttons}));
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
        this.render_values()
    },

    comparison_click: function(e) {
    var comparison_filter = e.target.attributes['data-filter'].value;
    this.report_options['comparison'] = comparison_filter;
    this.render_values()
    },

    prevent_menu: function(e){
        e.stopPropagation();
        var panel_custom = this.$('#custom_date')
        if (panel_custom[0].style.display === "block") {
          panel_custom[0].style.display = "none";
        } else {
          panel_custom[0].style.display = "block";
        }
    },
        prevent_menu_previous_click: function(e){
        console.log("uuuuuuuuuuuuu");
        e.stopPropagation();
        var panel_custom = this.$('#cmp_previous_period')
        if (panel_custom[0].style.display === "block") {
          panel_custom[0].style.display = "none";
        } else {
          panel_custom[0].style.display = "block";
        }
    },

    prevent_menu_last_year_previous_click: function(e){
        console.log("yyyyyyyyyy");
        e.stopPropagation();
        var panel_custom = this.$('#cmp_last_year_previous_period')
        if (panel_custom[0].style.display === "block") {
          panel_custom[0].style.display = "none";
        } else {
          panel_custom[0].style.display = "block";
        }
    },
//    comparison_custom_click: function(e){
//        console.log("rrrrrrrrrr");
//        e.stopPropagation();
//        var panel_custom = this.$('#comparison_custom_date')
//        if (panel_custom[0].style.display === "block") {
//          panel_custom[0].style.display = "none";
//        } else {
//          panel_custom[0].style.display = "block";
//        }
//    },

    custom_filter_apply: function(e){
        console.log("uuuuuuuuuuuuuuuuuu");
        var from_date = this.$('#from_date')
        var to_date = this.$('#to_date')
        this.report_options['date_filter'] = 'custom';
        this.report_options['custom_from'] = from_date.val();
        this.report_options['custom_to'] = to_date.val();
        this.render_values()
    },
    comparison_previous_period_filter_apply: function(e){
        console.log("wwwwwwwwwww",this);
        var number_period = this.$('#periods_number')
        console.log("qqqqqqqqqqqq",number_period.val());
        this.report_options['comparison'] = 'previous_period';
        this.report_options['number_period'] = number_period.val();
        console.log("hhhhhhhhhhhhhh");
        this.render_values()
    },
    comparison_same_period_last_year_filter_apply: function(e){
        console.log("iiiiiiiiiiiiiiiiii",this);
        var number_period = this.$('#last_year_periods_number')
        console.log("qqqqqqqqqqqq",number_period.val());
        this.report_options['comparison'] = 'same_period_last_year';

        this.report_options['number_period'] = number_period.val();
        console.log("hhhhhhhhhhhhhh");
        this.render_values()
    },

    posted_click: function(e) {
        var journal_filter = e.target.attributes['data-filter'].value;
        if (journal_filter == 'unfold'){
            var $table_row = this.$el.find('.child_lines')
            _.each($table_row, function (el) {
                if (el.style.display == "none"){
                    el.style.display = "";
                    e.target.text = 'Fold All';
                }
                else{
                    el.style.display = "none";
                    e.target.text = 'Unfold all';
                }
            });
        }
        else{
        this.report_options['entry'] = journal_filter;
        this.render_values()
        }

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

    trigger_action: function(e) {
        e.stopPropagation();
        var self = this;
        var action = $(e.target).attr('action');
        var id = $(e.target).parents('td').data('id');
        var params = $(e.target).data();
        var context = new Context(this.odoo_context, params.actionContext || {}, {active_id: id});
        if (action) {
            return this._rpc({
                    model: this.report_model,
                    method: action,
                    args: [this.financial_id, this.report_options, params],
                    context: context.eval(),
                })
                .then(function(result){
                    return self.do_action(result);
                });
        }

    },

    render_values: function() {
        var self = this;
        console.log("pppppppppppp",self)
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