# models/hr_employee_cost.py
# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

class HrEmployeeCost(models.Model):
    _name = 'hr.employee.cost'
    _description = 'Employee Cost Header'
    _order = 'date_from desc'

    name = fields.Char('Reference', required=True, default='New', copy=False)
    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', required=True)
    cost_line_ids = fields.One2many('hr.employee.cost.line', 'cost_id', string='Cost Lines')
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default='draft')
    employee_count = fields.Integer(compute='_compute_employee_count')

    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Cost Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.cost.line',
            'view_mode': 'tree,form',
            'domain': [('cost_id', '=', self.id)],
            'context': {'default_cost_id': self.id},
        }

    @api.model
    def get_cost_for_date(self, employee_id, date):
        """
        Returns the employee's cost applicable for the given date.
        Looks up hr.employee.cost.line based on date range.
        """
        if not employee_id or not date:
            return 0.0

        record = self.search([
            ('state', '=', 'confirmed'),
            ('date_from', '<=', date),
            ('date_to', '>=', date),
            ('cost_line_ids.employee_id', '=', employee_id),
        ], order='date_from desc', limit=1)

        if record and record.cost_line_ids:
            lines = record.cost_line_ids.filtered(
                lambda l: l.employee_id.id == employee_id)
            for line in lines:
                return line.cost if line else 0.0
        return 0.0

    @api.depends('cost_line_ids')
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.cost_line_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.cost') or 'New'
        return super().create(vals)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_draft(self):
        self.write({'state': 'draft'})

class HrEmployeeCostLine(models.Model):
    _name = 'hr.employee.cost.line'
    _description = 'Employee Cost Line'

    cost_id = fields.Many2one('hr.employee.cost', string='Cost Header', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    cost = fields.Float('Cost per Hour', required=True, digits='Account Cost Price')
    date_from = fields.Date(related='cost_id.date_from', store=True, readonly=True)
    date_to = fields.Date(related='cost_id.date_to', store=True, readonly=True)