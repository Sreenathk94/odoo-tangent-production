from odoo import api, fields, models

class Project(models.Model):

    _inherit = 'project.project'

    project_number = fields.Char(string='Project Number')

