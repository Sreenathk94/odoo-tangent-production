/** @odoo-module */
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useSetupView } from "@web/views/view_hook";
import { Dialog } from "@web/core/dialog/dialog";  
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog"; 
import { _t } from "@web/core/l10n/translation";

let models;
let auto_save_boolean_all;
let auto_save_boolean;
let manualSaveFlag = false; 
console.log("initially", manualSaveFlag);
const savee = FormController.prototype.save;


patch(FormController.prototype, {
    /* Patch FormController to restrict auto save in form views */
    setup() {
        super.setup(...arguments);
        this.uiService = useService("ui");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.actionService = useService("action");

        const getFormData = async () => {
            models = await this.orm.searchRead('prevent.model.line', [], ['model']);
            auto_save_boolean_all = await this.orm.searchRead('prevent.model', [], ['auto_save_prevent_all']);
            auto_save_boolean = await this.orm.searchRead('prevent.model', [], ['auto_save_prevent']);
        };
        getFormData();

        this.beforeLeaveHook = false;
        useSetupView({
            beforeLeave: () => this.beforeLeave(models, auto_save_boolean_all, auto_save_boolean),
            beforeUnload: (ev) => this.beforeUnload(ev),
        });
    },
    async beforeLeave() {
        /* Function will work before leaving the form */
        const isDirty = await this.model.root.isDirty();
        if (isDirty && this.beforeLeaveHook === false) {
            const model_lst = models.map(dict => dict.model);
            const boolean_all_lst = auto_save_boolean_all.map(dict => dict.auto_save_prevent_all);
            const boolean_lst = auto_save_boolean.map(dict => dict.auto_save_prevent);

            if (
                boolean_all_lst.includes(true) ||
                (model_lst.includes(this.model.root.resModel) && boolean_lst.includes(true))
            ) {

                if (manualSaveFlag) {
                    manualSaveFlag = false;
                    this.beforeLeaveHook = true;
                    return true; // Allow user to navigate without any confirmation
                } else {
                
                    // Create a custom dialog instead of the default confirm popup
                    return new Promise((resolve) => {
                        this.beforeLeaveHook = true;
                        this.dialogService.add(ConfirmationDialog, {
                            title: _t("Save Changes"),
                            body: _t("You have unsaved changes do you want to continue? Your changes will be lost"),
                            confirmClass: "autosave-ok",
                            confirm: () => {
                                this.model.root.discard();
                                resolve(true)

                            },

                        });
                        setTimeout(() => {
                           
                             // Locate and style the specific text
                             const modalBody = document.querySelector('.o_dialog .modal-body');
                             if (modalBody) {
                                 const updatedText = modalBody.innerHTML.replace(
                                     "Your changes will be lost",
                                     `<span style="color: red; font-weight: bold;">Your changes will be lost.</span>`
                                 );
                                 modalBody.innerHTML = updatedText;
                                 console.log("Styled the 'Your changes will be lost' text.");
                             } else {
                                 console.error("Modal body not found.");
                             }
                        }, 10); // Small delay to ensure the DOM is rendered
                        
                    });
                }

            } else {
                await this.model.root.save();
        
            }
            this.beforeLeaveHook = true;
        }
    },
    async save(){
        manualSaveFlag = true;
        console.log(manualSaveFlag);
        super.save(...arguments);
    },
    beforeUnload(ev) {
        var root = this.model.root
        var model_lst = models.map(dict => dict.model)
        var boolean_all_lst = auto_save_boolean_all.map(dict => dict.auto_save_prevent_all)
        var boolean_lst = auto_save_boolean.map(dict => dict.auto_save_prevent)
        if (boolean_all_lst.includes(true)) {
            root.discard();
            return true;
        } else {
            if (model_lst.includes(root.resModel) && boolean_lst.includes(true)) {
                root.discard();
                return true;
            } else {
                root.urgentSave();
                return true;
            }
        }
    },

});
