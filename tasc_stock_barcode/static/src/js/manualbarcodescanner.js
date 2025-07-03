/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import * as BarcodeScanner from '@web/webclient/barcode/barcode_scanner';
import { registry } from "@web/core/registry";

export class tasManualBarcodeScanner extends Component {
    setup() {
        this.title = _t("Barcode Manual Entry");
        this.orm = useService("orm");
        this.state = useState({
            'barcode': false,
        });
         this.action = useService("action");
        this.barcodeManual = useRef('manualBarcode');
        onMounted(() => {
            this.barcodeManual.el.focus();
        });
    }

    _onApply() {
        if (this.state.barcode) {
            this.orm.call('asset.barcode', 'barcode_search', [this.state.barcode,this.props.action.context.active_id])
            setTimeout(() => {
                this.action.doAction("soft_reload")
            }, 700);
        }
    }

    onBarcodeScanned(barcode) {
        this.orm.call('asset.barcode', 'barcode_search', [barcode,this.props.action.context.active_id])
        setTimeout(() => {
        this.action.doAction("soft_reload")
        }, 700);
    }

    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode(this.env);
        this.onBarcodeScanned(barcode);
    }

    _onBarcodeScan() {
        this.openMobileScanner();
    }

    _onKeydown(ev) {
        if (ev.key === 'Enter') {
            this._onApply(ev);
        }
    }
}

tasManualBarcodeScanner.components = { Dialog };

tasManualBarcodeScanner.template = "tasc_stock_barcode.ManualBarcodeScanner";

registry.category("actions").add("tasManualBarcodeScanner", tasManualBarcodeScanner);

