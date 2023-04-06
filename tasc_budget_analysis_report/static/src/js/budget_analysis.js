odoo.define('tasc_budget_analysis_report.budget_analysis_report', function (require) {
'use strict';
var CashFlow = require('cash_flow_statement_report.cash_flow_report');
CashFlow.include ({
        events: _.extend({}, CashFlow.prototype.events, {
        'click .tr_budget': 'budget_sub_line',
        'click .js_budget_analysis_budget_filter': 'budget_filter',
    }),

    budget_sub_line: function (ev) {
        var data_id = ev.target.attributes['data-id'].value;
        var datas = $('.'+ data_id)

        datas.each((line) => {
            if (datas[line].style.display === "") {
                datas[line].style.display = "none";
            } else {
              datas[line].style.display = "";
            }
        });
    },

    budget_filter: function (ev){
        var budget_filter = ev.target.attributes['data-id'].value;
        var budget_name = ev.target.attributes['title'].value;
        this.report_options['budget_filter'] = budget_filter;
        this.report_options['budget_name'] = budget_name;
        this.render_values()
    },

    });
});