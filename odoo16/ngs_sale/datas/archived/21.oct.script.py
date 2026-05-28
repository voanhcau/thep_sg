# coding=utf-8
import xmlrpclib
import time
import logging
import xlrd
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

suppliers_data = {
    u"CÔNG TY CỔ PHẦN VẬT TƯ HẬU GIANG (HAMACO)": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CP KIM KHÍ THÀNH PHỐ HỒ CHÍ MINH - VNSTEEL": None,
    u"CÔNG TY TNHH TM VÀ SX THÉP VIỆT": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY TNHH TM VÀ SX THÉP VIỆT": None,
    u"CÔNG TY TNHH THƯƠNG MẠI & SẢN XUẤT QUẢN TRUNG": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CỔ PHẦN TẬP ĐOÀN SEMEC": None,
    u"CÔNG TY CỔ PHẦN KIM KHÍ VIỆT PHÁT": None,
    u"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN": None,
    u"CÔNG TY CỔ PHẦN ĐẦU TƯ VÀ KINH DOANH THÉP NHÂN LUẬT": None
}

purchases_data = {
    "P06411":"CÔNG TY CỔ PHẦN THƯƠNG MẠI THÁI HƯNG",
    "P02033":"CÔNG TY CỔ PHẦN THÉP QUANG TIẾN",
    "P05239":"CÔNG TY TNHH TM VÀ SX THÉP VIỆT",
    "P06463":"CÔNG TY TNHH VẬT TƯ QUANG VINH",
    "P06189":"CÔNG TY TNHH VẬT TƯ QUANG VINH",
    "P01092":"CÔNG TY CỔ PHẦN KIM KHÍ VIỆT PHÁT",
    "P00385":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P00386":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P00500":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P00501":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P02075":"CÔNG TY CỔ PHẦN TẬP ĐOÀN SEMEC",
    "P00570":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P02622":"CÔNG TY CP ĐẦU TƯ THƯƠNG MẠI SMC",
    "P03801":"CÔNG TY CP ĐẦU TƯ THƯƠNG MẠI SMC",
    "P02319":"CÔNG TY CỔ PHẦN THÉP VÀ THƯƠNG MẠI HÀ NỘI",
    "P00573":"CÔNG TY CP KIM KHÍ THÀNH PHỐ HỒ CHÍ MINH - VNSTEEL",
    "P03391":"CÔNG TY TNHH METAL ONE (VIỆT NAM)-MOV",
    "P02258":"CÔNG TY TNHH MTV ĐTXD THƯƠNG MẠI DỊCH VỤ TRƯỜNG THỊNH",
    "P01173":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P00830":"CÔNG TY CP TẬP ĐOÀN VAS NGHI SƠN",
    "P06622":"CÔNG TY TNHH TM DỊCH VỤ XÂY DỰNG CẦN HƯƠNG",

}

# for po in purchases_data.items():
#     print po
#     partner = models.execute_kw(db, uid, password, "res.partner", "search_read", [[('name', '=', po[1])]],
#                                 {'fields': ['id', 'name']})
#     if not partner:
#         print '-' * 100
#         break
#     purchase = models.execute_kw(db, uid, password, "purchase.order", "search_read",
#                                  [[('name', '=', po[0])]],
#                                  {'fields': ['id', 'name', 'partner_id', 'state']})
#     if not purchase:
#         print '-' * 100
#         break
#     res = models.execute_kw(db, uid, password, 'purchase.order', 'write', [purchase[0]['id'], {
#         'state': 'draft',
#         'partner_id': partner[0]['id']
#     }])
#     print res
#     print '*' * 100


purchases_to_cancel = [
    "P04492",
    "P01089",
    "P01067",
    "P03523",
    "P04285",
    "P04286",
    "P04589",
]


for po_name in purchases_to_cancel:
    purchase = models.execute_kw(db, uid, password, "purchase.order", "search_read",
                                 [[('name', '=', po_name)]],
                                 {'fields': ['id', 'name', 'partner_id', 'state']})
    if not purchase:
        print '*' * 100
        break
    else:
        res = models.execute_kw(db, uid, password, 'purchase.order', 'write', [purchase[0]['id'], {'state': 'cancel'}])
        print purchase[0]['id'], res
        print 'update po id %s with state cancel' % (purchase[0]['id'])