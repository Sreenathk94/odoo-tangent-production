from odoo import api, fields, models
from odoo.exceptions import ValidationError
class PreventModelLine(models.Model):
    _name = "prevent.model.line"
    _description = "Prevent Model Line"

    model_id = fields.Many2one('ir.model', "Model Name", required=True, ondelete='cascade',help="Select the model for which you want to configure settings.")
    model_description = fields.Char(related="model_id.name", string="Description",help="This is the description of the selected model.")
    model = fields.Char(related="model_id.model", string="Model ID",help="This is the technical identifier for the selected model.")
    prevent_id = fields.Many2one('prevent.model', "Prevent Model Id",help="This field links to a specific 'prevent.model' record, indicating the configuration that applies to the selected model.")

    
    @api.constrains('model_id')
    def _check_model_id(self):
        for record in self:
            if not record.model_id:
                raise ValidationError("Please select a Model ID before saving.")
