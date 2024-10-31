/** @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { TimeOffDialogFormController } from '@hr_holidays/views/view_dialog/form_view_dialog';
import {patch} from "@web/core/utils/patch";

patch(TimeOffDialogFormController.prototype, {
     /**
     * Override the setup method to initialize additional services.
     */
    setup() {
        super.setup();
        this.actionService = useService("action");
    },

    async onClick(action) {
        const args = (action === 'action_approve') ? [this.record.resId, false] : [this.record.resId];
        var response = await this.orm.call("hr.leave", action, args);
        this.props.onLeaveUpdated();

        // If the action is to refuse the leave, perform additional action to add refuse reason.
        if (action === 'action_refuse'){
            this.actionService.doAction(response);
        }
    }
});
