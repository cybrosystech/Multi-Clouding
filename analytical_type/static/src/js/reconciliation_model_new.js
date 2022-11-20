odoo.define('analytical_type.ReconciliationModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var field_utils = require('web.field_utils');
var utils = require('web.utils');
var session = require('web.session');
var WarningDialog = require('web.CrashManager').WarningDialog;
var core = require('web.core');
var _t = core._t;
var NewStatementModel = require('account.ReconciliationModel');
//var NewManualModel = require('account.ReconciliationModel');


NewStatementModel.StatementModel.include({
    avoidCreate: false,
    quickCreateFields: ['account_id', 'amount', 'analytic_account_id','project_site_id','location_id',
    'type_id', 'name', 'tax_ids', 'force_tax_included', 'analytic_tag_ids', 'to_check'],

    // overridden in ManualModel
    modes: ['create', 'match_rp', 'match_other'],



      _formatQuickCreate: function (line, values) {
        values = values || {};
        var today = new moment().utc().format();
        var account = this._formatNameGet(values.account_id);
        var formatOptions = {
            currency_id: line.st_line.currency_id,
        };
        var amount = values.amount !== undefined ? values.amount : line.balance.amount;

        var prop = {
            'id': _.uniqueId('createLine'),
            'name': values.name || line.st_line.name,
            'account_id': account,
            'account_code': account ? this.accounts[account.id] : '',
            'analytic_account_id': this._formatNameGet(values.analytic_account_id),
            'project_site_id':this._formatNameGet(values.project_site_id),
            'location_id':this._formatNameGet(values.location_id),
            'type_id':this._formatNameGet(values.type_id),
            'analytic_tag_ids': values.analytic_tag_ids || [],
            'journal_id': this._formatNameGet(values.journal_id),
            'tax_ids': this._formatMany2ManyTagsTax(values.tax_ids || []),
            'tax_tag_ids': this._formatMany2ManyTagsTax(values.tax_tag_ids || []),
            'tax_repartition_line_id': values.tax_repartition_line_id,
            'tax_base_amount': values.tax_base_amount,
            'debit': 0,
            'credit': 0,
            'date': values.date ? values.date : field_utils.parse.date(today, {}, {isUTC: true}),
            'force_tax_included': values.force_tax_included || false,
            'base_amount': amount,
            'link': values.link,
            'display': true,
            'invalid': true,
            'to_check': !!values.to_check,
            '__tax_to_recompute': true,
            '__focus': '__focus' in values ? values.__focus : true,
        };
        if (prop.base_amount) {
            // Call to format and parse needed to round the value to the currency precision
            var sign = prop.base_amount < 0 ? -1 : 1;
            var amount = field_utils.format.monetary(Math.abs(prop.base_amount), {}, formatOptions);
            prop.base_amount = sign * field_utils.parse.monetary(amount, {}, formatOptions);
        }

        prop.amount = prop.base_amount;
        return prop;
    },

    _formatToProcessReconciliation: function (line, prop) {
        var amount = -prop.amount;
        if (prop.partial_amount) {
            amount = -prop.partial_amount;
        }

        var result = {
            name : prop.name,
            balance : amount,
            tax_exigible: prop.tax_exigible,
            analytic_tag_ids: [[6, null, _.pluck(prop.analytic_tag_ids, 'id')]]
        };
        if (!isNaN(prop.id)) {
            result.id = prop.id;
        } else {
            result.account_id = prop.account_id.id;
            if (prop.journal_id) {
                result.journal_id = prop.journal_id.id;
            }
        }
        if (prop.analytic_account_id) result.analytic_account_id = prop.analytic_account_id.id;
        if (prop.project_site_id) result.project_site_id = prop.project_site_id.id;
        if (prop.location_id) result.location_id = prop.location_id.id;
        if (prop.type_id) result.type_id = prop.type_id.id;
        if (prop.tax_ids && prop.tax_ids.length) result.tax_ids = [[6, null, _.pluck(prop.tax_ids, 'id')]];
        if (prop.tax_tag_ids && prop.tax_tag_ids.length) result.tax_tag_ids = [[6, null, _.pluck(prop.tax_tag_ids, 'id')]];
        if (prop.tax_repartition_line_id) result.tax_repartition_line_id = prop.tax_repartition_line_id;
        if (prop.tax_base_amount) result.tax_base_amount = prop.tax_base_amount;
        if (prop.reconcile_model_id) result.reconcile_model_id = prop.reconcile_model_id
        if (prop.currency_id) result.currency_id = prop.currency_id;
        return result;
    },
});
//NewManualModel.ManualModel.include({
//    quickCreateFields: ['account_id', 'journal_id', 'amount', 'analytic_account_id','cost_center_id', 'name', 'tax_ids', 'force_tax_included', 'analytic_tag_ids', 'date', 'to_check'],
//
//    modes: ['create', 'match'],
//
//    });
});