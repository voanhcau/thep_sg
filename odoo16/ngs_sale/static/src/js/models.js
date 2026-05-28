/** @odoo-module **/

import {Order, Orderline} from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';
import { Gui } from 'point_of_sale.Gui';

const {parse} = require('web.field_utils');
import core from 'web.core';

const _t = core._t;

const PosTemplateOrder = (Order) => class PosTemplateOrder extends Order {

    async activateCode(code) {
        const res = await this._activateCode(code);
        if (res == true) {
            const rule = this.pos.rules.find((rule) => {
                return rule.mode === 'with_code' && (rule.promo_barcode === code || rule.code === code)
            });
            if (rule && rule['program_id'] && rule['program_id']['damaged_display_item']) {
                let valid_product_ids = []
                for (let product_id of rule['valid_product_ids']) {
                    valid_product_ids.push(product_id)
                }
                const order_lines = this.orderlines
                for (let i = 0; i < order_lines.length; i++) {
                    let order_line = order_lines[i]
                    if (valid_product_ids.indexOf(order_line.product.id) != -1) {
                        order_line.rule = rule
                    }
                }
            }
        } else {
            Gui.showNotification(res);
        }
        return res
    }
}
Registries.Model.extend(Order, PosTemplateOrder);

const PosTemplateOrderLine = (Orderline) => class PosTemplateOrderLine extends Orderline {

    constructor(obj, options) {
        super(...arguments);
        if (!options.json) {
            this.rule = null
        }
    }

    export_as_JSON() {
        const result = super.export_as_JSON(...arguments);
        if (this.rule) {
            result['rule_id'] = this.rule.id
        }
        return result;
    }

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.rule) {
            result['rule'] = this.rule
        }
        return result;
    }

    init_from_JSON(json) {
        if (json.rule_id) {
            const rule = this.pos.rules.find((rule) => {
                return rule.id === json.rule_id
            });
            if (rule) {
                this.rule = rule
            }
        }
        super.init_from_JSON(...arguments);
    }

}
Registries.Model.extend(Orderline, PosTemplateOrderLine);

