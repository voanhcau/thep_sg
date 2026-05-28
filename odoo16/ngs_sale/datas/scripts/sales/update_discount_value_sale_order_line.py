import xmlrpclib
import time
import logging
import xlrd
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

orders = models.execute_kw(db, uid, password, "sale.order", "search_read", [[]], {'fields': ['id', 'name']})
order_ids = [vl.get('id') for vl in orders]

for sale_id in order_ids:
    try:
        models.execute_kw(db, uid, password, 'sale.order', 'write',
                          [[sale_id], {'pricelist_id': 2, 'purchase_pricelist_id': 1}])
    except:
        continue
datas = models.execute_kw(db, uid, password, "sale.order.line", "search_read", [[('discount_value', '=', 0)]], {'fields': ['id', 'discount_value', 'margin']})
sale_line_ids = [vl.get('id') for vl in datas]
if len(sale_line_ids) >= 1:
    for line_id in sale_line_ids:
        try:
            print line_id
            res = models.execute_kw(db, uid, password, 'sale.order.line', 'write', [[line_id], {'discount_value': 0}])
            print res
        except:
            continue
