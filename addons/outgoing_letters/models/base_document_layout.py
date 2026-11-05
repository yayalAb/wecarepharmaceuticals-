from odoo import api, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'outgoing.letter' and active_id:
            letter = self.env['outgoing.letter'].browse(active_id)
            if letter.exists():
                if 'report_layout_id' in fields_list and letter.report_layout_id:
                    res['report_layout_id'] = letter.report_layout_id.id
                if 'layout_background' in fields_list and letter.layout_background:
                    res['layout_background'] = letter.layout_background
                if 'layout_background_image' in fields_list and letter.layout_background_image:
                    res['layout_background_image'] = letter.layout_background_image
                if 'primary_color' in fields_list and letter.primary_color:
                    res['primary_color'] = letter.primary_color
                if 'secondary_color' in fields_list and letter.secondary_color:
                    res['secondary_color'] = letter.secondary_color
                if 'logo' in fields_list and letter.logo:
                    res['logo'] = letter.logo
                if 'report_header' in fields_list and letter.letter_header:
                    res['report_header'] = letter.letter_header
                if 'report_footer' in fields_list and letter.letter_footer:
                    res['report_footer'] = letter.letter_footer
        return res

    def document_layout_save(self):
        res = super().document_layout_save()
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'outgoing.letter' and active_id:
            letter = self.env['outgoing.letter'].browse(active_id)
            if letter.exists():
                vals = {}
                if self.report_layout_id:
                    vals['report_layout_id'] = self.report_layout_id.id
                if self.layout_background:
                    vals['layout_background'] = self.layout_background
                if self.layout_background_image:
                    vals['layout_background_image'] = self.layout_background_image
                if self.primary_color:
                    vals['primary_color'] = self.primary_color
                if self.secondary_color:
                    vals['secondary_color'] = self.secondary_color
                if self.logo:
                    vals['logo'] = self.logo
                if self.report_header:
                    vals['letter_header'] = self.report_header
                if self.report_footer:
                    vals['letter_footer'] = self.report_footer
                if vals:
                    letter.write(vals)
        return res
