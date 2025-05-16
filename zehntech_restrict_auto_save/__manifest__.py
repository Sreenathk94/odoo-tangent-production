{
    "name": " Restrict Auto Save",
    "description": """ This module enhances user experience by preventing the automatic saving of form views in Odoo. When a user attempts to navigate away from the form view or refresh the page without manually saving their changes, a popup will be displayed, prompting them to save their work before proceeding. This ensures data integrity by allowing users to consciously save their form data.""",
    "version": "17.0.1.0.0",
    "summary": "Restrict Auto Save Odoo App enhances the user experience by preventing automatic saving of changes in form views. Users must manually save their edits, and if they attempt to leave, navigate away, or refresh the page without saving, a popup will alert them to unsaved changes. This feature minimizes the risk of accidental data loss and ensures that important updates are consciously saved, maintaining data integrity.",
    "category": "Tools",
    "author": "Zehntech Technologies Inc.",
    "company": "Zehntech Technologies Inc.",
    "maintainer": "Zehntech Technologies Inc.",
    "contributor": "Zehntech Technologies Inc.",
    "website": "https://www.zehntech.com/",
    "support": "odoo-support@zehntech.com",
    "depends":['web','crm','hr','contacts','mail','sale'],
    "data": [
        "security/ir.model.access.csv",
        "data/prevent_model_demo.xml",
        "views/prevent_autosave_views.xml",
            ],
    "assets": {
        'web.assets_backend': [
                  "zehntech_restrict_auto_save/static/src/js/prevent_autosave_formcontroller.js",  
                   "zehntech_restrict_auto_save/static/src/css/custom.css",                 
    ],
},
    'i18n': [
            'i18n/es.po',#spanish translation file
            'i18n/fr.po',#french translation file
            'i18n/de.po',#german translation file
            'i18n/ja_JP.po',#japanese translation file
    ],
'images': ['static/description/banner.png'],
    "license": "OPL-1",  
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": 00.00,
    "currency": "USD",
     
}
