import xmlrpclib
import time
import logging
import xlrd
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

path =  '11.11.2024.xlsx'
workbook = xlrd.open_workbook(path)
ws = workbook.sheet_by_name("Rename_supplier_11.11.2024")
codes_not_found = []
codes_not_found_str = []
for row_id in range(2, ws.nrows):
    po_name = ws.cell(row_id, 1).value
    print po_name
    po_datas = models.execute_kw(db, uid, password, "purchase.order", "search_read",
                                 [[
                                     ('name', '=', po_name),
                                 ]],
                                 {'fields': ['id', 'name', 'state']})
    print po_datas
    print '*' * 50
    if po_datas and len(po_datas) == 1:
        res = models.execute_kw(db, uid, password, 'purchase.order', 'write', [po_datas[0]['id'], {'state': 'cancel'}])
        print 'update po id %s with state cancel' % (po_datas[0]['id'])
    else:
        print ' error ' * 1000
        break