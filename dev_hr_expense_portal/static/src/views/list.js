/** @odoo-module */

import { registry } from '@web/core/registry';

import { listView } from '@web/views/list/list_view';
import { ListController } from '@web/views/list/list_controller';
import { ListRenderer } from "@web/views/list/list_renderer";
import { ExpenseListController } from "@hr_expense/views/list";
console.log("xxxxxxxxx");


export class DevHrExpenseExpenseListController extends ExpenseListController{
  setup() {
      console.log("yyyyyyyyy");
        super.setup();
        }

    displayCreateReportAllEmployees() {
        const records = this.model.root.selection;
        return !this.isExpenseSheet && (records.some(record => record.data.state === "draft"))
    }
        displayApproveExpense() {
        const records = this.model.root.selection;
        return (records.some(record => record.data.state === "waiting_approval"))
    }

        async action_show_expenses_to_submit_all_employees () {
        console.log("ppppppppp");
        const records = this.model.root.selection;
        const res = await this.orm.call(this.model.config.resModel, 'action_submit_expenses_all_employees', [records.map((record) => record.resId)]);
        if (res) {
        console.log("action_submit_expenses_all_employees");
//            await this.actionService.doAction(res, {});
        }
    }

        async action_approve () {
        console.log("ppppppppp");
        const records = this.model.root.selection;
        const res = await this.orm.call(this.model.config.resModel, 'action_approve', [records.map((record) => record.resId)]);
        if (res) {
        console.log("action_approve");
//            await this.actionService.doAction(res, {});
        }
    }
}


registry.category('views').add('dev_hr_expense_tree', {
    ...listView,
    buttonTemplate: 'dev_hr_expense_portal.ListButtons',
    Controller: DevHrExpenseExpenseListController,
});