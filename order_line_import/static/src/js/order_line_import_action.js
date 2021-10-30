/**
 * 
 */
odoo.define('order_line_import.import_action',function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.BasicModel');
var Context = require('web.Context');
var session = require('web.session');
var pyeval=require("web.pyeval");
var QWeb = core.qweb;
var DataImport=require('base_import.import');
var Dialog=require('web.Dialog');

DataImport.DataImport.include({

 init:function (parent, action) {
        this._super.apply(this, arguments);
        this._target=action.target;
        this._dialog_height=action.params.height || '860px';
        this.show_required=action.params.show_required || false;
        this.import_field=action.params.import_field || false;
        if (this.need_import()){
        	var self=this;
        	var dialog=self.action_manager.dialog;
        	this.action_manager.dialog.opened().then(function(){        		
        		dialog.$el.css("height",self._dialog_height);
        		dialog.$footer.append(self.$buttons);
        	
        	});
        }
        
	 },
	  need_import:function(){
	 	return this._target=='new' && this.import_field;
	 },
	 exit:function(){
	 	if(!this.need_import()){
	 		return this._super.apply(this,arguments);
	 	}
	 	this.action_manager.dialog.close();	 		 	
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
	 	return this.action_manager.inner_widget.active_view.controller;
	 },
	  onimport: function () {
        var self = this;
        return this._super.apply(this,arguments).done(function(messages){
        	if(messages && messages.length>0 && self.need_import()){
        		var view=self.action_manager.inner_widget.active_view;
        		if(view.type!='form' || messages.length<=0){
        			return;
        		}
        		var controller=self.getController();        		
        		controller.update({fieldNames:[self.import_field]},{reload:true});
        		
        	}
        });
    },
    start:function(){
     var self=this;
     return this._super.apply(this,arguments).then(function(){
     	if(!self.need_import() || !self.show_required){
     		return;
     	}
     	var controller=self.getController();
     	var handle=controller.handle;
     	var model=controller.model;
     	var order=model.get(handle);
     	var line_data=order.data[self.import_field];
     	var fieldString="";
     	for(var fieldName in line_data.fields){
     		var field=line_data.fields[fieldName];
     		if(field.required){
     			fieldString+=field.string+",";
     		}
     	}
     	if(fieldString){
     		var infoObj=$('<div>').addClass('alert alert-warning')
     		                      .attr('role','alert')
     		                      .html('字段：'+fieldString+" 为必填");
     		self.$el.find('.oe_import_box').prepend(infoObj);
     	}
     });
    }
	
});
/**
DataImport.DataImport.include({
	 init: function (parent, action) {
        this._super.apply(this, arguments);
        this._target=action.target;
        if (this.need_import()){
        	var self=this;
        	this.action_manager.dialog.opened(function(){
        		self.action_manager.dialog.$el.find('.modal-body').css('height','860px');
        	});
        }
        
	 },
	 need_import:function(){
	 	return this._target=='new' && _.contains(this.res_model,['sale.order.line','purchase.order.line']);
	 },
	 renderButtons: function() {
	 	this._super.apply(this, arguments);
	 	
	 }
});
**/
});
