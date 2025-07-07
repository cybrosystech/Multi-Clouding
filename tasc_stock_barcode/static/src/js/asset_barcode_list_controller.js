/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";
export class AssetListController extends ListController {
   setup() {
       super.setup();
       this.orm = useService("orm");
       this.actionService = useService("action");
   }
   OnScanBrcodeClick() {
       this.actionService.doAction({
          type: 'ir.actions.client',
          tag: "tasManualBarcodeScanner",
          name:'Open Scanner',
          target: 'new'
      });
   }
   async OnValidateClick() {
        try {
            const selectedRecords = this.model.root.selection;

            if (selectedRecords.length > 0) {
                const selectedIds = selectedRecords.map(record => record.resId);
                await this.orm.write("asset.barcode", selectedIds, {
                    is_validated: true
                });

                await this.model.root.load();
            }

        } catch (error) {
//            console.error("Error validating records:", error);
        }
   }
}
registry.category("views").add("button_in_tree", {
   ...listView,
   Controller: AssetListController,
   buttonTemplate: "tasc_stock_barcode.ListView.Buttons",
});
