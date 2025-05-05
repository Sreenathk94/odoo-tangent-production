/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, onMounted, useState } from '@odoo/owl';

export class PrivacyPolicyDashboard extends Component {
    setup() {
        this.state = useState({
            loading: true,
            error: null,
            data: null
        });

        this.rpc = useService('rpc');

        onMounted(() => {
            this.loadPrivacyPolicy();
        });
    }

    async loadPrivacyPolicy() {
        try {
            const data = await this.rpc('/vision_board/privacy_policy');
            if (data.error) {
                this.state.error = data.error;
            } else {
                // Format the last updated date
                if (data.last_updated) {
                    const date = new Date(data.last_updated);
                    data.last_updated = date.toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                }
                
                // Add PDF URL if available
                if (data.privacy_policy_pdf) {
                    data.pdf_url = `/web/content/res.company/${data.company_id}/privacy_policy_pdf/${data.privacy_policy_filename}`;
                }
                
                this.state.data = data;
            }
        } catch (error) {
            this.state.error = "Failed to load privacy policy.";
            console.error(error);
        } finally {
            this.state.loading = false;
        }
    }
}

PrivacyPolicyDashboard.template = 'vision_board.PrivacyPolicyDashboard';
PrivacyPolicyDashboard.props = {
    action: { type: Object, optional: true },
    actionId: { type: Number, optional: true },
    className: { type: String, optional: true },
};

registry.category('actions').add('vision_board.privacy_policy_dashboard', PrivacyPolicyDashboard);