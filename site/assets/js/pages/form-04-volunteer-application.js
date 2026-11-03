/* Sporting Pearls - form-04-volunteer-application.js (verbatim v15) */
var currentSec = 1;
var totalSecs = 4;
var nextBtn = document.getElementById('nextBtn');
var prevBtn = document.getElementById('prevBtn');
var submitBtn = document.getElementById('submitBtn');
var trackerSteps = document.querySelectorAll('.t-step');

// Pre-fill today's date
document.getElementById('v_date').valueAsDate = new Date();

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
  var vName = document.getElementById('v_name').value;
  var vPhone = document.getElementById('v_phone').value;
  var vAvail = document.getElementById('v_avail').value;
  var vArea = document.getElementById('v_area').value;

  document.getElementById('rev_vname').textContent = vName || 'Not specified';
  document.getElementById('rev_vphone').textContent = vPhone || 'Not specified';
  document.getElementById('rev_vavail').textContent = vAvail || 'Not specified';
  document.getElementById('rev_varea').textContent = vArea || 'Not specified';
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

document.getElementById('volunteerForm').addEventListener('submit', function(e) {
  e.preventDefault();
  if (!validateSection(currentSec)) return;
  var vName = document.getElementById('v_name').value.trim();
  document.getElementById('succ_vol_name').textContent = vName;
  if (window.SP_FORMS && SP_FORMS.finish) {
    /* Phase 3: success screen + reference only after the server acks */
    SP_FORMS.finish(this, { refEl: 'succ_volref', hide: ['volunteerForm', 'stepTracker'], modal: 'successModal' });
  } else {
    document.getElementById('succ_volref').textContent = 'DEMO';
    document.getElementById('volunteerForm').style.display = 'none';
    document.getElementById('stepTracker').style.display = 'none';
    document.getElementById('successModal').classList.add('active');
  }
});
