/** @odoo-module **/

// require('web.dom_ready');

import { CharField } from "@web/views/fields/char/char_field";
import { onMounted, useEffect }from "@odoo/owl";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

export class MidIconSelectorBits extends CharField {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            if(this?.input?.el) {
                $(this.input.el).midiconpicker($(this.input.el));
            }
        })
    }

    async on_change(ev) {
        this.props.setDirty(true);
    }
}
MidIconSelectorBits.template = "IconSelectorBits"

export const midIconSelectorBits = {
    component: MidIconSelectorBits,
    displayName: _t("mid icon picker bits"),
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

registry.category("fields").add("mid_icon_picker_bits", midIconSelectorBits);
