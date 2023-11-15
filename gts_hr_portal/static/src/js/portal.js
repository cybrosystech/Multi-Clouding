odoo.define('gts_hr_portal.hr_portal', function(require) {
    'use strict';

    var rpc = require('web.rpc');
    $(document).ready(function() {

        $("#select_holiday_status_id").change(function(event){
            var holiday_status_id = $('#select_holiday_status_id').val();
            console.log('holiday_status_id........' + holiday_status_id);
            var employee_id = $('#hidden_employee_id').val();
            console.log('employee_id........' + employee_id);
            if (!holiday_status_id) {
                return;
            }
            if (!employee_id) {
                return;
            }
            rpc.query({
                route: "/get/employee/leaves/count/" + employee_id + '/' + holiday_status_id
            }).then(function(remaining_leaves) {
                console.log('remaining_leaves....' + remaining_leaves)
                var show_remaining_leaves_details = $("div[id='show_remaining_leaves_details']");
                var show_remaining_leaves_title = $("span[id='show_remaining_leaves_title']");
                var show_remaining_leaves_value = $("span[id='show_remaining_leaves_value']");
                show_remaining_leaves_details.removeClass('hidden');
                show_remaining_leaves_value.val(remaining_leaves);
            });
        });

        $("#leave_form_submit").click(function() {
            console.log('leave_form_submit...');
            var holiday_status_id = $('#select_holiday_status_id').val();
            var request_date_from = $('#request_date_from').val();
            var request_date_to = $('#request_date_to').val();
//            console.log('holiday_status_id........' + holiday_status_id);
             
            console.log('request_date_from........' + request_date_from);
            console.log('request_date_to........' + request_date_to);
            if (request_date_from !== null && request_date_to !== null && request_date_to < request_date_from) {
                alert('Date From must be less than Date To !')
            }
        });
    });

});
