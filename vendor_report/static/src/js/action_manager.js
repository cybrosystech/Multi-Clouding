/** @odoo-module */
import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { BlockUI } from "@web/core/ui/block_ui";

registry.category('ir.actions.report handlers').add('xlsx_report', async (action) => {
    if (action.report_type == 'xlsx_report') {
        BlockUI();
        await download({
            url: 'xlsx_report',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
    }
});