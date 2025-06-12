/* @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { useDebounced } from "@web/core/utils/timing";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";
import { Component, useRef, useState, onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc_service";

patch(ExportDataDialog.prototype, {
    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.draggableRef = useRef("draggable");
        this.exportListRef = useRef("exportList");
        this.searchRef = useRef("search");

        this.knownFields = {};
        this.expandedFields = {};
        this.availableFormats = [];
        this.templates = [];

        this.state = useState({
            exportList: [],
            isCompatible: false,
            isEditingTemplate: false,
            search: [],
            selectedFormat: 0,
            templateId: null,
            isSmall: this.env.isSmall,
            disabled: false,
            isAdmin: false,
        });

        this.title = _t("Export Data");
        this.newTemplateText = _t("New template");
        this.removeFieldText = _t("Remove field");

        this.debouncedOnResize = useDebounced(this.updateSize, 300);

        useSortable({
            // Params
            ref: this.draggableRef,
            elements: ".o_export_field",
            enable: !this.state.isSmall,
            cursor: "grabbing",
            // Hooks
            onDrop: async ({ element, previous, next }) => {
                const indexes = [element, previous, next].map(
                    (e) =>
                        e &&
                        Object.values(this.state.exportList).findIndex(
                            ({ id }) => id === e.dataset.field_id
                        )
                );
                let target;
                if (indexes[0] < indexes[1]) {
                    target = previous ? indexes[1] : 0;
                } else {
                    target = next ? indexes[2] : this.state.exportList.length - 1;
                }
                this.onDraggingEnd(indexes[0], target);
            },
        });

        onWillStart(async () => {
            this.availableFormats = await this.rpc("/web/export/formats");
            this.templates = await this.orm.searchRead(
                "ir.exports",
                [["resource", "=", this.props.root.resModel]],
                [],
                {
                    context: this.props.context,
                }
            );
            await this.fetchFields();

            const user_group_update_data = await this.rpc("/web/dataset/call_kw", {
            model: "res.users",
            method: "has_group",
            args: ["tasc_export.group_show_i_want_to_update_data_user"],
            kwargs: {},
            });
            this.state.isAdmin =  user_group_update_data;
        });

        onMounted(() => {
            browser.addEventListener("resize", this.debouncedOnResize);
            this.updateSize();
        });

        onWillUnmount(() => browser.removeEventListener("resize", this.debouncedOnResize));
    }

});