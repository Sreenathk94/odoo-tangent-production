# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProjectCostStageVariation(models.Model):
    _name = "project.cost.stage.variation"
    _description = "Variation Fee for Stages"

    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
    )
    allowed_stage_ids = fields.Many2many(
        related='project_id.allowed_stage_ids',
        string='Stages',
        readonly=True
    )
    timesheet_status_id = fields.Many2one(
        "hr.timesheet.status",
        string="Stage",
        required=True,

    )

    description = fields.Char("Description")
    amount = fields.Float("Variation Fee")
