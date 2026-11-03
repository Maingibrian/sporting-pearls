/* Sporting Pearls - form-10-safeguarding-report.js (verbatim v15) */
var currentSec = 1;
var totalSecs = 4;
var nextBtn = document.getElementById('nextBtn');
var prevBtn = document.getElementById('prevBtn');
var submitBtn = document.getElementById('submitBtn');
var trackerSteps = document.querySelectorAll('.t-step');

// Pre-fill today's date
document.getElementById('sr_date').valueAsDate = new Date();

// Handle Anonymous Selection
document.getElementById('sr_pref').addEventListener('change', function() {
  var isAnon = this.value === 'Completely Anonymous';
  var repFields = document.getElementById('reporter_fields');
  var reqs = [document.getElementById('sr_name'), document.getElementById('sr_role')];
  
  if (isAnon) {
    repFields.style.opacity = '0.4';
    reqs.forEach(function(r) { r.removeAttribute('required'); });
    document.getElementById('rep_req').style.display = 'none';
    document.getElementById('role_req').style.display = 'none';
  } else {
    repFields.style.opacity = '1';
    reqs.forEach(function(r) { r.setAttribute('required', 'required'); });
    document.getElementById('rep_req').style.display = 'inline';
    document.getElementById('role_req').style.display = 'inline';
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

  // Specific checkbox category validation for Step 2
  if (secNum === 2) {
    var checkedCats = activeSecEl.querySelectorAll('input[name="sr_type"]:checked');
    if (checkedCats.length === 0) {
      alert('Please check at least one Category of Concern in Step 2.');
      return false;
    }
  }

  inputs.forEach(function(input) {
    if (input.type === 'checkbox') {
      if (!input.checked) {
        valid = false;
        input.closest('label').style.color = 'var(--danger)';
      } else {
        input.closest('label').style.color = 'inherit';
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
    alert('Please complete all mandatory fields marked in red.');
  }
  return valid;
}

function populateReview() {
  var isAnon = document.getElementById('sr_pref').value === 'Completely Anonymous';
  var reporter = isAnon ? 'Anonymous Whistleblower' : (document.getElementById('sr_name').value || 'Confidential');
  var child = document.getElementById('sr_child').value;
  var squad = document.getElementById('sr_squad').value;
  var loc = document.getElementById('sr_loc').value;

  document.getElementById('rev_sstatus').textContent = reporter;
  document.getElementById('rev_schild').textContent = child || 'Not specified';
  document.getElementById('rev_ssquad').textContent = squad || 'Not specified';
  document.getElementById('rev_sloc').textContent = loc || 'Not specified';
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

document.getElementById('safeForm').addEventListener('submit', function(e) {
  e.preventDefault();
  if (!validateSection(currentSec)) return;
  if (window.SP_FORMS && SP_FORMS.finish) {
    /* Phase 3: the success screen + reference appear ONLY after the
       server confirms it has the report. Offline/rejected states keep
       the form on the page with an honest explanation. */
    SP_FORMS.finish(this, { refEl: 'succ_saferef', hide: ['safeForm', 'stepTracker'], modal: 'successModal' });
  } else {
    /* sp-forms.js missing (demo fallback) — keep the page working */
    document.getElementById('succ_saferef').textContent = 'DEMO';
    document.getElementById('safeForm').style.display = 'none';
    document.getElementById('stepTracker').style.display = 'none';
    document.getElementById('successModal').classList.add('active');
  }
});
