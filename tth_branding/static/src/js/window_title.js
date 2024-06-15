/** @odoo-module **/
import { useState,onMounted,useExternalListener,onWillStart } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { registry } from "@web/core/registry";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useBus, useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";

patch(WebClient.prototype, {
    /**
     * @override
     */
    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.title = useService("title");
        this.router = useService("router");
        this.user = useService("user");
        useOwnDebugContext({ categories: ["default"] });
        if (this.env.debug) {
            registry.category("systray").add(
                "web.debug_mode_menu",
                {
                    Component: DebugMenu,
                },
                { sequence: 100 }
            );
        }
        this.localization = localization;
        this.state = useState({
            fullscreen: false,
        });
        this.title.setParts({ zopenerp: "ERP" }); // zopenerp is easy to grep
        useBus(this.env.bus, "ROUTE_CHANGE", this.loadRouterState);
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", ({ detail: mode }) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
        onMounted(() => {
            this.loadRouterState();
            // the chat window and dialog services listen to 'web_client_ready' event in
            // order to initialize themselves:
            this.env.bus.trigger("WEB_CLIENT_READY");
        });
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
        onWillStart(this.registerServiceWorker);
    }

});
