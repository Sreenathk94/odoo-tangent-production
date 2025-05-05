from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    privacy_policy_pdf = fields.Binary(string='Privacy Policy PDF', attachment=True)
    privacy_policy_filename = fields.Char(string='Privacy Policy Filename')
    privacy_policy_last_updated = fields.Datetime(string='Last Updated', default=fields.Datetime.now)
    privacy_policy_content = fields.Html(string='Privacy Policy Content', sanitize=True, default="""
        <div class="text-center">
            <h3>Privacy Policy</h3>
            <p>Please upload a PDF file or enter the privacy policy content here.</p>
        </div>
    """)
