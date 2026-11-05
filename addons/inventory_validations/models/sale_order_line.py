from odoo import models, api, _, fields
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _is_discount_line(self):
        """
        Check if the line represents a discount, loyalty reward, or down payment
        where a negative unit price is valid and expected.
        """
        self.ensure_one()
        if not self.product_id:
            return False

        company = self.company_id or self.order_id.company_id or self.env.company
        if company and hasattr(company, 'sale_discount_product_id') and company.sale_discount_product_id:
            if self.product_id == company.sale_discount_product_id:
                return True

        default_code = (self.product_id.default_code or '').lower()
        product_name = (self.product_id.name or '').lower()
        if 'discount' in default_code or 'discount' in product_name:
            return True

        if getattr(self, 'reward_id', False):
            return True

        if getattr(self, 'is_discount', False) or getattr(self, 'is_downpayment', False):
            return True

        return False

    @api.constrains('product_uom_qty', 'price_unit')
    def _check_quantity_and_price_not_negative(self):
        """
        Validates that the ordered quantity and unit price on a sales order line
        are not negative. Zero is allowed for both fields.
        Fixed amount discounts and reward lines are allowed to have a negative unit price.
        """
        for line in self:
            if line.display_type:
                continue

            if line.product_uom_qty < 0:
                raise ValidationError(_(
                    "The ordered quantity for product [%s] cannot be negative.",
                    line.product_id.display_name
                ))

            if line.price_unit < 0:
                if line._is_discount_line():
                    continue
                raise ValidationError(_(
                    "The unit price for product [%s] cannot be negative.",
                    line.product_id.display_name
                ))
