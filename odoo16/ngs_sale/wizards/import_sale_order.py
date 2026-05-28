# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import tempfile
import binascii
import datetime

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug("Cannot `import csv`.")

try:
    import xlrd
except ImportError:
    _logger.debug("Cannot `import xlrd`.")


class ImportSaleOrder(models.TransientModel):
    _name = "import.sale.order"
    _description = "Import Sale Order"

    attachment_ids = fields.Many2many(
        "ir.attachment", string="Files", required=True)

    def get_partner(self, value):
        partner = self.env["res.partner"].search([("name", "=", value)])
        return partner.id if partner else False

    def get_currency(self, value):
        currency = self.env["res.currency"].search([("name", "=", value)])
        return currency.id if currency else False

    def create_statement(self, values):
        statement = self.env["account.bank.statement"].create(values)
        return statement

    def import_file(self):
        for data_file in self.attachment_ids:
            file_name = data_file.name.lower()
            if file_name.strip().endswith(".xlsm") or file_name.strip().endswith(".xlsx"):
                statement = False
                try:
                    fp = None
                    if file_name.strip().endswith(".xlsm"):
                        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsm")
                    else:
                        fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    fp.write(binascii.a2b_base64(data_file.datas))
                    fp.seek(0)
                    values = {}
                    workbook = xlrd.open_workbook(fp.name)
                except:
                    raise ValidationError(
                        _("Error when parse file"))
                    return False
                import_done = False
                sale_ids = []
                for sheet in workbook.sheets():
                    sheet_name = sheet.name
                    if len(sheet_name.split("-")) != 2:
                        continue
                    try:
                        _logger.info(datetime.datetime.strptime(sheet_name, "%d-%m").strftime('%d-%m'))
                    except:
                        _logger.warning(">>>> sheet name could not import")
                        continue
                    if sheet_name != datetime.datetime.strptime(sheet_name, "%d-%m").strftime('%d-%m'):
                        continue
                    _logger.info(">>>>> checking sheet name %s" % sheet_name)
                    ws = workbook.sheet_by_name(sheet_name)
                    customer_name = ws.cell(11, 7).value
                    origin = ws.cell(12, 7).value
                    vals = {
                        "customer_name": customer_name,
                        "origin": origin,
                        "date_order": sheet_name,
                        "order_line": [],
                    }
                    default_code_col = base_price_col = product_uom_qty_col = quantity_another1_col = price_unit_col = purchase_uom_qty_col = None
                    for row_id in range(ws.nrows):
                        if row_id == 19:
                            for col in range(ws.ncols):
                                if ws.cell_value(row_id, col) == "MASP":
                                    default_code_col = col
                                if ws.cell_value(row_id, col) == "SL":
                                    quantity_another1_col = col
                                if ws.cell_value(row_id, col) == "KGBAN":
                                    product_uom_qty_col = col
                                if ws.cell_value(row_id, col) == "GIAMUA":
                                    base_price_col = col
                                if ws.cell_value(row_id, col) == "GIABAN":
                                    price_unit_col = col
                                if ws.cell_value(row_id, col) == "KGMUA":
                                    purchase_uom_qty_col = col
                        if row_id <= 20:
                            continue
                        default_code = ws.cell(row_id, default_code_col).value
                        if default_code in ["KEM", "VAS8C", "VAS10C3"]:
                            _logger.info("KEM")
                        if not default_code:
                            continue
                        price_unit = ws.cell(row_id, price_unit_col).value
                        product_uom_qty = ws.cell(row_id, product_uom_qty_col).value
                        base_price = ws.cell(row_id, base_price_col).value
                        quantity_another1 = ws.cell(row_id, quantity_another1_col).value
                        quantity_another2 = ws.cell(row_id, quantity_another1_col + 1).value
                        quantity_another3 = ws.cell(row_id, quantity_another1_col + 2).value
                        if not purchase_uom_qty_col:
                            purchase_uom_qty = product_uom_qty
                        else:
                            purchase_uom_qty = ws.cell(row_id, purchase_uom_qty_col).value
                        if not product_uom_qty or not price_unit or not base_price or not quantity_another1:
                            continue
                        val = {
                            "default_code": default_code,
                            "base_price": base_price,
                            "purchase_price": base_price,
                            "price_unit": price_unit,
                            "product_uom_qty": product_uom_qty,
                            "quantity_another1": quantity_another1,
                            "quantity_another2": quantity_another2,
                            "quantity_another3": quantity_another3,
                        }
                        try:
                            if purchase_uom_qty:
                                val['purchase_uom_qty'] = purchase_uom_qty
                                val['quantity_extra'] = product_uom_qty - purchase_uom_qty
                        except:
                            _logger.error("Error import line %s" % row_id)
                            continue
                        _logger.info(val)
                        vals["order_line"].append(val)
                    _logger.info(vals)
                    if len(vals.get("order_line", [])) > 0:
                        sale = self.env["sale.order"].import_from_excel(vals)
                        # if sale:
                        #     action_window = {
                        #         "type": "ir.actions.act_window",
                        #         "res_model": "sale.order",
                        #         "name": _("Sales Order"),
                        #         "views": [[False, "form"]],
                        #         "context": {"create": False, "show_sale": True},
                        #         "res_id": sale.id
                        #     }
                        #     return action_window
                        import_done = True
                        if sale:
                            _logger.info(">>>>>>>>>>>>>>>>>> create sale order id %s" % sale.id)
                            sale_ids.append(sale.id)
                if import_done:
                    return {
                        "type": "ir.actions.act_window",
                        "res_model": "sale.order",
                        "views": [[False, "tree"], [False, "form"]],
                        "domain": [["id", "in", sale_ids]],
                        "context": {"create": False},
                        "name": "Import Orders",
                    }
                else:
                    raise ValidationError(
                        _("Have not any sheet for import, please correct sheet name need import with format DD-MM"))
            else:
                raise ValidationError(_("Unsupported File Type, please upload correct with format xlsx or xlsm"))
