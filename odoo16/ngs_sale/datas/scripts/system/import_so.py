import xmlrpclib
import time
import logging
import xlrd
from login_local import uid, password, db, models

__logger = logging.getLogger(__name__)

path =  "import_so.xlsm"
workbook = xlrd.open_workbook(path)
ws = workbook.sheet_by_name("Import 1")
codes_not_found = []
customer_name = ws.cell(11, 7).value
origin = ws.cell(12, 7).value
date_order = ws.cell(12, 8).value
print customer_name, origin, date_order
print "----------------- sale order line ---------------------"
vals = {
    "customer_name": customer_name,
    "origin": origin,
    "date_order": date_order,
    "order_line": []
}
for row_id in range(2, ws.nrows):
    if row_id < 22:
        continue
    default_code = ws.cell(row_id, 34).value
    price_unit = ws.cell(row_id, 18).value
    product_uom_qty = ws.cell(row_id, 12).value
    quantity_another1 = ws.cell(row_id, 7).value
    quantity_another2 = ws.cell(row_id, 8).value
    quantity_another3 = ws.cell(row_id, 9).value
    val = {
        "default_code": default_code,
        "price_unit": price_unit,
        "product_uom_qty": product_uom_qty,
        "quantity_another1": quantity_another1,
        "quantity_another2": quantity_another2,
        "quantity_another3": quantity_another3,
    }
    if not product_uom_qty:
        continue
    vals["order_line"].append(val)
    print "---------------------"
print vals
if vals.get("order_line", []):
    datas = models.execute_kw(db, uid, password, "sale.order", "import_from_excel", [[], vals])
