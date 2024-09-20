/** @odoo-module **/
import {  useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ImportDataOptions } from "@base_import/import_data_options/import_data_options";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";


// Patching the ImportDataOptions component
patch(ImportDataOptions.prototype, {
    setup() {
        this.orm = useService("orm");
        this.user = useService("user");
        this.state = useState({
            options: [],
        });
        this.currentModel = this.props.fieldInfo.comodel_name || this.props.fieldInfo.model_name;
        onWillStart(async () => {
            this.state.options = await this.loadOptions();
        });
    },
        async loadOptions() {
        const options = [["prevent", _t("Prevent import")]];
        if (this.props.fieldInfo.type === "boolean") {
            options.push(["false", _t("Set to: False")]);
            options.push(["true", _t("Set to: True")]);
            !this.props.fieldInfo.required &&
                options.push(["import_skip_records", _t("Skip record")]);
        }
        if (["many2one", "many2many", "selection"].includes(this.props.fieldInfo.type)) {
            if (!this.props.fieldInfo.required) {
                options.push(["import_set_empty_fields", _t("Set value as empty")]);
                options.push(["import_skip_records", _t("Skip record")]);
            }
            if (this.props.fieldInfo.type === "selection") {
                const fields = await this.orm.call(this.currentModel, "fields_get");
                const selection = fields[this.props.fieldInfo.name].selection.map((opt) => [
                    opt[0],
                    _t("Set to: %s", opt[1]),
                ]);
                options.push(...selection);
            } else {
                if (this.user.id === 1 || await this.user.hasGroup('base.group_erp_manager') || await this.user.hasGroup('base.group_system'))
                {
                  options.push(["name_create_enabled_fields", _t("Create new values")]);

                }
            }
        }
        return options;
    }
});
