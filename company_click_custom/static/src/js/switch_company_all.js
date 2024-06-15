/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";


patch(SwitchCompanyMenu.prototype, {
    on_select_all(){
        var companies = Object.values(this.companyService.allowedCompaniesWithAncestors).filter((c) => !c.parent_id)
        for (const line of companies) {
            this.companySelector._selectCompany(line.id);
        }
        this.companyService.setCompanies(this.companySelector.selectedCompaniesIds, false);
    },

    de_select_all(){
        var companies = Object.values(this.companyService.allowedCompaniesWithAncestors).filter((c) => !c.parent_id)
        for (const line of companies) {
            this.companySelector._deselectCompany(line.id);
        }
        this.companySelector._debouncedApply();
    }
});
