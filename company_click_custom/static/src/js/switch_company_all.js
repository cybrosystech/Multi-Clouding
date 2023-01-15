odoo.define('company_click_custom.switch_company_all', function(require) {
"use strict";
var SwitchCompanyMenu = require('web.SwitchCompanyMenu');
var session = require('web.session');
console.log('SwitchCompanyMenu', SwitchCompanyMenu)

SwitchCompanyMenu.include ({
    events: _.extend({}, SwitchCompanyMenu.prototype.events, {
        'click .select_companies': 'on_select_all',
    }),

    on_select_all: function (ev) {
        console.log('heee', this.$el.find('.dropdown-item'))
        var dropdownelement = this.$el.find('.dropdown-item')
        var allowed_company_ids = this.allowed_company_ids;
        for (let i = 0; i < this.$el.find('.dropdown-item').length; i++) {
            var dropdownItem = dropdownelement[i]
            var companyID = dropdownItem.attributes['data-company-id'].value;
//            var allowed_company_ids = this.allowed_company_ids;
            var current_company_id = allowed_company_ids[0];
            allowed_company_ids.push(companyID);
            this.$el.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');

        }
        session.setCompanies(current_company_id, allowed_company_ids);
    },
});


});