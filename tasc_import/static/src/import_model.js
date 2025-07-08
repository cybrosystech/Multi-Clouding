/** @odoo-module **/

import { BaseImportModel } from "@base_import/import_model";
import { patch } from "@web/core/utils/patch";
patch(BaseImportModel.prototype, {
    async init() {
        await super.init(...arguments);
        this.importOptionsValues.tracking_disable.value = false;
    }
});