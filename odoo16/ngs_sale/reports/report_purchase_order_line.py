import xlsxwriter
import base64
from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone
import pytz

import openpyxl
from openpyxl.styles import NamedStyle

from odoo.tools import file_open
import os
xlsx_path = os.path.abspath(os.getcwd()) + '/nsgerp/ngs_sale/reports/'
xlsx_path = "/odoo/custom/nsgerp/ngs_sale/reports/"


class ReportPurchaseOrderLine(models.TransientModel):
    _name = "report.purchase.order.line"
    _description = "Report Purchase Order Line"

    @api.model
    def get_default_date_model(self):
        return pytz.UTC.localize(datetime.now()).astimezone(timezone(self.env.user.tz or 'UTC'))

    datas = fields.Binary('File', readonly=True)
    datas_fname = fields.Char('Filename', readonly=True)
    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'report_purchase_order_line_rel',
        'report_id',
        'purchase_id',
        'Purchase Orders')

    def print_excel_report(self):
        self.ensure_one()
        data = self.read()[0]
        purchase_order_ids = data['purchase_order_ids']

        date_string = self.get_default_date_model().strftime("%Y-%m-%d")
        report_name = u'PHIẾU NHẬP MUA HÀNG'
        filename = '%s %s' % (report_name, date_string)

        columns = [
            ('NGÀY CHỨNG TỪ', 20, 'datetime', 'datetime'),
            ('SỐ CHỨNG TỪ', 20, 'char', 'char'),
            ('NGÀY', 20, 'datetime', 'datetime'),
            ('SỐ', 10, 'char', 'char'),
            ('KÝ HIỆU', 10, 'char', 'char'),
            ('MẪU', 10, 'char', 'char'),
            ('BỘ PHẬN', 10, 'char', 'char'),
            ('HỢP ĐỒNG', 20, 'char', 'char'),
            ('ĐỐI TƯỢNG', 20, 'char', 'char'),
            ('DIỄN GIẢI TIẾNG VIỆT', 40, 'float', 'float'),
            ('DIỄN GIẢI TIẾNG ANH', 20, 'char', 'char'),
            ('MÃ NHẬP XUẤT', 10, 'char', 'char'),
            ('XUẤT XỨ', 10, 'char', 'char'),
            ('MÃ KHO', 10, 'char', 'char'),
            ('MÃ VẬT TƯ', 10, 'char', 'char'),
            ('ĐƠN VỊ TÍNH', 20, 'char', 'char'),
            ('LÔ HÀNG', 10, 'char', 'char'),
            ('HẠN DÙNG', 10, 'char', 'char'),
            ('MÃ TIỀN TỆ', 10, 'char', 'char'),
            ('TỶ GIÁ', 10, 'char', 'char'),
            ('SỐ LƯỢNG', 10, 'float', 'float'),
            ('NGUYÊN TỆ', 20, 'float', 'float'),
            ('THÀNH TIỀN', 20, 'float', 'float'),
            ('NGUYÊN TỆ', 20, 'float', 'float'),
            ('THÀNH TIỀN', 20, 'float', 'float'),
            ('%', 5, 'char', 'char'),
            ('NGUYÊN TỆ', 20, 'float', 'float'),
            ('THÀNH TIỀN', 20, 'float', 'float'),
            ('THUẾ NHẬP KHẨU', 10, 'char', 'char'),
            ('NGUYÊN TỆ', 20, 'float', 'float'),
            ('THÀNH TIỀN', 20, 'float', 'float'), # 31 colums
        ]
        datetime_format = '%Y-%m-%d %H:%M:%S'
        utc = datetime.now().strftime(datetime_format)
        utc = datetime.strptime(utc, datetime_format)
        tz = self.get_default_date_model().strftime(datetime_format)
        tz = datetime.strptime(tz, datetime_format)
        duration = tz - utc
        hours = duration.seconds / 60 / 60
        if hours > 1 or hours < 1:
            hours = str(hours) + ' hours'
        else:
            hours = str(hours) + ' hour'

        query = """
            SELECT 
                        pol.name AS n_0,
                        pp.default_code AS n_1,
                        pol.date_planned AS n_2, 
                        uu.name AS n_3, 
                        pol.product_qty AS n_4,
                        pol.price_unit as n_5,
                        pol.price_subtotal as  n_6,
                        po.date_order as n_7,
                        am.ref as n_8,
                        am.invoice_date as n_9,
                        po.name as n_10,
                        rp.ref as n_11,
                        pol.price_tax as n_12
            FROM 
                        purchase_order_line AS pol
            LEFT JOIN 
                        product_product pp ON pp.id=pol.product_id
            LEFT JOIN 
                        product_template pt ON pt.id=pp.product_tmpl_id
            LEFT JOIN 
                        uom_uom uu ON uu.id=pol.product_uom
            LEFT JOIN 
                        purchase_order po ON po.id=pol.order_id
            LEFT JOIN 
                        account_move_line aml ON aml.purchase_line_id=pol.id
            LEFT JOIN 
                        account_move am ON am.id=aml.move_id
            LEFT JOIN
                        res_partner rp ON rp.id=po.partner_id
            WHERE 
                        pol.order_id in %s  
            ORDER BY 
                        pol.order_id
        """
        if len(purchase_order_ids) == 1:
            purchase_order_ids.append(0)
        if len(purchase_order_ids) == 0:
            return
        self._cr.execute(query % (tuple(purchase_order_ids), ))
        result = self._cr.fetchall()


        wb = openpyxl.load_workbook(filename=xlsx_path + 'PHIEUNHAPMUAHANG.xlsx')
        worksheet = wb.worksheets[0]
        worksheet.protection.sheet = False

        row = 4
        col = 0

        row += 1
        no = 1

        result_parse = []
        for res in result:
            result_parse.append(tuple([
                res[7],
                res[10],
                res[9],
                res[8],
                'AP/21E',
                'GTKT0/001',
                '',
                '',
                res[11],
                u'Mua hàng theo hoá đơn số %s' % res[8] if res[8] else 'Mua hàng theo hoá đơn số: N/A',
                res[0],
                '331',
                '0',
                'HH',
                res[1],
                res[3].get('vi_VN'),
                '',
                '',
                'VND',
                1,
                res[4],
                res[5],
                res[5],
                res[6],
                res[6],
                10 if res[12] > 0 else 0,
                res[12],
                res[12],
                0,
                0,
                0,
            ]))
        for res in result_parse:
            col = 0
            for column in columns:
                column_type = column[2]
                if column_type == 'char':
                    col_value = res[col] if res[col] else ''
                elif column_type == 'no':
                    col_value = no
                elif column_type == 'datetime':
                    col_value = res[col].strftime('%d/%m/%Y') if res[col] else ''
                else:
                    col_value = res[col] if res[col] else 0
                c = worksheet.cell(row - 1, col + 1)
                c.value = col_value
                # if column_type == 'datetime':
                #     date_style = NamedStyle(name='datetime', number_format='DD/MM/YYYY')
                #     c.style = date_style
                col += 1
            row += 1

        wb.save(xlsx_path + 'PHIEUNHAPMUAHANG-final.xlsx')

        filename += '%2Exlsx'

        with file_open(xlsx_path + 'PHIEUNHAPMUAHANG-final.xlsx', "rb") as f:
            self.datas = base64.encodebytes(f.read())
            self.datas_fname = filename
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': 'web/content/?model=' + self._name + '&id=' + str(
                self.id) + '&field=datas&download=true&filename=' + filename,
        }

    def add_workbook_format(self, workbook):
        colors = {
            'white_orange': '#FFFFDB',
            'orange': '#FFC300',
            'red': '#FF0000',
            'yellow': '#F6FA03',
        }

        wbf = {}
        wbf['header'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': '#FFFFDB', 'font_color': '#000000', 'font_name': 'Georgia'})
        wbf['header'].set_border()

        wbf['header_orange'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': colors['orange'], 'font_color': '#000000',
             'font_name': 'Georgia'})
        wbf['header_orange'].set_border()

        wbf['header_yellow'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': colors['yellow'], 'font_color': '#000000',
             'font_name': 'Georgia'})
        wbf['header_yellow'].set_border()

        wbf['header_no'] = workbook.add_format(
            {'bold': 1, 'align': 'center', 'bg_color': '#FFFFDB', 'font_color': '#000000', 'font_name': 'Georgia'})
        wbf['header_no'].set_border()
        wbf['header_no'].set_align('vcenter')

        wbf['footer'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})

        wbf['content_datetime'] = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'font_name': 'Georgia'})
        wbf['content_datetime'].set_left()
        wbf['content_datetime'].set_right()

        wbf['content_date'] = workbook.add_format({'num_format': 'yyyy-mm-dd', 'font_name': 'Georgia'})
        wbf['content_date'].set_left()
        wbf['content_date'].set_right()

        wbf['title_doc'] = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 20,
            'font_name': 'Georgia',
        })

        wbf['company'] = workbook.add_format({'align': 'left', 'font_name': 'Georgia'})
        wbf['company'].set_font_size(11)

        wbf['content'] = workbook.add_format()
        wbf['content'].set_left()
        wbf['content'].set_right()

        wbf['content_float'] = workbook.add_format({'align': 'right', 'num_format': '#,##0.00', 'font_name': 'Georgia'})
        wbf['content_float'].set_right()
        wbf['content_float'].set_left()

        wbf['content_number'] = workbook.add_format({'align': 'right', 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['content_number'].set_right()
        wbf['content_number'].set_left()

        wbf['content_percent'] = workbook.add_format({'align': 'right', 'num_format': '0.00%', 'font_name': 'Georgia'})
        wbf['content_percent'].set_right()
        wbf['content_percent'].set_left()

        wbf['total_float'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['white_orange'], 'align': 'right', 'num_format': '#,##0.00',
             'font_name': 'Georgia'})
        wbf['total_float'].set_top()
        wbf['total_float'].set_bottom()
        wbf['total_float'].set_left()
        wbf['total_float'].set_right()

        wbf['total_number'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['white_orange'], 'bold': 1, 'num_format': '#,##0',
             'font_name': 'Georgia'})
        wbf['total_number'].set_top()
        wbf['total_number'].set_bottom()
        wbf['total_number'].set_left()
        wbf['total_number'].set_right()

        wbf['total'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['white_orange'], 'align': 'center', 'font_name': 'Georgia'})
        wbf['total'].set_left()
        wbf['total'].set_right()
        wbf['total'].set_top()
        wbf['total'].set_bottom()

        wbf['total_float_yellow'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['yellow'], 'align': 'right', 'num_format': '#,##0.00',
             'font_name': 'Georgia'})
        wbf['total_float_yellow'].set_top()
        wbf['total_float_yellow'].set_bottom()
        wbf['total_float_yellow'].set_left()
        wbf['total_float_yellow'].set_right()

        wbf['total_number_yellow'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['yellow'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['total_number_yellow'].set_top()
        wbf['total_number_yellow'].set_bottom()
        wbf['total_number_yellow'].set_left()
        wbf['total_number_yellow'].set_right()

        wbf['total_yellow'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['yellow'], 'align': 'center', 'font_name': 'Georgia'})
        wbf['total_yellow'].set_left()
        wbf['total_yellow'].set_right()
        wbf['total_yellow'].set_top()
        wbf['total_yellow'].set_bottom()

        wbf['total_float_orange'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['orange'], 'align': 'right', 'num_format': '#,##0.00',
             'font_name': 'Georgia'})
        wbf['total_float_orange'].set_top()
        wbf['total_float_orange'].set_bottom()
        wbf['total_float_orange'].set_left()
        wbf['total_float_orange'].set_right()

        wbf['total_number_orange'] = workbook.add_format(
            {'align': 'right', 'bg_color': colors['orange'], 'bold': 1, 'num_format': '#,##0', 'font_name': 'Georgia'})
        wbf['total_number_orange'].set_top()
        wbf['total_number_orange'].set_bottom()
        wbf['total_number_orange'].set_left()
        wbf['total_number_orange'].set_right()

        wbf['total_orange'] = workbook.add_format(
            {'bold': 1, 'bg_color': colors['orange'], 'align': 'center', 'font_name': 'Georgia'})
        wbf['total_orange'].set_left()
        wbf['total_orange'].set_right()
        wbf['total_orange'].set_top()
        wbf['total_orange'].set_bottom()

        wbf['header_detail_space'] = workbook.add_format({'font_name': 'Georgia'})
        wbf['header_detail_space'].set_left()
        wbf['header_detail_space'].set_right()
        wbf['header_detail_space'].set_top()
        wbf['header_detail_space'].set_bottom()

        wbf['header_detail'] = workbook.add_format({'bg_color': '#E0FFC2', 'font_name': 'Georgia'})
        wbf['header_detail'].set_left()
        wbf['header_detail'].set_right()
        wbf['header_detail'].set_top()
        wbf['header_detail'].set_bottom()

        return wbf, workbook
