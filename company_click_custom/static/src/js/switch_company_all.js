odoo.define('company_click_custom.switch_company_all', function(require) {
"use strict";
var SwitchCompanyMenu = require('web.SwitchCompanyMenu');
var session = require('web.session');

SwitchCompanyMenu.include ({
    events: _.extend({}, SwitchCompanyMenu.prototype.events, {
        'click .select_companies': 'on_select_all',
        'click .deselect_companies': 'de_select_all',
    }),

    on_select_all: function (ev) {
        var dropdownelement = $(ev.currentTarget.parentElement).find('.dropdown-item')
        for (let i = 0; i < dropdownelement.length; i++) {
            var dropdownItem = $(dropdownelement[i]);
            var companyID = dropdownItem.data('company-id');
            var allowed_company_ids = this.allowed_company_ids;
            var current_company_id = allowed_company_ids[0];
            allowed_company_ids.push(companyID);
            dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'true');
        }
        session.setCompanies(current_company_id, allowed_company_ids);
    },
    de_select_all: function (ev) {
        var dropdownelement = $(ev.currentTarget.parentElement).find('.dropdown-item')
        for (let i = 0; i < dropdownelement.length; i++) {
            var dropdownItem = $(dropdownelement[i]);
            var companyID = dropdownItem.data('company-id');
            var allowed_company_ids = this.allowed_company_ids;
            var current_company_id = allowed_company_ids[0];
            allowed_company_ids.splice(allowed_company_ids.indexOf(companyID), 1);
            dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
            $(ev.currentTarget).attr('aria-checked', 'false');

        }
        session.setCompanies(current_company_id, allowed_company_ids);
    },
});


});