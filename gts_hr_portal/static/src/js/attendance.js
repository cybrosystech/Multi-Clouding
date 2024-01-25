odoo.define('gts_hr_portal.hr_portal_attendance', function(require) {
    'use strict';

    var rpc = require('web.rpc');
    var session = require('web.session');

    $(document).ready(function() {

        function convert(str) {
        var date = new Date().toLocaleString();
        return date
         }

        $("#check_in_button").click(function() {
            var self = this;
            var check_in = $('.gts_checkin');
            console.log("check_in",check_in);
            var employee_id = $(".employee_id");
            var check_out_date
            var status = Date();
            console.log("status",status);
            if (check_in) {
                self.status = convert(status);
                var values = {check_in:self.status,'write_uid':session.user_id}
            }
            rpc.query({
                    model: 'hr.attendance',
                    method: 'create_attendance',
                    args: [[values],values],
                })
                .then(function (result){
                    if (result) {
                        alert(result);
                    }
                    location.reload();
            });
        });

        $("#check_out_button").click(function() {
            var self = this;
            var check_out = $('.gts_checkout');
            var check_out_date = Date();
            console.log("check_out_date",check_out_date);

            if (check_out) {
                self.check_out_date = convert(check_out_date);
                var values = {check_out:self.check_out_date,'write_uid':session.user_id}
            }
            
            rpc.query({
                    model: 'hr.attendance',
                    method: 'write_attendance',
                    args: [[values],values],
                })
                .then(function (result){
                    if (result) {
                        alert(result);
                    }
                    location.reload();
            });
        });


    });



});
