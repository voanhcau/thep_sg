import xmlrpclib
import time
import logging
import xlrd
from login import uid, password, db, models

__logger = logging.getLogger(__name__)

path =  'Barem-12Jan2024.xlsm'
workbook = xlrd.open_workbook(path)
ws = workbook.sheet_by_name('Barem')
codes_not_found = []
codes_not_found_str = []
for row_id in range(2, ws.nrows):
    default_code = ws.cell(row_id, 0).value
    quantity_supplier = ws.cell(row_id, 8).value
    quantity_tcvn = ws.cell(row_id, 9).value
    quantity_another = ws.cell(row_id, 7).value or 0
    if not default_code or not quantity_supplier or not quantity_tcvn:
        continue
    else:
        value = {
            'default_code': default_code,
            'quantity_supplier': quantity_supplier,
            'quantity_tcvn': quantity_tcvn,
            'quantity_another': quantity_another,
        }
        datas = models.execute_kw(db, uid, password, 'product.template', 'import_update_quantity_supplier_and_tcvn', [[], value])
        if not datas:
            print '>>>>>>>>>>>>>>>>>>>>>>'
            print default_code
            print '>>>>>>>>>>>>>>>>>>>>>>'
            codes_not_found.append(row_id)
            codes_not_found_str.append(default_code)
print codes_not_found
print codes_not_found_str