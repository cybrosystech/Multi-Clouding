/** @odoo-module **/

import { CharField } from "@web/views/fields/char/char_field";
import { onMounted, useEffect }from "@odoo/owl";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

export class IconSelectorBits extends CharField {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if(this?.input?.el) {
                $(this.input.el).iconpicker($(this.input.el));
            }
        })
    }

    async on_change(ev) {
        this.props.setDirty(true);
    }
}
IconSelectorBits.template = "IconSelectorBits"

export const iconSelectorBits = {
    component: IconSelectorBits,
    displayName: _t("icon picker bits"),
    supportedTypes: ["char"],
    extractProps: ({ attrs, options }) => ({
        isPassword: archParseBoolean(attrs.password),
        dynamicPlaceholder: options.dynamic_placeholder || false,
        dynamicPlaceholderModelReferenceField:
            options.dynamic_placeholder_model_reference_field || "",
        autocomplete: attrs.autocomplete,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("icon_picker_bits", iconSelectorBits);
