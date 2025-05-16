================================================================
Restrict Auto Save
================================================================

The Restrict Auto Save module is a solution for controlling the save functionality of forms within Odoo. This module prevents auto-saving of form data, allowing users to save changes only manually. If a user attempts to navigate away or refresh the page without saving manually, a popup will appear as a reminder.

**Table of contents**
 
.. contents::
   :local:
 
**Key Features**
================================================================

- **Global Prevention of Auto-Save**: Disables auto-save functionality across all forms in Odoo.
- **Specific Model Selection**: Option to prevent auto-save for specific models. By enabling the "Prevent Auto Save Specific Model" checkbox, users can choose specific models where auto-save should be restricted.
- **Manual Save Requirement**: Users must manually save changes to persist form data.
- **Popup Warning on Navigation**: Displays a confirmation popup if the user tries to navigate away without saving changes.
- **No Save on Refresh or Reload**: Ensures that unsaved data is not saved if the page is refreshed or reloaded.
- **Re Enable Auto Save**: Re enables the automatic autosave feature.


**Summary**
================================================================

Restrict Auto Save Odoo App enhances the user experience by preventing automatic saving of changes in form views. Users must manually save their edits, and if they attempt to leave, navigate away, or refresh the page without saving, a popup will alert them to unsaved changes. This feature minimizes the risk of accidental data loss and ensures that important updates are consciously saved, maintaining data integrity.

**Installation**
================================================================

1. Download the module from the Odoo App Store or clone the repository.
2. Place the module in your Odoo addons directory.
3. Update your Odoo instance to include the new module.
4. Install the module through the Odoo interface.

**How to use this module:**
================================================================

1. Navigate to settings in your Odoo dashboard.
2. Click on prevent auto save menu item.
3. **Global Auto-Save Prevention**: Enable the global prevention of auto-save for all forms by toggling the Prevent Auto Save Globally setting.
4. **Specific Model Configuration**: If needed, enable the "Prevent Auto Save for Specific Models" checkbox. A new field will appear to select the specific models you want to apply the prevent auto-save functionality to.
5. **Popup Navigation Warning**: Attempt to navigate away without saving to experience the popup confirmation prompt.

Change logs
================================================================

[1.0.0]

* ``Added`` [25-10-2024]- Restrict Auto Save App

Support
================================================================
 
`Zehntech Technologies <https://www.zehntech.com/erp-crm/odoo-services/>`_

