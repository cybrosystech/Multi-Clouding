odoo.define('analytical_type.project_type', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var FieldManagerMixin = require('web.FieldManagerMixin');
    var relational_fields = require('web.relational_fields');
    var basic_fields = require('web.basic_fields');
    var core = require('web.core');
    var time = require('web.time');
    var session = require('web.session');
    var qweb = core.qweb;
    var _t = core._t;
    var NewLineRenderer = require('account.ReconciliationRenderer');

NewLineRenderer.LineRenderer.include({

      events: {
        'click .accounting_view caption .o_buttons button': '_onValidate',
        'click .accounting_view tfoot': '_onChangeTab',
        'click': '_onTogglePanel',
        'click .o_field_widget': '_onStopPropagation',
        'keydown .o_input, .edit_amount_input': '_onStopPropagation',
        'click .o_notebook li a': '_onChangeTab',
        'click .cell': '_onEditAmount',
        'change input.filter': '_onFilterChange',
        'click .match .load-more a': '_onLoadMore',
        'click .match .mv_line td': '_onSelectMoveLine',
        'click .accounting_view tbody .mv_line td': '_onSelectProposition',
        'click .o_reconcile_models button': '_onQuickCreateProposition',
        'click .create .add_line': '_onCreateProposition',
        'click .reconcile_model_create': '_onCreateReconcileModel',
        'click .reconcile_model_edit': '_onEditReconcileModel',
        'keyup input': '_onInputKeyup',
        'blur input': '_onInputKeyup',
        'keydown': '_onKeydown',
        'change tr.create_project_site_id': '_onProjectChange',
    },
//    events: _.extend({}, LineRenderer.prototype.events, {
//        'change .create_project_site_id': '_onProjectChange'
//    }),
//
    _onProjectChange: function (event) {
        console.log('Filter');
    },

    _renderCreate: function (state) {
        var self = this;
        return this.model.makeRecord('account.bank.statement.line', [{
            relation: 'account.account',
            type: 'many2one',
            name: 'account_id',
            domain: [['company_id', '=', state.st_line.company_id], ['deprecated', '=', false]],
        }, {
            relation: 'account.journal',
            type: 'many2one',
            name: 'journal_id',
            domain: [['company_id', '=', state.st_line.company_id], ['type', '=', 'general']],
        }, {
            relation: 'account.tax',
            type: 'many2many',
            name: 'tax_ids',
            domain: [['company_id', '=', state.st_line.company_id]],
        }, {
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'analytic_account_id',
            domain: ["|", ['company_id', '=', state.st_line.company_id], ['company_id', '=', false], ['analytic_account_type', '=', 'cost_center']],
        }, {
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'project_site_id',
            domain: ["|","&", ['company_id', '=', state.st_line.company_id],['company_id', '=', false], ['analytic_account_type', '=', 'project_site']],
        },{
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'location_id',
            domain: ["|","&", ['company_id', '=', state.st_line.company_id],['company_id', '=', false], ['analytic_account_type', '=', 'location']],
        },{
            relation: 'account.analytic.account',
            type: 'many2one',
            name: 'type_id',
            domain: ["|","&",['company_id', '=', state.st_line.company_id],['company_id', '=', false], ['analytic_account_type', '=', 'type']],
        },{
            relation: 'account.analytic.tag',
            type: 'many2many',
            name: 'analytic_tag_ids',
            domain: ["|", ['company_id', '=', state.st_line.company_id], ['company_id', '=', false]],
        }, {
            type: 'boolean',
            name: 'force_tax_included',
        }, {
            type: 'char',
            name: 'name',
        }, {
            type: 'float',
            name: 'amount',
        }, {
            type: 'date',
            name: 'date',
        }, {
            type: 'boolean',
            name: 'to_check',
        }], {
            account_id: {
                string: _t("Account"),
            },
            name: {string: _t("Label")},
            amount: {string: _t("Account")},
        }).then(function (recordID) {
            self.handleCreateRecord = recordID;
            var record = self.model.get(self.handleCreateRecord);

            self.fields.account_id = new relational_fields.FieldMany2One(self,
                'account_id', record, {mode: 'edit', attrs: {can_create:false}});

            self.fields.journal_id = new relational_fields.FieldMany2One(self,
                'journal_id', record, {mode: 'edit'});

            self.fields.tax_ids = new relational_fields.FieldMany2ManyTags(self,
                'tax_ids', record, {mode: 'edit', additionalContext: {append_type_to_tax_name: true}});

            self.fields.analytic_account_id = new relational_fields.FieldMany2One(self,
                'analytic_account_id', record, {mode: 'edit'});

            self.fields.project_site_id = new relational_fields.FieldMany2One(self,
                'project_site_id', record, {mode: 'edit'});

            self.fields.location_id = new relational_fields.FieldMany2One(self,
                'location_id', record, {mode: 'edit'});

            self.fields.type_id = new relational_fields.FieldMany2One(self,
                'type_id', record, {mode: 'edit'});

            self.fields.analytic_tag_ids = new relational_fields.FieldMany2ManyTags(self,
                'analytic_tag_ids', record, {mode: 'edit'});

            self.fields.force_tax_included = new basic_fields.FieldBoolean(self,
                'force_tax_included', record, {mode: 'edit'});

            self.fields.name = new basic_fields.FieldChar(self,
                'name', record, {mode: 'edit'});

            self.fields.amount = new basic_fields.FieldFloat(self,
                'amount', record, {mode: 'edit'});

            self.fields.date = new basic_fields.FieldDate(self,
                'date', record, {mode: 'edit'});

            self.fields.to_check = new basic_fields.FieldBoolean(self,
                'to_check', record, {mode: 'edit'});

            var $create = $(qweb.render("reconciliation.line.create", {'state': state, 'group_tags': self.group_tags, 'group_acc': self.group_acc}));
            self.fields.account_id.appendTo($create.find('.create_account_id .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.account_id));
            self.fields.journal_id.appendTo($create.find('.create_journal_id .o_td_field'));
            self.fields.tax_ids.appendTo($create.find('.create_tax_id .o_td_field'));
            self.fields.analytic_account_id.appendTo($create.find('.create_analytic_account_id .o_td_field'));
            self.fields.project_site_id.appendTo($create.find('.create_project_site_id .o_td_field'));
            self.fields.location_id.appendTo($create.find('.create_location_id .o_td_field'));
            self.fields.type_id.appendTo($create.find('.create_type_id .o_td_field'));
            self.fields.analytic_tag_ids.appendTo($create.find('.create_analytic_tag_ids .o_td_field'));
            self.fields.force_tax_included.appendTo($create.find('.create_force_tax_included .o_td_field'));
            self.fields.name.appendTo($create.find('.create_label .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.name));
            self.fields.amount.appendTo($create.find('.create_amount .o_td_field'))
                .then(addRequiredStyle.bind(self, self.fields.amount));
            self.fields.date.appendTo($create.find('.create_date .o_td_field'));
            self.fields.to_check.appendTo($create.find('.create_to_check .o_td_field'));
            self.$('.create').append($create);

            function addRequiredStyle(widget) {
                widget.$el.addClass('o_required_modifier');
            }
        });
    },

});
});

