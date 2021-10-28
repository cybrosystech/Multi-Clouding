/**
 * 
 */
odoo.define('order_line_import.import_action',function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.BasicModel');
var DataImport=require('base_import.import');
var Dialog=require('web.Dialog');

DataImport.DataImport.include({

 init:function (parent, action) {
        this._super.apply(this, arguments);
        this._target=action.target;
        this._dialog_height=action.params.height || '860px';
        this.show_required=action.params.show_required || false;
        this.import_field=action.params.import_field || false;
        this.action_id=action.jsID;
        if (this.need_import()){
        	this.parentController=this.action_manager.getCurrentController();
        }
        
	 },
	  need_import:function(){
	 	return this._target=='new' && this.import_field;
	 },
	 exit:function(){
	 	if(!this.need_import()){
	 		return this._super.apply(this,arguments);
	 	}
	 	if(this.action_manager.currentDialogController){
	 		//如果本action在对话框中则关闭对话框
	 		this.action_manager.currentDialogController.dialog.close();
	 	}
	 		 		 	
	 },
	 import_options: function () {
	 	var options=this._super.apply(this,arguments);
	 	var is_import=this.need_import();
	 	if(options && is_import){
	 		var controller=this.getController();
	 		var model=controller.model;
	 		var order=model.get(controller.handle);	 	
	 		_.extend(options,{import_order_line:is_import,
	 			import_field:order.fields[this.import_field].relation_field,
	 			order_id:order.data['name'],
	 		});
	 	}
	 	return options;
	 },
	 getController:function(){
	 	//获取form controller
	 	return this.action_manager.getCurrentController().widget;
	 },
	 
    renderButtons: function(footer) {
    	 this._super.apply(this,arguments);
    	if(footer && this.need_import()){
    		var controller=this.action_manager.currentDialogController;
    		if(controller && controller.dialog){
    			//设置对话框高度
    			controller.dialog.$el.css("height",this._dialog_height);
    			footer.append(this.$buttons);
    		}
    		
    	}
    	
    },

	
});

});
