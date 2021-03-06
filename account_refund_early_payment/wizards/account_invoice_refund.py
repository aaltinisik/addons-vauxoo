from itertools import zip_longest
from odoo import api, fields, models


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.onchange('percentage')
    def _onchange_amount_total(self):
        invoices = self.env['account.invoice'].browse(
            self._context.get('active_ids', self.active_id))
        self.amount_total = sum(invoices.mapped('amount_total')) * (
            self.percentage / 100)

    filter_refund = fields.Selection(
        selection_add=[('early_payment', 'Early payment: Prepare a discount '
                                         'and reconcile automatically such '
                                         'refund with the invoices selected')])
    percentage = fields.Float(default=5.0)
    product_id = fields.Many2one(
        'product.product', string='Product',
        default=lambda x: x.env.ref(
            'account_refund_early_payment.product_discount', False))
    amount_total = fields.Float()
    active_id = fields.Integer()

    @api.multi
    def compute_refund(self, mode):
        result = super(AccountInvoiceRefund, self).compute_refund(mode)
        if mode != 'early_payment':
            return result
        invoices = self.env['account.invoice'].browse(
            self._context.get('active_ids'))
        total = sum(invoices.mapped('amount_total'))
        refunds = invoices.browse(result.get('domain')[1][2])
        refunds.mapped('tax_line_ids').unlink()
        refunds.mapped('invoice_line_ids').unlink()
        for inv, refund in zip_longest(invoices, refunds, fillvalue=None):
            if not inv or not refund:
                break
            percentage = inv.amount_total / total
            taxes = self.product_id.taxes_id
            tax_perc = sum(taxes.filtered(
                lambda tax: not tax.price_include
                and tax.amount_type == 'percent').mapped('amount'))
            account = self.product_id.product_tmpl_id.get_product_accounts(
                inv.fiscal_position_id)['income']
            self.env['account.invoice.line'].create({
                'invoice_id': refund.id,
                'product_id': self.product_id.id,
                'name': self.product_id.name_get()[0][1],
                'uom_id': self.product_id.uom_id.id,
                'invoice_line_tax_ids': [
                    (6, 0, taxes._ids)],
                'price_unit': self.amount_total * percentage / (
                    1.0 + (tax_perc or 0.0) / 100),
                'account_id': account.id,
            })
            refund.compute_taxes()
            refund.action_invoice_open()
            # Which is the aml to reconcile to (the receivable one)
            reconcile = refund.move_id.line_ids.filtered(
                lambda x: x.account_id == refund.account_id
                and not x.reconciled).sorted('date_maturity')
            inv.assign_outstanding_credit(reconcile.id)
        return result

    @api.model
    def action_split_reconcile(self, brw):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return False
        invoices = self.env['account.invoice'].browse(active_ids)
        prec = self.env['decimal.precision'].precision_get('Account')
        account_m_line_obj = self.env['account.move.line']

        brw.move_id.button_cancel()

        # we get the aml of refund to be split and reconciled
        to_reconcile_ids = {}
        for tmpline in brw.move_id.line_id:
            if (tmpline.account_id.reconcile
                    and tmpline.account_id.type == 'receivable'):
                move_line_id_refund = tmpline
                move_refund_credit = tmpline.credit
            elif tmpline.account_id.reconcile:
                to_reconcile_ids.setdefault(
                    tmpline.account_id.id, []).append(tmpline.id)

        amount_total_inv = 0
        invoice_source = []
        # Get the amount_total of all invoices to make
        # proration with refund

        for inv in invoices:
            amount_total_inv += inv.currency_id.round(inv.amount_total)
            invoice_source.append(inv.number)

        for inv in invoices:
            for line in inv.move_id.line_id:
                if (line.account_id.reconcile
                        and not line.reconcile_id
                        and line.account_id == move_line_id_refund.account_id):
                    amount_inv_refund = (
                        amount_total_inv and inv.amount_total
                        / amount_total_inv) * move_line_id_refund.credit or 0.0

                    if 1 > (abs(move_refund_credit - amount_inv_refund)) >\
                            10 ** (-max(5, prec)):
                        amount_inv_refund = move_refund_credit

                    move_line_id_inv_refund = move_line_id_refund.copy(
                        default={
                            'credit': inv.currency_id.round(
                                amount_inv_refund)})
                    move_refund_credit -= move_line_id_inv_refund.credit

                    line_to_reconcile = account_m_line_obj.browse(
                        [line.id, move_line_id_inv_refund.id])
                    line_to_reconcile.reconcile_partial()

                elif line.account_id.reconcile and not line.reconcile_id:
                    to_reconcile_ids.setdefault(
                        line.account_id.id, []).append(line.id)

        for account in to_reconcile_ids:
            if len(to_reconcile_ids[account]) > 1:
                line_to_reconcile_2 = account_m_line_obj.browse(
                    to_reconcile_ids[account])
                line_to_reconcile_2.reconcile_partial()

        move_line_id_refund.unlink()
        brw.move_id.button_validate()
        brw.write(
            {'origin': ','.join(inv_source for inv_source in invoice_source)})
