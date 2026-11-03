/* Sporting Pearls - form-09-media-photo-consent.js */
var currentSec=1,totalSecs=3;
var nextBtn=document.getElementById('nextBtn'),prevBtn=document.getElementById('prevBtn'),submitBtn=document.getElementById('submitBtn');
var trackerSteps=document.querySelectorAll('.t-step');
document.getElementById('m_date').valueAsDate=new Date();
function consentList(){
  var out=[];
  if(document.getElementById('c_website').checked)out.push('Website');
  if(document.getElementById('c_social').checked)out.push('Social Media');
  if(document.getElementById('c_print').checked)out.push('Print & Press');
  if(document.getElementById('c_promo').checked)out.push('Promo Materials');
  return out.length?out.join(', '):'None selected';
}
function updateStep(step){
  if(step<1||step>totalSecs)return;
  document.querySelectorAll('.form-section').forEach(function(s){s.classList.remove('active')});
  document.querySelector('.form-section[data-sec="'+step+'"]').classList.add('active');
  trackerSteps.forEach(function(t,idx){t.classList.remove('active');if(idx+1<step)t.classList.add('completed');else t.classList.remove('completed');if(idx+1===step)t.classList.add('active')});
  prevBtn.style.visibility=(step===1)?'hidden':'visible';
  if(step===totalSecs){nextBtn.style.display='none';submitBtn.style.display='inline-flex';populateReview();}
  else{nextBtn.style.display='inline-flex';submitBtn.style.display='none';nextBtn.innerHTML='Continue to Step '+(step+1)+' &rarr;';}
  currentSec=step;window.scrollTo({top:document.querySelector('.tracker-wrap').offsetTop-20,behavior:'smooth'});
}
function validateSection(n){
  var sec=document.querySelector('.form-section[data-sec="'+n+'"]');
  var inputs=sec.querySelectorAll('input[required], select[required], textarea[required]');var valid=true;
  inputs.forEach(function(i){
    if(i.type==='checkbox'){if(!i.checked){valid=false;i.closest('label').style.borderColor='var(--danger)'}else{i.closest('label').style.borderColor='var(--hair)'}}
    else{if(!i.value.trim()){valid=false;i.style.borderColor='var(--danger)'}else{i.style.borderColor='var(--hair)'}}
  });
  if(!valid){alert('Please complete the required fields before proceeding.');}
  return valid;
}
function populateReview(){
  document.getElementById('rev_player').textContent=document.getElementById('m_player').value||'Not specified';
  document.getElementById('rev_squad').textContent=document.getElementById('m_squad').value||'Not specified';
  document.getElementById('rev_gname').textContent=document.getElementById('m_gname').value||'Not specified';
  document.getElementById('rev_consents').textContent=consentList();
}
nextBtn.addEventListener('click',function(){if(validateSection(currentSec))updateStep(currentSec+1)});
prevBtn.addEventListener('click',function(){updateStep(currentSec-1)});
trackerSteps.forEach(function(t){t.addEventListener('click',function(){var g=parseInt(this.getAttribute('data-step'),10);if(g<currentSec||validateSection(currentSec))updateStep(g)})});
document.getElementById('consentForm').addEventListener('submit',function(e){
  e.preventDefault();
  if(!validateSection(currentSec))return;
  document.getElementById('succ_gname').textContent=document.getElementById('m_gname').value.trim();
  document.getElementById('succ_player').textContent=document.getElementById('m_player').value.trim();
  document.getElementById('succ_consents').textContent=consentList();
  if(window.SP_FORMS&&SP_FORMS.finish){
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this,{refEl:'succ_ref',hide:['consentForm','stepTracker'],modal:'successModal'});
  }else{
    document.getElementById('succ_ref').textContent='DEMO';
    document.getElementById('consentForm').style.display='none';
    document.getElementById('stepTracker').style.display='none';
    document.getElementById('successModal').classList.add('active');
  }
});
