# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProjectCostStage(models.Model):
    _name = "project.cost.stage"
    _description = "Project Cost Stage"

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        ondelete='cascade'
    )

    # Just to restrict domain
    allowed_stage_ids = fields.Many2many(
        related='project_id.allowed_stage_ids',
        string='Stages',
        readonly=True
    )

    timesheet_status_id = fields.Many2one(
        "hr.timesheet.status",
        string='Stage',
        required=True
    )

    # Base stage fee
    amount = fields.Float('Stage Base Fee')

    # Total = base + all variations
    total_amount = fields.Float(
        string="Total Stage Fee",
        compute="_compute_total_amount",
        store=True
    )

    @api.depends(
        'amount',
        'project_id.variation_ids.amount',
        'project_id.variation_ids.timesheet_status_id'
    )
    def _compute_total_amount(self):
        for rec in self:
            variations = rec.project_id.variation_ids.filtered(
                lambda v: v.timesheet_status_id.id == rec.timesheet_status_id.id
            )
            rec.total_amount = rec.amount + sum(variations.mapped('amount'))


