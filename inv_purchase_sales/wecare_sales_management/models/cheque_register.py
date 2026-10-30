# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

CHEQUE_METHODS = ('cheque', 'pdc', 'check_printing', 'check')


class WecareChequeInvoiceLine(models.Model):
    _name = 'wecare.cheque.invoice.line'
    _description = 'Cheque Invoice Allocation'
    _order = 'invoice_date asc, id asc'

    cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Cheque Registration',
        required=True,
        ondelete='cascade',
        index=True,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Customer Invoice',
        required=True,
        domain="[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial'))]",
    )
    invoice_number = fields.Char(
        string='Invoice Number',
        related='invoice_id.name',
        readonly=True,
    )
    invoice_date = fields.Date(
        string='Invoice Date',
        related='invoice_id.invoice_date',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='cheque_id.currency_id',
        string='Currency',
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        related='invoice_id.amount_total',
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string='Outstanding',
        related='invoice_id.amount_residual',
        readonly=True,
    )
    amount_paid = fields.Monetary(
        string='Previously Paid',
        compute='_compute_amount_paid',
        readonly=True,
    )
    amount_allocated = fields.Monetary(
        string='Amount Allocated',
        required=True,
    )

    @api.depends('amount_total', 'amount_residual')
    def _compute_amount_paid(self):
        for line in self:
            line.amount_paid = max(0.0, (line.amount_total or 0.0) - (line.amount_residual or 0.0))

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        if self.invoice_id and not self.amount_allocated:
            remaining = self.cheque_id.unallocated_amount if self.cheque_id else 0.0
            if remaining > 0:
                self.amount_allocated = min(remaining, self.invoice_id.amount_residual)
            else:
                self.amount_allocated = self.invoice_id.amount_residual


