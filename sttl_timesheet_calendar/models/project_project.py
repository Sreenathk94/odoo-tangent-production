# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    allowed_stage_ids = fields.Many2many(
        "hr.timesheet.status",
        'allowed_stage_project_rel',
        string='Stages',
        order='sequence asc'
    )

    timesheet_status_id = fields.Many2one(
        "hr.timesheet.status",
        'Stages',
        order='sequence asc',
        domain="[('id', 'in', allowed_stage_ids)]"
    )

    timesheet_count = fields.Integer(
        "Timesheet Count",
        compute="_get_timesheet_count"
    )

    timesheet_duration = fields.Float(
        "Timesheet Durations(HH:MM)",
        compute="_get_timesheet_duration"
    )

    is_project_start_mail_sent = fields.Boolean(
        "Project Start Mail Sent?",
        default=False,
        copy=False
    )

    # Stage-wise base + total cost
    stage_cost_ids = fields.One2many(
        'project.cost.stage',
        'project_id',
        string='Stage wise cost'
    )

    # All variation lines for this project
    variation_ids = fields.One2many(
        'project.cost.stage.variation',
        'project_id',
        string="Stage Variations"
    )

    # Total cost of all stages (base + variations)
    total_stage_cost = fields.Float(
        string="Total Stage Cost",
        compute="_compute_total_stage_cost",
        store=False
    )

    total_project_cost = fields.Float(
        string="Total Stage Cost", store=True,

    )

    @api.depends('stage_cost_ids.total_amount')
    def _compute_total_stage_cost(self):
        for rec in self:
            rec.total_stage_cost = sum(rec.stage_cost_ids.mapped('total_amount'))

    @api.depends('timesheet_ids')
    def _get_timesheet_count(self):
        for rec in self:
            rec.timesheet_count = len(rec.timesheet_ids) if rec.timesheet_ids else 0

    @api.depends('timesheet_ids')
    def _get_timesheet_duration(self):
        for rec in self:
            rec.timesheet_duration = sum(rec.timesheet_ids.mapped('unit_amount')) if rec.timesheet_ids else 0.0

    @api.onchange('allowed_stage_ids')
    def _onchange_allowed_stage_ids(self):
        """Automatically create or delete project.cost.stage lines based on selected stages"""
        if not self.id:
            return

        selected_stage_ids = set(self.allowed_stage_ids.ids)
        existing_stage_ids = set(self.stage_cost_ids.mapped('timesheet_status_id').ids)

        # Add new stage lines
        stages_to_add = selected_stage_ids - existing_stage_ids
        for stage_id in stages_to_add:
            self.env['project.cost.stage'].create({
                'project_id': self.id,
                'timesheet_status_id': stage_id,
                'amount': 0.0,
            })

        # Remove lines for unselected stages
        stages_to_remove = existing_stage_ids - selected_stage_ids
        lines_to_delete = self.stage_cost_ids.filtered(
            lambda line: line.timesheet_status_id.id in stages_to_remove
        )
        lines_to_delete.unlink()

    def write(self, vals):
        res = super().write(vals)
        if 'allowed_stage_ids' in vals:
            self._onchange_allowed_stage_ids()
        return res
