/* Sporting Pearls - form-07-donation-support.js */
var currentSec=1,totalSecs=4;
var nextBtn=document.getElementById('nextBtn'),prevBtn=document.getElementById('prevBtn'),submitBtn=document.getElementById('submitBtn');
var trackerSteps=document.querySelectorAll('.t-step');
document.getElementById('d_date').valueAsDate=new Date();
var amt='';
document.getElementById('amountChips').addEventListener('click',function(e){
  var b=e.target.closest('.chip');if(!b)return;
  document.querySelectorAll('#amountChips .chip').forEach(function(c){c.classList.remove('on')});
  b.classList.add('on');amt=b.getAttribute('data-amt');
  var other=document.getElementById('d_amount');
  if(amt==='other'){other.style.display='block';other.focus();amt='';}else{other.style.display='none';other.value=amt; /* keep the chosen amount in the field so the backend sync serializes it */}
});
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
  if(n===3&&!amt){var v=document.getElementById('d_amount');if(v.value.trim()){amt=v.value.trim()}else{valid=false;alert('Please choose or enter a contribution amount.');}}
  if(!valid&&n!==3){alert('Please fill in all mandatory fields before proceeding.');}
  return valid;
}
function populateReview(){
  document.getElementById('rev_dname').textContent=document.getElementById('d_name').value||'Not specified';
  document.getElementById('rev_dphone').textContent=document.getElementById('d_phone').value||'Not specified';
  var a=document.getElementById('d_amount').value||amt;
  document.getElementById('rev_damt').textContent=a?('KES '+Number(a).toLocaleString()):'Not specified';
  document.getElementById('rev_dfreq').textContent=document.getElementById('d_freq').value||'Not specified';
}
nextBtn.addEventListener('click',function(){if(validateSection(currentSec))updateStep(currentSec+1)});
prevBtn.addEventListener('click',function(){updateStep(currentSec-1)});
trackerSteps.forEach(function(t){t.addEventListener('click',function(){var g=parseInt(this.getAttribute('data-step'),10);if(g<currentSec||validateSection(currentSec))updateStep(g)})});
document.getElementById('donationForm').addEventListener('submit',function(e){
  e.preventDefault();
  if(!validateSection(currentSec))return;
  var a=document.getElementById('d_amount').value||amt;
  document.getElementById('succ_donor_name').textContent=document.getElementById('d_name').value.trim();
  document.getElementById('succ_amt').textContent='KES '+Number(a).toLocaleString();
  document.getElementById('succ_phone').textContent=document.getElementById('d_phone').value.trim();
  document.getElementById('succ_freq').textContent=document.getElementById('d_freq').value;
  if(window.SP_FORMS&&SP_FORMS.finish){
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this,{refEl:'succ_ref',hide:['donationForm','stepTracker'],modal:'successModal'});
  }else{
    document.getElementById('succ_ref').textContent='DEMO';
    document.getElementById('donationForm').style.display='none';
    document.getElementById('stepTracker').style.display='none';
    document.getElementById('successModal').classList.add('active');
  }
});
