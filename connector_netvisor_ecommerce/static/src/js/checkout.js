odoo.define("connector_netvisor_ecommerce.checkout", function (require) {
  "use strict";
  const publicWidget = require("web.public.widget");

  publicWidget.registry.CheckoutSnailmail = publicWidget.Widget.extend({
    selector: ".oe_website_sale:has(input[name=company_name])",
    events: {
      "change input[name=company_name]": "_onChangeCompanyName",
    },
    start: function () {
      const result = this._super(...arguments);
      this.$company_name = this.$("input[name=company_name]");
      return result;
    },

    _onChangeCompanyName: function () {
      var is_company = this.$company_name.val().length !== 0;

      var speed = "slow";
      if (is_company) {
        $("#transmit_method_snailmail_div").fadeOut(speed);
      } else {
        $("#transmit_method_snailmail_div").fadeIn(speed);
      }
    },
  });
});
