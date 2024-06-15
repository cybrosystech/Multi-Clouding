/** @odoo-module */
import { ListController } from '@web/views/list/list_controller';
import { useService } from '@web/core/utils/hooks';
import { patch } from '@web/core/utils/patch';
import { useState } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
patch(ListController.prototype, {
    async setup() {
        super.setup(...arguments);
        this.actionsService = useService('action');
        this.orm = useService('orm');
    },
    onClickVendorReport() {
        this.actionsService.doAction({
            name : _t('action wizard'),
            type: 'ir.actions.act_window',
            res_model: 'vendor.report.wizard',
            views: [[false, 'form']],
            view_mode: 'form',
            context: {},
            target: 'new',
        })
    }
})