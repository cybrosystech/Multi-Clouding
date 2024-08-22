/** @odoo-module **/

import {
  Component,
  onWillStart,
  onMounted,
  useState,
  useRef,
  onWillUnmount,
} from "@odoo/owl";
import Dialog from "@web/legacy/js/core/dialog";
import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class DashboardViewControllerBits extends Component {
  setup() {
    super.setup();
    this.rpc = useService("rpc");
    this.orm = useService("orm");
    this.state = useState({});
    this.action = useService("action");
    this.notification = useService("notification");
    this.state.dashboard_data = [];
    this.state.orderFormat = "Default";
    this.el = useRef("el");

    onWillStart(async () => {
      this.state.dashboard_data = [];
      this.state.orderFormat = "Default";
      this.state.hasAccess = false;
    });
    onMounted(async () => {
      document.addEventListener("click", (ev) => {
        $("body *").removeClass("show");
      });
      await this._fetch_dashboards("");
    });

    onWillUnmount(() => {
      document.removeEventListener("click", (ev) => {
        $("body *").removeClass("show");
      });
    });
  }

  async onSelectOrder(ev) {
    ev.stopPropagation();
    $("body *").removeClass("show");
    $(ev.target)?.toggleClass("show");
    this.orderFormat = $(ev.target)?.data()?.orderFormat
      ? $(ev.target)?.data()?.orderFormat
      : "Default";
    await this._fetch_dashboards("");
  }

  toggleDropdownClass(ev) {
    const parent = $(ev.target).parent();
    ev.stopPropagation();
    $("body *").removeClass("show");
    parent.find(".dropdown-menu")?.toggleClass("show");
  }

  sortDashboardData() {
    this.state.dashboard_data = [...this.state.dashboard_data].sort((a, b) => {
      // Convert names to lowercase for case-insensitive sorting
      const nameA = a.name.toLowerCase();
      const nameB = b.name.toLowerCase();

      // Compare the names
      if (nameA < nameB) {
        return this.orderFormat == "ASC" ? -1 : 1;
      }
      if (nameA > nameB) {
        return this.orderFormat == "ASC" ? 1 : -1;
      }
      // Names are equal
      return 0;
    });
  }

  onClickImpDasboard(e) {
    this.action.doAction({
      // name: _t(name),
      type: "ir.actions.act_window",
      res_model: "import.dashboard",
      // res_id: parseInt(rid),
      view_mode: "form",
      views: [[false, "form"]],
      target: "new",
    });
  }
  _AddNewDashboard(ev) {
    ev.preventDefault();
    this.action.doAction({
      type: "ir.actions.act_window",
      name: _t("New Dashboard"),
      res_model: "dashboard.bits",
      views: [[false, "form"]],
    });
  }
  async _OpenDashboard(ev) {
    var action_data = $(ev.currentTarget).data();
    $("body").append(
      '<div id="cover" style="position: fixed; min-width: 100vw; min-height: 100vh; opacity: 0.5; color: white; top: 0; left: 0;"></div>'
    );
    await this.action.doAction({
      type: "ir.actions.client",
      id: action_data.caid,
      tag: "bits_dashboard_action",
      context: {
        params: {
          dashboard_id: action_data.did,
          default_color_theme: action_data.color_theme || false,
          default_time_frame: action_data.tframe,
          default_view_mode: action_data.view_mode,
        },
      },
    });
    $("body").find("#cover").remove();
  }
  async _fetch_dashboards(src) {
    const dashboard_data = await this.orm.call(
      "dashboard.bits",
      "get_dashboards",
      [[], src]
    );
    this.state.dashboard_data = dashboard_data?.dashboards
      ? dashboard_data?.dashboards
      : [];
    this.state.hasAccess = Boolean(dashboard_data?.has_group_admin_bits);
    this.search = dashboard_data.search;
    if (this.orderFormat != "Default") {
      this.sortDashboardData();
    }
  }
  onClickEditDashboard(e) {
    var $target = $(e.currentTarget).parent().parent().data();
    e.stopPropagation();
    e.preventDefault();
    this.action.doAction({
      name: _t("Dashboard"),
      type: "ir.actions.act_window",
      views: [[false, "form"]],
      res_model: "dashboard.bits",
      res_id: $target.did,
      flags: { mode: "edit" },
      context: { create: false },
    });
  }
  onClickDeleteDashboard(e) {
    var self = this;
    e.stopPropagation();
    var $target = $(e.currentTarget).parent().parent().data();
    var dialog = new Dialog(this, {
      title: _t("Delete Dashboard"),
      $content: "<h3>Are you sure you want to delete ?</h3> ",
      size: "medium",
      buttons: [
        {
          text: _t("Yes"),
          classes: "btn-primary",
          close: true,
          click() {
            self.deleteDashboard($target.did);
          },
        },
        {
          text: _t("No"),
          classes: "btn-primary",
          close: true,
        },
      ],
    });
    dialog.open();
  }
  async deleteDashboard(rec_id) {
    var self = this;
    // removed direct unlink method bcase of delete
    await this.orm
      .call("dashboard.bits", "unlink_dashboard_bits", [[rec_id]])
      .then(async function () {
        await self._fetch_dashboards("");
      });
  }
  async onSearchInput(e) {
    var target = $(e.currentTarget);
    e.preventDefault();
    if (target.val().trim() == "") {
      await this._fetch_dashboards("");
    } else {
      await this._fetch_dashboards(target.val());
    }
  }
} 

DashboardViewControllerBits.template = "DashboardViewControllerBits";
registry
  .category("actions")
  .add("bits_all_dashboard_action", DashboardViewControllerBits);