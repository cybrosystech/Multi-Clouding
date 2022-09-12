odoo.define('vendor_report.vendor_report_wizard', function (require) {
"use strict";

    var core = require('web.core');
    var ListController = require('web.ListController');
    var _t = core._t;


    ListController.include({
        renderButtons: function($node) {
           this._super.apply(this, arguments);
               if (this.$buttons) {
                 this.$buttons.find('.new').click(this.proxy('get_so_lines')) ;
               }
        },
        get_so_lines: function () {
            this.do_action({
                _name : _t('action wizard'),
                type: 'ir.actions.act_window',
                res_model: 'vendor.report.wizard',
                views: [[false, 'form']],
                view_mode: 'form',
                context: {
                },
                target: 'new',
            });
        }
    })

});