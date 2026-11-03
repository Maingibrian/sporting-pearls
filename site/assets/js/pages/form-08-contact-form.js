/* Sporting Pearls - form-08-contact-form.js */
document.getElementById('contactForm').addEventListener('submit',function(e){
  e.preventDefault();
  var sec=document.querySelector('.form-section[data-sec="1"]');
  var inputs=sec.querySelectorAll('input[required], select[required], textarea[required]');var valid=true;
  inputs.forEach(function(i){if(!i.value.trim()){valid=false;i.style.borderColor='var(--danger)'}else{i.style.borderColor='var(--hair)'}});
  if(!valid){alert('Please fill in all mandatory fields before sending.');return;}
  document.getElementById('succ_name').textContent=document.getElementById('e_name').value.trim();
  document.getElementById('succ_topic').textContent=document.getElementById('e_topic').value;
  document.getElementById('succ_ref').textContent='DEMO';
  if(window.SP_FORMS&&SP_FORMS.finish){
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this,{refEl:'succ_ref',hide:['contactForm'],modal:'successModal'});
  }else{
    document.getElementById('contactForm').style.display='none';
    document.getElementById('successModal').classList.add('active');
  }
});
