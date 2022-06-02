odoo.define('invoice_refund_restrictions.relational_fields', function (require) {
    "use strict";

    var relational_fields = require('web.relational_fields');

    return relational_fields.FieldX2Many.include({
        _hasCreateLine: function () {
            if (this.attrs.name === 'invoice_line_ids') {
                if (this.recordData.is_vendus_credit_note) {
                    this.canCreate = false;
                }
            }
            return this._super();
        },
    });
});


