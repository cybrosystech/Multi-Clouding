odoo.define('tasc_pf_bs_report.multi_companies', function (require) {
'use strict';
var CashFlow = require('cash_flow_statement_report.cash_flow_report');

    CashFlow.include ({
        events: _.extend({}, CashFlow.prototype.events, {
        'click .js_multi_companies_filter': 'multi_companies_filter',
    }),

    multi_companies_filter: function (ev) {
        console.log(ev.target.attributes)
        var multi_companies = ev.target.attributes['data-filter'].value;
        this.report_options['multi_company'] = multi_companies;
        this.render_values()
    },

});
});