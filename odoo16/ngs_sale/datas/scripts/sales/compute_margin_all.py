# coding=utf-8
import xmlrpclib
import time
import logging
import xlrd
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

result = models.execute_kw(db, uid, password, "sale.order.line", "compute_margin_all", [[]])

print '-' * 100
print result