# -*- coding: utf-8 -*-
# hr_employee.py

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    current_employee_cost = fields.Float(
        string='Current Employee Cost',
        compute='_compute_current_employee_cost',
        store=True,
    )

    historical_cost_ids = fields.One2many(
        'hr.employee.cost.line',
        'employee_id',
        string='Historical Costs'
    )


    @api.depends('historical_cost_ids', 'historical_cost_ids.cost',
                 'historical_cost_ids.cost_id.date_from', 'historical_cost_ids.cost_id.date_to')
    def _compute_current_employee_cost(self):
        Cost = self.env['hr.employee.cost']
        CostLine = self.env['hr.employee.cost.line']

        for emp in self:
            today = fields.Date.context_today(emp)

            # 1) Find the most recent confirmed cost header that covers "today"
            cost_header = Cost.search([
                ('state', '=', 'confirmed'),
                ('date_from', '<=', today),
                ('date_to', '>=', today),
            ], order='date_from desc, id desc', limit=1)

            cost = 0.0
            if cost_header:
                # 2) Find that employee's line inside this header
                line = CostLine.search([
                    ('cost_id', '=', cost_header.id),
                    ('employee_id', '=', emp.id),
                ], limit=1)
                if line:
                    cost = line.cost or 0.0

            emp.current_employee_cost = cost

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    current_employee_cost = fields.Float(
        string='Current Employee Cost',
        readonly=True
    )



class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    # Employee cost
    employee_cost = fields.Float(
        compute='_compute_employee_cost',
        store=True,
    )
    total_employee_cost = fields.Float(
        compute='_compute_employee_cost',
        store=True,
    )

    # Stage (computed)
    timesheet_status_id = fields.Many2one(
        "hr.timesheet.status",
        string="Timesheet Stage",
        store=True,
        compute='_compute_timesheet_status_id',
        readonly=False,
        domain="[('id', 'in', project_id.allowed_stage_ids or [])]"
    )

    # Useful for domain
    allowed_stage_ids = fields.Many2many(
        related='project_id.allowed_stage_ids',
        readonly=True
    )

    # Stage Fee (computed)
    stage_fee = fields.Float(
        compute='_compute_stage_fee',
        store=True,
    )
    # total_stage_fee = fields.Float(
    #     compute='_compute_stage_fee',
    #     store=True,
    # )
    # total_project_stage_fee = fields.Float(
    #     compute='_compute_stage_fee',
    #     store=True,
    # )

    # ===============================================================
    #  EMPLOYEE COST COMPUTE
    # ===============================================================
    @api.depends('employee_id', 'employee_id.current_employee_cost', 'date', 'unit_amount')
    def _compute_employee_cost(self):
        Cost = self.env['hr.employee.cost']
        CostLine = self.env['hr.employee.cost.line']

        for line in self:
            if not line.employee_id or not line.date:
                line.employee_cost = 0.0
                line.total_employee_cost = 0.0
                continue

            cost_header = Cost.search([
                ('state', '=', 'confirmed'),
                ('date_from', '<=', line.date),
                ('date_to', '>=', line.date),
            ], order='date_from desc, id desc', limit=1)

            cost = 0.0
            if cost_header:
                cost_line = CostLine.search([
                    ('cost_id', '=', cost_header.id),
                    ('employee_id', '=', line.employee_id.id),
                ], limit=1)
                cost = cost_line.cost or 0.0 if cost_line else 0.0

            line.employee_cost = cost
            line.total_employee_cost = cost * (line.unit_amount or 0.0)

    # ===============================================================
    #  COMPUTE TIMESHEET STAGE (TASK → PROJECT → EMPTY)
    # ===============================================================
    @api.depends(
        'project_id',
        'project_id.timesheet_status_id'
    )
    def _compute_timesheet_status_id(self):
        for line in self:
            stage = False

            # Priority 1: Task stage
            if line.project_id and line.project_id.timesheet_status_id:
                stage = line.project_id.timesheet_status_id

            # Priority 2: Project stage
            elif line.project_id and line.project_id.timesheet_status_id:
                stage = line.project_id.timesheet_status_id

            line.timesheet_status_id = stage

    # ===============================================================
    #  COMPUTE STAGE FEE
    # ===============================================================
    @api.depends(
        'project_id.total_stage_cost',
        'project_id.stage_cost_ids.amount',
        'project_id.stage_cost_ids.total_amount',
        'project_id.stage_cost_ids.timesheet_status_id',
        'timesheet_status_id',
        'status_id'
    )
    def _compute_stage_fee(self):

        # ✅ Pre-group lines by project
        lines_by_project = {}
        for line in self:
            lines_by_project.setdefault(line.project_id, []).append(line)

        for project, lines in lines_by_project.items():
            if not project:
                continue

            # ✅ Pre-map stage cost by status
            stage_map = {
                stage.timesheet_status_id.id: stage.amount
                for stage in project.stage_cost_ids
                if stage.timesheet_status_id
            }

            # ✅ Print ONCE per project
            for status_id, amount in stage_map.items():
                status_name = project.stage_cost_ids.filtered(
                    lambda s: s.timesheet_status_id.id == status_id
                ).timesheet_status_id.name
                print(status_name, ":", amount)

            # ✅ Assign value per line (NO recomputation)
            for line in lines:
                valid_status_ids = {
                                       line.timesheet_status_id.id,
                                       line.status_id.id,
                                   } - {None}

                matched_amount = next(
                    (
                        stage_map[status_id]
                        for status_id in valid_status_ids
                        if status_id in stage_map
                    ),
                    0.0
                )

                line.stage_fee = matched_amount

