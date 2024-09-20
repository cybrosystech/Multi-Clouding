/** @odoo-module **/
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { patch } from "@web/core/utils/patch";
import { jsonrpc } from "@web/core/network/rpc_service";
import IZIViewDashboard from "@izi_dashboard/js/component/main/izi_view_dashboard";
const { onMounted } = owl;

patch(HomeMenu.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            self = this;
            self.$el = $('#ask_ai_container');
            var $viewDashboard = new IZIViewDashboard(self);
            $viewDashboard.appendTo(self.$el);
            self.$viewDashboard = $viewDashboard;
            self.getDefaultDashboard()
            self.setDragFunction()
        });
    },
    setDragFunction(){
        const aiMenu = document.getElementById("izi_home_menu");
        if(aiMenu){
            let shiftX, shiftY;
            function moveAt(pageX, pageY) {
                aiMenu.style.left = pageX + 'px';
                aiMenu.style.top = pageY + 'px';
            }
            function onMouseOrTouchMove(event) {
                let pageX = event.pageX || event.touches[0].pageX;
                let pageY = event.pageY || event.touches[0].pageY;
                moveAt(pageX - shiftX, pageY - shiftY);
            }
            aiMenu.onmousedown = aiMenu.ontouchstart = function(event) {
                shiftX = (event.clientX || event.touches[0].clientX) - aiMenu.getBoundingClientRect().left;
                shiftY = (event.clientY || event.touches[0].clientY) - aiMenu.getBoundingClientRect().top;
        
                document.addEventListener('mousemove', onMouseOrTouchMove);
                document.addEventListener('touchmove', onMouseOrTouchMove);
        
                aiMenu.onmouseup = aiMenu.ontouchend = function() {
                    document.removeEventListener('mousemove', onMouseOrTouchMove);
                    document.removeEventListener('touchmove', onMouseOrTouchMove);
                    aiMenu.onmouseup = aiMenu.ontouchend = null;
                };
            };
        
            aiMenu.ondragstart = function() {
                return false;
            };
        }

    },
    getDefaultDashboard() {
        jsonrpc('/web/dataset/call_kw/izi.dashboard/get_default_dashboard', {
            model: 'izi.dashboard',
            method: 'get_default_dashboard',
            args: [[]],
            kwargs: {},
        }).then(function (result) {
            self.$viewDashboard._setDashboard(result)
        });
    },
    onClickOpenAI(ev){
        var self = this;
        self.$viewDashboard._renderAIMessages();
        $(".izi_view_dashboard_ask_container").removeAttr('style');
        $(".izi_view_dashboard_ask_result").css('display','none');
        $(".izi_view_dashboard_ask_discuss").css('width','100%');
        if (self.$el.hasClass('active')) {
            self.$el.removeClass('active');
            setTimeout(() => self.$el.css('display', 'none'), 300); // Delay hiding until animation ends
        } else {
            self.$el.css('display', 'block'); // Show before fading in
            setTimeout(() => self.$el.addClass('active'), 10); // Trigger the fade-in animation
        }
    },
    
});
