import xmlrpclib
import time
import logging
import xlrd
from login import uid, password, db, models

__logger = logging.getLogger(__name__)

datas = models.execute_kw(db, uid, password, 'product.category', 'set_master_data', [[]])