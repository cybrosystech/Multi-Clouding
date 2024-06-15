/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
const userMenuRegistry = registry.category("user_menuitems");

patch(UserMenu.prototype, {
setup() {
super.setup();
userMenuRegistry.remove("documentation");
userMenuRegistry.remove("profile");
userMenuRegistry.remove("odoo_account");
},

});