from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    project_number = fields.Char(string='Project Number')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', order=None, limit=100, name_get_uid=None):
        args = args or []
        if name:
            args = ['|', ('name', operator, name), ('project_number', operator, name)] + args
        return self._search(args, limit=limit, order=order, access_rights_uid=name_get_uid)
