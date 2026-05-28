from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestSaleOrder(TransactionCase):
    def setUp(self):
        super().setUp()
        # Tạo dữ liệu mẫu: partner, product, pricelist, sale order, ...
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.pricelist = self.env['product.pricelist'].create({'name': 'Test Pricelist', 'type': 'sale'})
        self.purchase_pricelist = self.env['product.pricelist'].create({'name': 'Test Purchase Pricelist', 'type': 'purchase'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'default_code': 'TP001',
            'list_price': 100,
            'standard_price': 50,
        })
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'purchase_pricelist_id': self.purchase_pricelist.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 10,
                    'price_unit': 100,
                })
            ]
        })

    def test_calculate_interest_no_invoice(self):
        """Test calculate_interest raises UserError if no invoice exists."""
        with self.assertRaises(UserError):
            self.sale_order.calculate_interest()

    def test_action_create_purchase_order(self):
        """Test creating and updating purchase order from sale order."""
        # Test tạo đơn mua mới
        result = self.sale_order.action_create_purchase_order()
        self.assertTrue(result, "Should return action window")
        self.assertEqual(result['res_model'], 'purchase.order', "Should return purchase order form view")
        
        # Kiểm tra đơn mua đã được tạo
        purchase_order = self.env['purchase.order'].browse(result['res_id'])
        self.assertTrue(purchase_order, "Purchase order should be created")
        self.assertEqual(purchase_order.partner_id, self.partner, "Partner should match")
        self.assertEqual(purchase_order.sale_reference_id, self.sale_order, "Should be linked to sale order")
        
        # Kiểm tra dòng đơn mua
        self.assertEqual(len(purchase_order.order_line), 1, "Should have one order line")
        po_line = purchase_order.order_line[0]
        self.assertEqual(po_line.product_id, self.product, "Product should match")
        self.assertEqual(po_line.product_qty, 10, "Quantity should match")
        
        # Test cập nhật đơn mua
        self.sale_order.order_line[0].write({'product_uom_qty': 20})
        result = self.sale_order.action_create_purchase_order()
        purchase_order = self.env['purchase.order'].browse(result['res_id'])
        self.assertEqual(purchase_order.order_line[0].product_qty, 20, "Quantity should be updated")

    # Các test case cho các hàm khác sẽ được bổ sung tiếp theo 