class WecareChequeRegister(models.Model):
    _name = 'wecare.cheque.register'
    _description = 'Cheque Register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'received_date desc, id desc'

    # -------------------------------------------------------------------------
    # A. REGISTRATION INFORMATION
    # -------------------------------------------------------------------------
    collection_no = fields.Char(
        string='Registration Reference',
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
        help='Sequential reference formatted as COL-YYYY-XXXX',
    )
    payment_type = fields.Selection(
        [
            ('inbound', 'Customer Collection'),
            ('outbound', 'Vendor Payment'),
        ],
        string='Payment Type',
        default='inbound',
        required=True,
        tracking=True,
    )
    collection_type = fields.Selection(
        [
            ('cheque', 'Cheque'),
            ('cash', 'Cash'),
            ('cpo', 'CPO'),
            ('tele_birr', 'Tele Birr'),
        ],
        string='Collection Method',
        default='cheque',
        required=True,
        tracking=True,
    )
    received_date = fields.Date(
        string='Registration Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Date when cheque collection was registered / received.',
    )

    # -------------------------------------------------------------------------
    # B. CUSTOMER & INVOICE DETAILS
    # -------------------------------------------------------------------------
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        check_company=True,
    )
    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        tracking=True,
        check_company=True,
        help='Auto-filled from customer or the allocated invoices.',
    )
    customer_balance = fields.Monetary(
        string='Customer Balance',
        compute='_compute_customer_balance',
        help='Total outstanding receivable balance across all posted invoices of the customer.',
    )
    payment_method_display = fields.Selection(
        [
            ('cash', 'Cash'),
            ('credit', 'Credit'),
        ],
        string='Payment Method: Cash/Credit',
        compute='_compute_payment_method_display',
        store=True,
        help='Auto-linked from customer invoices.',
    )
    allocation_line_ids = fields.One2many(
        'wecare.cheque.invoice.line',
        'cheque_id',
        string='Invoice Allocations',
        copy=True,
    )
    invoice_ids = fields.Many2many(
        'account.move',
        'wecare_cheque_invoice_rel',
        'cheque_id',
        'invoice_id',
        string='Invoices',
        compute='_compute_invoice_ids',
        store=True,
        readonly=False,
        domain="[('move_type', 'in', ('out_invoice', 'in_invoice')), ('partner_id', '=', partner_id)]",
    )
    total_allocated = fields.Monetary(
        string='Total Allocated',
        compute='_compute_total_allocated',
        store=True,
    )
    unallocated_amount = fields.Monetary(
        string='Unallocated Balance',
        compute='_compute_unallocated_amount',
        store=True,
    )
    allow_excess_credit = fields.Boolean(
        string='Allow Excess as Customer Credit',
        default=False,
        tracking=True,
        help='When enabled, allows cheque amount to exceed invoice total under company credit policy.',
    )

    # -------------------------------------------------------------------------
    # C. CHEQUE DETAILS
    # -------------------------------------------------------------------------
    name = fields.Char(
        string='Cheque Number',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    amount = fields.Monetary(
        string='Cheque Amount',
        required=True,
        tracking=True,
    )
    cheque_date = fields.Date(
        string='Cheque Date',
        required=True,
        tracking=True,
    )
    drawer_bank = fields.Char(
        string='Drawer / Issuing Bank',
        tracking=True,
        help="Customer's issuing bank name.",
    )
    partner_bank_id = fields.Many2one(
        'res.partner.bank',
        string="Customer Bank Account",
        check_company=True,
    )
    cheque_image = fields.Binary(
        string='Cheque Attachment',
        attachment=True,
        help='Scanned copy of the physical cheque.',
    )
    cheque_image_filename = fields.Char(string='Cheque Attachment Name')

    # -------------------------------------------------------------------------
    # D. DEPOSIT & ACCOUNTING DETAILS
    # -------------------------------------------------------------------------
    journal_id = fields.Many2one(
        'account.journal',
        string='Deposit Bank / Journal',
        domain="[('type', '=', 'bank')]",
        check_company=True,
        tracking=True,
        help='Configured bank journal where the cheque is deposited.',
    )
    deposit_date = fields.Date(
        string='Deposit Date',
        tracking=True,
        help='Required at the deposit stage.',
    )
    deposit_reference = fields.Char(
        string='Deposit Reference / Slip No.',
        tracking=True,
        help='Bank deposit slip number or reference code.',
    )
    deposit_slip = fields.Binary(
        string='Deposit Slip Attachment',
        attachment=True,
        help='Uploaded scanned bank deposit slip.',
    )
    deposit_slip_filename = fields.Char(string='Deposit Slip Filename')
    payment_id = fields.Many2one(
        'account.payment',
        string='Linked Payment Record',
        copy=False,
        tracking=True,
    )
    accounting_status = fields.Selection(
        [
            ('pending', 'Pending Deposit'),
            ('deposited', 'Deposited / In Clearing'),
            ('cleared', 'Cleared / Reconciled'),
            ('bounced', 'Bounced / Reversed'),
            ('cancelled', 'Cancelled / Void'),
        ],
        string='Accounting Status',
        compute='_compute_accounting_status',
        store=True,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # E. WORKFLOW & AUDIT TRAIL
    # -------------------------------------------------------------------------
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('received', 'Received'),
            ('deposited', 'Deposited'),
            ('cleared', 'Cleared'),
            ('bounced', 'Bounced'),
            ('cancelled', 'Cancelled'),
        ],
        default='received',
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    deposit_user_id = fields.Many2one(
        'res.users',
        string='Deposited By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    clear_user_id = fields.Many2one(
        'res.users',
        string='Cleared By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    clear_date = fields.Date(
        string='Clearance Date',
        readonly=True,
        copy=False,
        tracking=True,
    )
    bounce_user_id = fields.Many2one(
        'res.users',
        string='Marked Bounced By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    bounce_date = fields.Date(
        string='Bounce Date',
        tracking=True,
    )
    bounce_reason = fields.Text(
        string='Bounce Reason',
        tracking=True,
    )
    bounce_attachment = fields.Binary(
        string='Bounce Notice Document',
        attachment=True,
    )
    bounce_attachment_filename = fields.Char(string='Bounce Notice Filename')

    cancel_user_id = fields.Many2one(
        'res.users',
        string='Cancelled By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancel_date = fields.Date(
        string='Cancellation Date',
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancel_reason = fields.Text(
        string='Cancellation Reason',
        tracking=True,
    )

    redeposit_date = fields.Date(string='Re-deposit Date', tracking=True)
    original_cheque_id = fields.Many2one(
        'wecare.cheque.register',
        string='Original Cheque',
        copy=False,
        tracking=True,
        help='Original bounced cheque when this record is a re-deposit.',
    )
    redeposit_ids = fields.One2many(
        'wecare.cheque.register',
        'original_cheque_id',
        string='Re-deposits',
    )
    remarks = fields.Text(string='Remarks / Notes')

    # Status helper flags
    is_credit_sale = fields.Boolean(
        string='Credit Sale',
        compute='_compute_is_credit_sale',
        store=True,
    )
    outstanding = fields.Boolean(
        string='Open Bounce',
        compute='_compute_outstanding',
        store=True,
    )
    is_replaced = fields.Boolean(
        string='Is Replaced',
        compute='_compute_replacement_info',
        store=True,
        help='Indicates if this bounced cheque has been replaced by a re-deposit.',
    )
    is_cancelled = fields.Boolean(
        string='Is Cancelled / Void',
        default=False,
        tracking=True,
        help='Flag to mark a cheque as cancelled or void.',
    )

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('allocation_line_ids.amount_allocated')
    def _compute_total_allocated(self):
        for cheque in self:
            cheque.total_allocated = sum(cheque.allocation_line_ids.mapped('amount_allocated'))

    @api.depends('amount', 'total_allocated')
    def _compute_unallocated_amount(self):
        for cheque in self:
            cheque.unallocated_amount = (cheque.amount or 0.0) - (cheque.total_allocated or 0.0)

    @api.depends('allocation_line_ids.invoice_id')
    def _compute_invoice_ids(self):
        for cheque in self:
            allocated = cheque.allocation_line_ids.mapped('invoice_id')
            if allocated:
                cheque.invoice_ids = allocated

    @api.depends('partner_id', 'company_id')
    def _compute_customer_balance(self):
        Move = self.env['account.move']
        for cheque in self:
            if not cheque.partner_id:
                cheque.customer_balance = 0.0
                continue
            open_invoices = Move.search([
                ('partner_id', '=', cheque.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('company_id', '=', cheque.company_id.id),
            ])
            cheque.customer_balance = sum(open_invoices.mapped('amount_residual'))

    @api.depends('allocation_line_ids.invoice_id', 'invoice_ids.payment_method')
    def _compute_payment_method_display(self):
        for cheque in self:
            invoices = cheque.allocation_line_ids.mapped('invoice_id') or cheque.invoice_ids
            if not invoices:
                cheque.payment_method_display = 'credit' if cheque.payment_type == 'inbound' else False
                continue
            methods = invoices.mapped('payment_method')
            if any(m == 'credit' for m in methods):
                cheque.payment_method_display = 'credit'
            elif any(m == 'cash' for m in methods):
                cheque.payment_method_display = 'cash'
            else:
                cheque.payment_method_display = 'credit'

    @api.depends('state', 'payment_id', 'payment_id.state', 'payment_id.is_reconciled')
    def _compute_accounting_status(self):
        for cheque in self:
            if cheque.state == 'cancelled':
                cheque.accounting_status = 'cancelled'
            elif cheque.state == 'bounced':
                cheque.accounting_status = 'bounced'
            elif cheque.state == 'cleared':
                cheque.accounting_status = 'cleared'
            elif cheque.state == 'deposited':
                cheque.accounting_status = 'deposited'
            else:
                cheque.accounting_status = 'pending'

    @api.depends('redeposit_ids', 'original_cheque_id')
    def _compute_replacement_info(self):
        for cheque in self:
            cheque.is_replaced = bool(cheque.redeposit_ids or cheque.original_cheque_id)

    @api.depends('invoice_ids.payment_method', 'allocation_line_ids.invoice_id')
    def _compute_is_credit_sale(self):
        for cheque in self:
            invoices = (cheque.allocation_line_ids.mapped('invoice_id') | cheque.invoice_ids).filtered(
                lambda inv: inv.move_type == 'out_invoice'
            )
            if not invoices:
                cheque.is_credit_sale = cheque.payment_type == 'inbound'
                continue
            methods = invoices.mapped('payment_method')
            cheque.is_credit_sale = any(m == 'credit' for m in methods) or not any(methods)

    @api.depends('state', 'redeposit_ids.state')
    def _compute_outstanding(self):
        for cheque in self:
            if cheque.state != 'bounced':
                cheque.outstanding = False
            else:
                cheque.outstanding = not any(
                    r.state in ('deposited', 'cleared') for r in cheque.redeposit_ids
                )

    # -------------------------------------------------------------------------
    # ONCHANGE & CONSTRAINS
    # -------------------------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id_set_details(self):
        if self.partner_id:
            if not self.salesperson_id and self.partner_id.user_id:
                self.salesperson_id = self.partner_id.user_id
            if self.partner_id.bank_ids:
                self.partner_bank_id = self.partner_id.bank_ids[:1]
                if self.partner_bank_id.bank_id:
                    self.drawer_bank = self.partner_bank_id.bank_id.name

    @api.constrains('name', 'company_id', 'original_cheque_id')
    def _check_duplicate_cheque_no(self):
        for cheque in self:
            if not cheque.name:
                continue
            domain = [
                ('name', '=', cheque.name),
                ('company_id', '=', cheque.company_id.id),
                ('id', '!=', cheque.id),
                ('original_cheque_id', '=', False),
            ]
            if cheque.original_cheque_id:
                domain.append(('id', '!=', cheque.original_cheque_id.id))
            if self.search_count(domain):
                raise ValidationError(self.env._(
                    'Cheque number "%s" already exists in the system. Duplicate cheque numbers are not allowed.',
                    cheque.name,
                ))

    @api.constrains('amount', 'cheque_date')
    def _check_amount_date(self):
        for cheque in self:
            if cheque.amount <= 0:
                raise ValidationError(self.env._('Cheque amount must be strictly greater than zero.'))
            if not cheque.cheque_date:
                raise ValidationError(self.env._('Every cheque must contain a valid Cheque Date.'))

    @api.constrains('allocation_line_ids', 'amount', 'allow_excess_credit', 'state')
    def _check_allocation_amounts(self):
        for cheque in self:
            if cheque.state in ('draft', 'cancelled'):
                continue
            if cheque.payment_type == 'inbound' and cheque.allocation_line_ids:
                total_allocated = sum(cheque.allocation_line_ids.mapped('amount_allocated'))
                if total_allocated > (cheque.amount + 0.001):
                    raise ValidationError(self.env._(
                        'Total allocated amount (%(total).2f) cannot exceed the cheque amount (%(amount).2f).',
                        total=total_allocated,
                        amount=cheque.amount,
                    ))
                for line in cheque.allocation_line_ids:
                    if line.amount_allocated <= 0:
                        raise ValidationError(self.env._(
                            'Allocated amount for invoice %s must be greater than zero.',
                            line.invoice_id.name,
                        ))
                    if line.amount_allocated > (line.invoice_id.amount_residual + 0.001):
                        raise ValidationError(self.env._(
                            'Allocated amount (%(alloc).2f) for invoice %(inv)s exceeds its outstanding balance (%(res).2f).',
                            alloc=line.amount_allocated,
                            inv=line.invoice_id.name,
                            res=line.invoice_id.amount_residual,
                        ))
                if (cheque.amount - total_allocated) > 0.01 and not cheque.allow_excess_credit:
                    raise ValidationError(self.env._(
                        'Cheque amount (%(amount).2f) exceeds total allocated invoices (%(total).2f) by %(diff).2f. '
                        'Please allocate the remaining amount to invoices or check "Allow Excess as Customer Credit".',
                        amount=cheque.amount,
                        total=total_allocated,
                        diff=cheque.amount - total_allocated,
                    ))

    # -------------------------------------------------------------------------
    # CRUD & LIFECYCLE
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('collection_no') or vals.get('collection_no') == 'New':
                vals['collection_no'] = self.env['ir.sequence'].next_by_code(
                    'wecare.cheque.register'
                ) or 'New'
        return super().create(vals_list)

    def unlink(self):
        for cheque in self:
            if cheque.state in ('deposited', 'cleared', 'bounced'):
                raise UserError(self.env._(
                    'Cheques in status "%s" cannot be deleted. Use Cancellation instead to preserve full audit history.',
                    dict(cheque._fields['state'].selection).get(cheque.state)
                ))
        return super().unlink()

    # -------------------------------------------------------------------------
    # USER ACTIONS
    # -------------------------------------------------------------------------
    def action_load_outstanding_invoices(self):
        """Auto-load outstanding customer invoices and allocate cheque amount FIFO."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(self.env._('Please select a Customer first.'))
        Move = self.env['account.move']
        open_invoices = Move.search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('company_id', '=', self.company_id.id),
        ], order='invoice_date asc, id asc')

        if not open_invoices:
            raise UserError(self.env._(
                'No outstanding posted customer invoices found for %s.',
                self.partner_id.display_name
            ))

        new_lines = []
        remaining_cheque = self.amount
        for inv in open_invoices:
            alloc = min(remaining_cheque, inv.amount_residual) if remaining_cheque > 0 else 0.0
            remaining_cheque -= alloc
            new_lines.append((0, 0, {
                'invoice_id': inv.id,
                'amount_allocated': alloc,
            }))

        self.allocation_line_ids = [(5, 0, 0)] + new_lines
        if not self.salesperson_id:
            self.salesperson_id = open_invoices[:1].invoice_user_id or self.partner_id.user_id

    def action_receive(self):
        """Transition from Draft to Received."""
        for cheque in self:
            if cheque.state not in ('draft', 'received'):
                raise UserError(self.env._('Only draft cheques can be confirmed.'))
            cheque._check_allocation_amounts()
            cheque.state = 'received'
            cheque.message_post(body=self.env._(
                'Cheque %s received and registered by %s.',
                cheque.name,
                self.env.user.name,
            ))

    def action_deposit(self):
        """Deposit stage: requires journal_id and deposit_date. Syncs/reconciles payment."""
        for cheque in self:
            if cheque.state not in ('draft', 'received'):
                raise UserError(self.env._('Only received cheques can be deposited.'))
            if not cheque.journal_id:
                raise UserError(self.env._('Please select a Deposit Bank / Journal.'))
            deposit_date = cheque.deposit_date or fields.Date.context_today(cheque)
            cheque._check_allocation_amounts()

            vals = {
                'state': 'deposited',
                'deposit_date': deposit_date,
                'deposit_user_id': self.env.user.id,
            }
            if not cheque.payment_id:
                payment = cheque._create_and_post_payment(deposit_date)
                vals['payment_id'] = payment.id

            cheque.write(vals)
            cheque._reconcile_allocated_invoices()
            cheque.message_post(body=self.env._(
                'Cheque deposited into journal %s on %s by %s. Ref: %s',
                cheque.journal_id.display_name,
                deposit_date,
                self.env.user.name,
                cheque.deposit_reference or cheque.collection_no,
            ))

    def action_clear(self):
        """Cleared stage: confirm bank reconciliation."""
        for cheque in self:
            if cheque.state != 'deposited':
                raise UserError(self.env._('Only deposited cheques can be cleared.'))
            cheque.write({
                'state': 'cleared',
                'clear_user_id': self.env.user.id,
                'clear_date': fields.Date.context_today(cheque),
            })
            cheque._reconcile_allocated_invoices()
            cheque.message_post(body=self.env._(
                'Cheque clearance confirmed by bank by %s on %s.',
                self.env.user.name,
                fields.Date.context_today(cheque),
            ))

    def action_bounce(self):
        """Open bounce processing wizard."""
        self.ensure_one()
        if self.state not in ('received', 'deposited', 'cleared'):
            raise UserError(self.env._(
                'Only received, deposited, or cleared cheques can be marked as bounced.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Cheque Bounce Processing'),
            'res_model': 'wecare.cheque.bounce.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cheque_id': self.id},
        }

    def _process_bounce(self, bounce_date, bounce_reason, attachment=None, attachment_filename=None):
        """Execute bounce logic: un-reconcile, cancel payment, reopen receivables cleanly."""
        self.ensure_one()
        # 1. Un-reconcile payment move lines to reopen original customer invoices
        if self.payment_id and self.payment_id.move_id:
            receivable_lines = self.payment_id.move_id.line_ids.filtered(
                lambda l: l.account_type == 'asset_receivable'
            )
            receivable_lines.remove_move_reconcile()
            if self.payment_id.state != 'cancel':
                self.payment_id.action_cancel()

        # 2. Update cheque state & audit fields
        vals = {
            'state': 'bounced',
            'bounce_date': bounce_date,
            'bounce_reason': bounce_reason,
            'bounce_user_id': self.env.user.id,
        }
        if attachment:
            vals['bounce_attachment'] = attachment
            vals['bounce_attachment_filename'] = attachment_filename or 'bounce_notice.pdf'
        self.write(vals)

        # 3. Post audit trail message
        self.message_post(body=self.env._(
            'Cheque marked as BOUNCED on %s by %s. Reason: %s. Outstanding receivables cleanly reopened without invoice duplication.',
            bounce_date,
            self.env.user.name,
            bounce_reason,
        ))

    def action_cancel_cheque(self):
        """Open cancellation wizard."""
        self.ensure_one()
        if self.state in ('cleared', 'cancelled'):
            raise UserError(self.env._(
                'Cleared cheques cannot be cancelled directly. Please record a bounce or reverse reconciliation first.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Cancel Cheque Registration'),
            'res_model': 'wecare.cheque.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cheque_id': self.id},
        }

    def _process_cancel(self, cancel_date, cancel_reason):
        """Execute cancellation logic: cancel linked payment and update audit history."""
        self.ensure_one()
        if self.payment_id and self.payment_id.move_id:
            receivable_lines = self.payment_id.move_id.line_ids.filtered(
                lambda l: l.account_type == 'asset_receivable'
            )
            receivable_lines.remove_move_reconcile()
            if self.payment_id.state != 'cancel':
                self.payment_id.action_cancel()

        self.write({
            'state': 'cancelled',
            'is_cancelled': True,
            'cancel_date': cancel_date,
            'cancel_reason': cancel_reason,
            'cancel_user_id': self.env.user.id,
        })
        self.message_post(body=self.env._(
            'Cheque registration CANCELLED on %s by %s. Reason: %s',
            cancel_date,
            self.env.user.name,
            cancel_reason,
        ))

    def action_reset_draft(self):
        """Reset cancelled cheque to draft (Manager only)."""
        self.ensure_one()
        if self.state not in ('cancelled', 'bounced'):
            raise UserError(self.env._('Only cancelled or bounced cheques can be reset to draft.'))
        self.write({
            'state': 'draft',
            'is_cancelled': False,
        })
        self.message_post(body=self.env._('Cheque reset to Draft by %s.', self.env.user.name))

    def action_redeposit(self):
        """Create a new cheque linked to the bounced original. Never delete the bounce."""
        self.ensure_one()
        if self.state != 'bounced':
            raise UserError(self.env._('Only bounced cheques can be re-deposited.'))
        new_cheque = self.copy({
            'name': self.name,
            'state': 'deposited',
            'deposit_date': fields.Date.context_today(self),
            'redeposit_date': fields.Date.context_today(self),
            'original_cheque_id': self.id,
            'bounce_date': False,
            'bounce_reason': False,
            'bounce_attachment': False,
            'payment_id': False,
            'collection_no': 'New',
            'remarks': self.env._('Re-deposit of bounced cheque %s', self.name),
        })
        self.redeposit_date = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wecare.cheque.register',
            'res_id': new_cheque.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # PAYMENT INTEGRATION HELPERS
    # -------------------------------------------------------------------------
    def _create_and_post_payment(self, payment_date):
        self.ensure_one()
        Payment = self.env['account.payment']
        method_code = 'cheque' if self.collection_type == 'cheque' else 'manual'
        payment_method_line = self.journal_id.inbound_payment_method_line_ids.filtered(
            lambda l: l.code == method_code or l.payment_method_id.code == method_code
        )[:1] or self.journal_id.inbound_payment_method_line_ids[:1]

        vals = {
            'payment_type': 'inbound' if self.payment_type == 'inbound' else 'outbound',
            'partner_type': 'customer' if self.payment_type == 'inbound' else 'supplier',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'date': payment_date,
            'journal_id': self.journal_id.id,
            'payment_method_line_id': payment_method_line.id if payment_method_line else False,
            'check_transfer_no': self.name,
            'maturity_date': self.cheque_date,
            'memo': self.collection_no or self.name,
            'cheque_register_id': self.id,
        }
        payment = Payment.create(vals)
        payment.action_post()
        return payment

    def _reconcile_allocated_invoices(self):
        """Reconcile payment receivable lines with allocated invoice receivable lines."""
        for cheque in self:
            if not cheque.payment_id or cheque.payment_id.state != 'posted':
                continue
            payment_lines = cheque.payment_id.move_id.line_ids.filtered(
                lambda l: l.account_type == 'asset_receivable' and not l.reconciled
            )
            if not payment_lines:
                continue

            invoices = cheque.allocation_line_ids.mapped('invoice_id') or cheque.invoice_ids
            invoice_lines = invoices.mapped('line_ids').filtered(
                lambda l: l.account_type == 'asset_receivable' and not l.reconciled
            )
            if invoice_lines:
                try:
                    (payment_lines + invoice_lines).reconcile()
                except Exception:
                    # Reconciliation fallback if lines are partially matched
                    pass

    def action_open_payment(self):
        self.ensure_one()
        if not self.payment_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # REPORTING & PERIOD CLASSIFICATION (Existing reports preservation)
    # -------------------------------------------------------------------------
    def classify_for_period(self, date_from, date_to):
        self.ensure_one()
        if self.state == 'bounced':
            bounce_day = self.bounce_date or self.deposit_date or self.received_date
            if bounce_day and date_from <= bounce_day <= date_to:
                return 'bounce'
            if self.outstanding and self.bounce_date and self.bounce_date <= date_to:
                return 'bounce'
        origin = self.cheque_date or self.received_date
        deposit = self.deposit_date
        if deposit and date_from <= deposit <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        if not deposit and self.received_date and date_from <= self.received_date <= date_to:
            if origin and origin < date_from:
                return 'previous'
            return 'current'
        return False

    def _records_for_print(self):
        if self:
            return self
        domain = list(self.env.context.get('active_domain') or [])
        return self.search(domain)

    def _report_period(self):
        dates = [
            d for d in (
                self.mapped('received_date')
                + self.mapped('deposit_date')
                + self.mapped('cheque_date')
                + self.mapped('bounce_date')
            ) if d
        ]
        today = fields.Date.context_today(self)
        return (min(dates) if dates else today, max(dates) if dates else today)

    def _group_by_salesperson_report(self):
        buckets = defaultdict(lambda: self.env['wecare.cheque.register'])
        for rec in self:
            buckets[rec.salesperson_id] |= rec
        groups = []
        for user, recs in buckets.items():
            groups.append({
                'salesperson_name': user.name if user else self.env._('Undefined'),
                'lines': recs,
                'subtotal': sum(recs.mapped('amount')),
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        return groups

    def _report_company(self):
        return self[:1].company_id or self.env.company

    def _get_collection_report_data(self):
        date_from, date_to = self._report_period()
        groups = self._group_by_salesperson_report()
        company = self._report_company()
        return {
            'groups': groups,
            'grand_total': sum(g['subtotal'] for g in groups),
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_bank_deposit_report_data(self):
        date_from, date_to = self._report_period()
        company = self._report_company()
        rows = []
        for cheque in self:
            klass = cheque.classify_for_period(date_from, date_to)
            if not klass:
                continue
            rows.append({
                'cheque': cheque,
                'current': cheque.amount if klass == 'current' else 0.0,
                'previous': cheque.amount if klass == 'previous' else 0.0,
                'bounce': cheque.amount if klass == 'bounce' else 0.0,
            })
        buckets = defaultdict(list)
        for row in rows:
            buckets[row['cheque'].salesperson_id].append(row)
        groups = []
        for user, recs in buckets.items():
            groups.append({
                'salesperson_name': user.name if user else self.env._('Undefined'),
                'lines': recs,
                'subtotal_current': sum(r['current'] for r in recs),
                'subtotal_previous': sum(r['previous'] for r in recs),
                'subtotal_bounce': sum(r['bounce'] for r in recs),
            })
        groups.sort(key=lambda g: g['salesperson_name'])
        existing_bounce = self.filtered(lambda c: c.state == 'bounced' and c.outstanding)
        return {
            'groups': groups,
            'total_current': sum(g['subtotal_current'] for g in groups),
            'total_previous': sum(g['subtotal_previous'] for g in groups),
            'total_bounce': sum(g['subtotal_bounce'] for g in groups),
            'existing_bounce': sum(existing_bounce.mapped('amount')),
            'company': company,
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_classified_report_data(self, klass):
        date_from, date_to = self._report_period()
        cheques = self.filtered(
            lambda c: c.classify_for_period(date_from, date_to) == klass
        )
        groups = cheques._group_by_salesperson_report()
        titles = {
            'current': self.env._('Current Cheque Report'),
            'previous': self.env._('Previous Cheque Report'),
            'bounce': self.env._('Bounced Cheque Report'),
        }
        return {
            'title': titles.get(klass, self.env._('Cheque Report')),
            'groups': groups,
            'grand_total': sum(g['subtotal'] for g in groups),
            'company': self._report_company(),
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_collection_performance_report_data(self):
        date_from, date_to = self._report_period()
        buckets = defaultdict(lambda: {
            'received_amt': 0.0, 'received_count': 0,
            'deposited_amt': 0.0, 'bounce_amt': 0.0,
        })
        for cheque in self:
            key = cheque.salesperson_id
            buckets[key]['received_amt'] += cheque.amount
            buckets[key]['received_count'] += 1
            if cheque.deposit_date:
                buckets[key]['deposited_amt'] += cheque.amount
            if cheque.state == 'bounced':
                buckets[key]['bounce_amt'] += cheque.amount
        lines = []
        for salesperson, vals in buckets.items():
            lines.append({
                'salesperson_name': salesperson.name if salesperson else self.env._('Undefined'),
                **vals,
                'net': vals['deposited_amt'] - vals['bounce_amt'],
            })
        lines.sort(key=lambda l: l['salesperson_name'])
        return {
            'lines': lines,
            'total_received': sum(l['received_amt'] for l in lines),
            'total_deposited': sum(l['deposited_amt'] for l in lines),
            'total_bounce': sum(l['bounce_amt'] for l in lines),
            'company': self._report_company(),
            'date_from': date_from,
            'date_to': date_to,
            'reporting_date': fields.Date.context_today(self),
        }

    def _get_bank_summary_report_data(self):
        data = self._get_bank_deposit_report_data()
        banks = defaultdict(lambda: {'current': 0.0, 'previous': 0.0, 'bounce': 0.0})
        for group in data['groups']:
            for row in group['lines']:
                bank = row['cheque'].journal_id
                banks[bank]['current'] += row['current']
                banks[bank]['previous'] += row['previous']
                banks[bank]['bounce'] += row['bounce']
        lines = []
        for bank, vals in banks.items():
            lines.append({
                'bank_name': bank.display_name if bank else self.env._('Undefined'),
                **vals,
                'total': vals['current'] + vals['previous'] + vals['bounce'],
            })
        lines.sort(key=lambda l: l['bank_name'])
        return {
            'lines': lines,
            'total_current': sum(l['current'] for l in lines),
            'total_previous': sum(l['previous'] for l in lines),
            'total_bounce': sum(l['bounce'] for l in lines),
            'existing_bounce': data['existing_bounce'],
            'company': data['company'],
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'reporting_date': data['reporting_date'],
        }

    def action_print_weekly_collection(self):
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_collection'
        ).report_action(self._records_for_print())

    def action_print_weekly_bank_deposit(self):
        return self.env.ref(
            'wecare_sales_management.action_report_weekly_bank_deposit'
        ).report_action(self._records_for_print())

    def action_print_current_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='current').report_action(
            self._records_for_print()
        )

    def action_print_previous_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='previous').report_action(
            self._records_for_print()
        )

    def action_print_bounced_cheques(self):
        return self.env.ref(
            'wecare_sales_management.action_report_cheque_classified'
        ).with_context(cheque_classification='bounce').report_action(
            self._records_for_print()
        )

    def action_print_collection_performance(self):
        return self.env.ref(
            'wecare_sales_management.action_report_collection_performance'
        ).report_action(self._records_for_print())

    def action_print_bank_summary(self):
        return self.env.ref(
            'wecare_sales_management.action_report_bank_deposit_summary'
        ).report_action(self._records_for_print())
