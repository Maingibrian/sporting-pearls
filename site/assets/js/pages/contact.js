/* Sporting Pearls - contact.js (verbatim v15) */
(function(){
"use strict";
var form=document.getElementById('generalEnquiry');
if(!form)return;
form.addEventListener('submit',function(e){
e.preventDefault();
var ok=true;
[['eq_name',function(v){return v.trim().length>=2}],['eq_email',function(v){return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)}],['eq_msg',function(v){return v.trim().length>=5}]].forEach(function(pair){
var el=document.getElementById(pair[0]);
var valid=pair[1](el.value||'');
el.style.borderColor=valid?'':'rgba(245,157,30,.9)';
if(!valid)ok=false;
});
if(!ok)return;
if(window.SP_FORMS&&SP_FORMS.finish){
/* Phase 3: the confirmation appears only after the server acks;
   offline/rejected states keep the form + explain honestly. */
SP_FORMS.finish(form,{reveal:'enquirySuccess',hide:['generalEnquiry'],onSettled:function(){}});
}else{
form.hidden=true;
var s=document.getElementById('enquirySuccess');
s.hidden=false;s.scrollIntoView({behavior:'smooth',block:'center'});
}
});
})();
