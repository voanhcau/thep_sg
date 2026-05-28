import xmlrpclib
import time
import logging
import xlrd
from login import uid, password, db, models

__logger = logging.getLogger(__name__)

path = 'Baremfull-3.xlsx'
workbook = xlrd.open_workbook(path)
ws = workbook.sheet_by_name('Sheet1')
codes_not_found = []
for row_id in range(2, ws.nrows):
    vat = ws.cell(row_id, 8).value
    default_code = ws.cell(row_id, 4).value.encode('utf-8')
    product_code = ws.cell(row_id, 3).value.encode('utf-8')
    if not vat or not default_code or not product_code:
        continue
    else:
        vat = str(ws.cell(row_id, 8).value).encode('utf-8').split('.')[0]
        print u'[INFO] Processing row %s' % row_id
        print product_code
        datas = models.execute_kw(db, uid, password, 'product.template', 'import_product_supplierinfo', [[], {
            'default_code': default_code,
            'vat': vat,
            'product_code': product_code,
        }])
