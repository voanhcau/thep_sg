import xmlrpclib
import time
import logging
import xlrd
from login import uid, password, db, models

__logger = logging.getLogger(__name__)

path =  "update_so.xlsx"
workbook = xlrd.open_workbook(path)
ws = workbook.sheet_by_name("Sheet2")
codes_not_found = []
print "----------------- sale order update ---------------------"
for row_id in range(2, ws.nrows):

    name = ws.cell(row_id, 0).value
    date_order = ws.cell(row_id, 1).value
    date_order = xlrd.xldate.xldate_as_datetime(date_order, 0).strftime('%Y-%m-%d')
    print name, date_order, type(date_order)
    datas = models.execute_kw(db, uid, password, "sale.order", "search_read", [[('name', '=', name)]], {'fields': ['id']})
    if len(datas) == 1:
        sale_id = datas[0].get('id')
        print sale_id
        res = models.execute_kw(db, uid, password, 'sale.order', 'write', [sale_id, {'date_order': date_order}])
        print res
    print "---------------------"
