# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_description = fields.Text(u'Nội dung và điều khoản bán hàng')
    purchase_description = fields.Text(u'Nội dung và điều khoản mua hàng')
    signature = fields.Image(
        string="Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024)
    signature_so = fields.Boolean('Hiển thị chữ ký lên YCBG')
    signature_po = fields.Boolean('Hiển thị chữ ký lên XNKG')
    interest_calculation_extra_days = fields.Integer(
        string='Số ngày bổ sung tính lãi vay',
        default=0,
        help='Số ngày bổ sung thêm vào khi tính lãi vay. Mặc định là 0.'
    )
    delivery_receipt_construction_site = fields.Html(
        string='Biên bản giao nhận',
        help='HTML mặc định cho phần mở đầu biên bản giao nhận (Căn cứ báo giá / Phiếu giao hàng / Ngày). '
             'Sẽ được copy sang phiếu giao nhận và có thể chỉnh sửa tại đó.',
        default="""
<p style="margin: 5px 0;">Căn cứ báo giá số: <span style="min-width: 250px; display: inline-block;"></span> ký ngày: <span style="min-width: 250px; display: inline-block;"></span></p>
<p style="margin: 5px 0;">+ Phiếu giao hàng: ................................................</p>
<p style="margin: 5px 0;">Ngày: ............................................................</p>
        """
    )
    delivery_receipt_footer_notes = fields.Html(
        string='Ghi chú cuối biên bản giao nhận',
        default="""
<p style="margin: 5px 0;">- Chất lượng hàng hóa: Hàng mới, không rỉ sét, không dính nước.</p>
<p style="margin: 5px 0;">- Việc giao nhận đã hoàn tất, và kể từ đây Bên giao không còn chịu trách nhiệm giải quyết sự thiếu hụt về số lượng này nữa, việc quản lý hàng hóa đã thuộc bên nhận hàng.</p>
<p style="margin: 5px 0;">- Bên giao hàng gửi kèm theo các chứng từ sau:<br/>+    Biên bản giao nhận hàng hoá: 02 bản (NSG giữ 01 bản)<br/>+    Chứng chỉ chất lượng và/ chứng chỉ xuất xưởng: 1 bộ bản cứng hoặc bản điện tử.</p>
        """,
        help='Ghi chú cuối biên bản giao nhận (HTML) - bao gồm chất lượng, trách nhiệm và chứng từ'
    )
    hide_report_footer = fields.Boolean(
        string='Ẩn footer báo cáo',
        default=True,
        help='Nếu được bật, footer (số trang, tên báo cáo) sẽ bị ẩn trong tất cả các báo cáo của hệ thống'
    )

    @api.model
    def default_get(self, fields):
        result = super(ResCompany, self).default_get(fields)
        result['sale_description'] = """
            Phương thức thanh toán:		Thanh toán 100% ngay sau khi nhận hàng và xuất hóa đơn VAT.
            Hiệu lực của báo giá:			Giá thời điểm 
            Địa điểm giao nhận:			Hàng giao lên phương tiện Bên Mua tại kho nhà máy /kho Bên Bán.
            Khối lượng giao nhận:			Theo thỏa thuận.
            Thời gian giao hàng:			1-2 ngày
            Phương thức giao nhận:			Theo chính sách giao nhận của nhà máy tại từng thời điểm.
            Tài khoản đơn vị thụ hưởng:	        CÔNG TY TNHH XUẤT NHẬP KHẨU THƯƠNG MẠI  NAM SÀI GÒN 
            1. Số TK: 79890968 ACB - CN NAM SÀI GÒN.
            2. Số TK : 33886868 Techcombank - CN Tân Thuận 
            3. Số TK: 040 660 1979 6868 Ngân hàng TMCP Hàng Hải (MSB) - CN TP.HCM. 
            4. Số TK: 0600 9566 5805 SACOMBANK - CN SÀI GÒN - PGD Quận 1.
            5. Số TK: 0181 00 211 6868 VIETCOMBANK - CN NAM SÀI GÒN"								
            """
        result['purchase_description'] = """
                    +	Chứng từ giao theo xe:		CCXX, TPHH, CCCL 						
                    +	Chiết Khấu:		-180		đ/kg (chưa VAT). 		Lô GG:		
                    +	Giao thẳng kho:		Nha Trang						
                                                                            
                    1.	Phương thức thanh toán: 	CK trước khi nhận hàng						
                    2.	Phương thức giao nhận:		Theo phiếu cân						
                    3.	Thời gian giao hàng:		28-05-2023						
                    4.	Khu vực giao hàng:		HCM						
                    Rất mong sự hỗ trợ và hợp tác của Quý Công ty.								
                    Trân trọng cảm ơn!																
                    """
        return result

    def write(self, vals):
        for company in self:
            if not company.sale_description:
                vals.update({
                    'sale_description': """
                        Phương thức thanh toán:		Thanh toán 100% ngay sau khi nhận hàng và xuất hóa đơn VAT.
                        Hiệu lực của báo giá:			Giá thời điểm 
                        Địa điểm giao nhận:			Hàng giao lên phương tiện Bên Mua tại kho nhà máy /kho Bên Bán.
                        Khối lượng giao nhận:			Theo thỏa thuận.
                        Thời gian giao hàng:			1-2 ngày
                        Phương thức giao nhận:			Theo chính sách giao nhận của nhà máy tại từng thời điểm.
                        Tài khoản đơn vị thụ hưởng:	        CÔNG TY TNHH XUẤT NHẬP KHẨU THƯƠNG MẠI  NAM SÀI GÒN 
                        1. Số TK: 79890968 ACB - CN NAM SÀI GÒN.
                        2. Số TK : 33886868 Techcombank - CN Tân Thuận 
                        3. Số TK: 040 660 1979 6868 Ngân hàng TMCP Hàng Hải (MSB) - CN TP.HCM. 
                        4. Số TK: 0600 9566 5805 SACOMBANK - CN SÀI GÒN - PGD Quận 1.
                        5. Số TK: 0181 00 211 6868 VIETCOMBANK - CN NAM SÀI GÒN"								
                    """,
                    'purchase_description': """
                        +	Chứng từ giao theo xe:		CCXX, TPHH, CCCL 						
                        +	Chiết Khấu:		-180		đ/kg (chưa VAT). 		Lô GG:		
                        +	Giao thẳng kho:		Nha Trang						
                                                                                
                        1.	Phương thức thanh toán: 	CK trước khi nhận hàng						
                        2.	Phương thức giao nhận:		Theo phiếu cân						
                        3.	Thời gian giao hàng:		28-05-2023						
                        4.	Khu vực giao hàng:		HCM						
                        Rất mong sự hỗ trợ và hợp tác của Quý Công ty.								
                        Trân trọng cảm ơn!																
                    """
                })
                break
        return super(ResCompany, self).write(vals)
