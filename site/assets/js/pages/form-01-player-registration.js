/* Sporting Pearls - form-01-player-registration.js (verbatim v15) */
var currentSec = 1;
var totalSecs = 6;
var nextBtn = document.getElementById('nextBtn');
var prevBtn = document.getElementById('prevBtn');
var submitBtn = document.getElementById('submitBtn');
var trackerSteps = document.querySelectorAll('.t-step');

// Pre-fill today's date on declaration
document.getElementById('sig_date').valueAsDate = new Date();

function updateStep(step) {
  if (step < 1 || step > totalSecs) return;
  
  // Update section views
  document.querySelectorAll('.form-section').forEach(function(sec) {
    sec.classList.remove('active');
  });
  document.querySelector('.form-section[data-sec="' + step + '"]').classList.add('active');

  // Update Tracker UI
  trackerSteps.forEach(function(t, idx) {
    t.classList.remove('active');
    if (idx + 1 < step) t.classList.add('completed');
    else t.classList.remove('completed');
    if (idx + 1 === step) t.classList.add('active');
  });

  // Manage Nav Button visibility
  prevBtn.style.visibility = (step === 1) ? 'hidden' : 'visible';
  
  if (step === totalSecs) {
    nextBtn.style.display = 'none';
    submitBtn.style.display = 'inline-flex';
    populateReview();
  } else {
    nextBtn.style.display = 'inline-flex';
    submitBtn.style.display = 'none';
    var nextChar = String.fromCharCode(65 + step);
    nextBtn.innerHTML = 'Continue to Section ' + nextChar + ' →';
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
    alert('Please fill in all mandatory fields (marked with a red asterisk) before proceeding.');
  }
  return valid;
}

function populateReview() {
  var pFirst = document.getElementById('p_first').value;
  var pLast = document.getElementById('p_last').value;
  var pDob = document.getElementById('p_dob').value;
  var pGender = document.getElementById('p_gender').value;
  var pSquad = document.getElementById('fb_squad').value;
  var gName = document.getElementById('g1_name').value;
  var gPhone = document.getElementById('g1_phone').value;

  document.getElementById('rev_name').textContent = (pFirst + ' ' + pLast).trim() || 'Not specified';
  document.getElementById('rev_dob').textContent = (pDob + ' (' + pGender + ')') || 'Not specified';
  document.getElementById('rev_squad').textContent = pSquad || 'Not specified';
  document.getElementById('rev_gname').textContent = gName || 'Not specified';
  document.getElementById('rev_gphone').textContent = gPhone || 'Not specified';
}

nextBtn.addEventListener('click', function() {
  if (validateSection(currentSec)) {
    updateStep(currentSec + 1);
  }
});

prevBtn.addEventListener('click', function() {
  updateStep(currentSec - 1);
});

// Step tracker jump
trackerSteps.forEach(function(t) {
  t.addEventListener('click', function() {
    var target = parseInt(this.getAttribute('data-step'), 10);
    if (target < currentSec || validateSection(currentSec)) {
      updateStep(target);
    }
  });
});

// Form Submission
document.getElementById('playerRegForm').addEventListener('submit', function(e) {
  e.preventDefault();
  if (!validateSection(currentSec)) return;
  var pName = (document.getElementById('p_first').value + ' ' + document.getElementById('p_last').value).trim();
  document.getElementById('succ_player_name').textContent = pName;
  if (window.SP_FORMS && SP_FORMS.finish) {
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this, { refEl: 'succ_ref', hide: ['playerRegForm', 'stepTracker'], modal: 'successModal' });
  } else {
    document.getElementById('succ_ref').textContent = 'DEMO';
    document.getElementById('playerRegForm').style.display = 'none';
    document.getElementById('stepTracker').style.display = 'none';
    document.getElementById('successModal').classList.add('active');
  }
});
