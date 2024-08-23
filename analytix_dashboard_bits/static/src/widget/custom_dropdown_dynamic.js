/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps, useState, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { archParseBoolean } from "@web/views/utils";
import { _t } from "@web/core/l10n/translation";

export class CustomCombinedFieldWidget extends Component {
  setup() {
    super.setup();
    this.state = useState({
      chart_groups: {},
      isUlAvailable: "",
      sources: [{ options: [] }],
    });
    this.orm = useService("orm");
    useEffect(() => {
      this.generate_value(this.props);
    })
    onWillStart(async () => {
      await this.generate_value(this.props);
    });
  }
  getTagProps(record) {
    return {
      id: record.id,
      text: record.text,
      colorIndex: 0,
      onDelete: !this.props.readonly
        ? () => this.deleteTag(record.id)
        : undefined,
      onKeydown: () => {},
    };
  }

  get tags() {
    try {
      const value = JSON.parse(this.props.record.data[this.props.name]);
      const arr = value.map((ele) => {
        return { id: ele.id, text: ele.display_name };
      });
      return arr.map((record) => this.getTagProps(record));
    } catch (err) {
      return [];
    }
  }

  async generate_value(props) {
    const self = this;
    const result = await this.orm.call(
      props.record.resModel,
      "get_dropdown_options",
      [props.record.data.id, props.record.data.b_trend_field_id[0], ""]
    );
    let newData = {};
    result.map((ele) => {
      newData[ele[0]] = ele[1];
    });
    this.state.chart_groups = newData;
    if (props.record.data[this.props.name]) {
      const val = JSON.parse(props.record.data[this.props.name]);
      val.map((ele) => {
        delete self.state.chart_groups[ele.id];
      });
    }
    try {
      const arr = Object.entries(this.state.chart_groups).map((ele) => {
        return { value: ele[0], label: ele[1] };
      });
      this.state.sources[0].options = arr;
    } catch (err) {
      this.state.sources.options = [];
    }
  }

  deleteTag(record) {
    let newJson = JSON.parse(this.props.record.data[this.props.name]);
    this.props.record.update(
      {[this.props.name]: JSON.stringify(newJson.filter((ele) => ele.id != record))}
    );
  }

  async onSelect(ev) {
    if (ev.value == -1) return;
    
    if (this.props.record.data[this.props.name].length == 0) {
      const d = [{}];
      d[0] = { id: ev.value, display_name: ev.label };
      await this.props.record.update({[this.props.name]: JSON.stringify(d)});
    } else {
      let newJson = JSON.parse(this.props.record.data[this.props.name]);
      newJson.push({ id: ev.value, display_name: ev.label });
      await this.props.record.update({[this.props.name]: JSON.stringify(newJson)});
    }
  }
}

CustomCombinedFieldWidget.template = "YaxisBits";
CustomCombinedFieldWidget.components = { TagsList, AutoComplete };

export const customCombinedFieldWidget = {
  component: CustomCombinedFieldWidget,
  displayName: _t("Combined Field widget"),
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

registry
  .category("fields")
  .add("custom_dropdown_dynamic", customCombinedFieldWidget);