/** @odoo-module **/

import {ExpirationPanel} from "@web_enterprise/webclient/home_menu/expiration_panel";
import {patch} from 'web.utils';
import {useService} from "@web/core/utils/hooks";

patch(ExpirationPanel.prototype, 'admin_expiration_panel', {
    setup() {
        this._super.apply(this, arguments);
        this.user = useService("user");
    },

    async mounted() {
        if (!await this.user.hasGroup('base.group_erp_manager')) {
            this.state.display = false;
        }
        this._super.apply(this, arguments);
    }
})
