/* Sporting Pearls - form-02-trial-application.js (verbatim v15) */
var currentSec = 1;
var totalSecs = 4;
var nextBtn = document.getElementById('nextBtn');
var prevBtn = document.getElementById('prevBtn');
var submitBtn = document.getElementById('submitBtn');
var trackerSteps = document.querySelectorAll('.t-step');

// Pre-fill today's date
document.getElementById('t_date').valueAsDate = new Date();

// DOB to Age calculator
document.getElementById('t_dob').addEventListener('change', function() {
  if (this.value) {
    var dob = new Date(this.value);
    var diff = Date.now() - dob.getTime();
    var ageDate = new Date(diff);
    var age = Math.abs(ageDate.getUTCFullYear() - 1970);
    document.getElementById('t_age').value = age + ' Years Old';
  }
});

function updateStep(step) {
  if (step < 1 || step > totalSecs) return;
  
  document.querySelectorAll('.form-section').forEach(function(sec) {
    sec.classList.remove('active');
  });
  document.querySelector('.form-section[data-sec="' + step + '"]').classList.add('active');

  trackerSteps.forEach(function(t, idx) {
    t.classList.remove('active');
    if (idx + 1 < step) t.classList.add('completed');
    else t.classList.remove('completed');
    if (idx + 1 === step) t.classList.add('active');
  });

  prevBtn.style.visibility = (step === 1) ? 'hidden' : 'visible';
  
  if (step === totalSecs) {
    nextBtn.style.display = 'none';
    submitBtn.style.display = 'inline-flex';
    populateReview();
  } else {
    nextBtn.style.display = 'inline-flex';
    submitBtn.style.display = 'none';
    nextBtn.innerHTML = 'Continue to Step ' + (step + 1) + ' →';
  }

  currentSec = step;
  window.scrollTo({ top: document.querySelector('.tracker-wrap').offsetTop - 20, behavior: 'smooth' });
}

function validateSection(secNum) {
  var activeSecEl = document.querySelector('.form-section[data-sec="' + secNum + '"]');
  var inputs = activeSecEl.querySelectorAll('input[required], select[required], textarea[required]');
  var valid = true;

  inputs.forEach(function(input) {
    if (input.type === 'checkbox') {
      if (!input.checked) {
        valid = false;
        input.closest('label').style.borderColor = 'var(--danger)';
      } else {
        input.closest('label').style.borderColor = 'var(--hair)';
      }
    } else {
      if (!input.value.trim()) {
        valid = false;
        input.style.borderColor = 'var(--danger)';
      } else {
        input.style.borderColor = 'var(--hair)';
      }
    }
  });

  if (!valid) {
    alert('Please fill in all mandatory fields before proceeding.');
  }
  return valid;
}

function populateReview() {
  var tFirst = document.getElementById('t_first').value;
  var tLast = document.getElementById('t_last').value;
  var tSquad = document.getElementById('t_squad').value;
  var tPos = document.getElementById('t_pos').value;
  var tSess = document.getElementById('ts_day').value;
  var tgPhone = document.getElementById('tg_phone').value;

  document.getElementById('rev_tname').textContent = (tFirst + ' ' + tLast).trim() || 'Not specified';
  document.getElementById('rev_tsquad').textContent = tSquad || 'Not specified';
  document.getElementById('rev_tpos').textContent = tPos || 'Not specified';
  document.getElementById('rev_tsess').textContent = tSess || 'Not specified';
  document.getElementById('rev_tgphone').textContent = tgPhone || 'Not specified';
}

nextBtn.addEventListener('click', function() {
  if (validateSection(currentSec)) {
    updateStep(currentSec + 1);
  }
});

prevBtn.addEventListener('click', function() {
  updateStep(currentSec - 1);
});

trackerSteps.forEach(function(t) {
  t.addEventListener('click', function() {
    var target = parseInt(this.getAttribute('data-step'), 10);
    if (target < currentSec || validateSection(currentSec)) {
      updateStep(target);
    }
  });
});

document.getElementById('trialForm').addEventListener('submit', function(e) {
  e.preventDefault();
  if (!validateSection(currentSec)) return;
  var tName = (document.getElementById('t_first').value + ' ' + document.getElementById('t_last').value).trim();
  document.getElementById('succ_trial_name').textContent = tName;
  document.getElementById('succ_tslot').textContent = document.getElementById('ts_day').value;
  if (window.SP_FORMS && SP_FORMS.finish) {
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this, { refEl: 'succ_tref', hide: ['trialForm', 'stepTracker'], modal: 'successModal' });
  } else {
    document.getElementById('succ_tref').textContent = 'DEMO';
    document.getElementById('trialForm').style.display = 'none';
    document.getElementById('stepTracker').style.display = 'none';
    document.getElementById('successModal').classList.add('active');
  }
});
