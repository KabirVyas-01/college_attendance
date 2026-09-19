// Minimalist UI Helpers

document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });
});

// Quick fill credentials on login page
function fillLogin(role, idVal, passVal) {
  const tabTriggerEl = document.querySelector(`#tab-${role}`);
  if (tabTriggerEl) {
    const tab = new bootstrap.Tab(tabTriggerEl);
    tab.show();
  }

  setTimeout(() => {
    if (role === 'student') {
      const uidInput = document.getElementById("student_uid");
      const passInput = document.getElementById("student_password");
      if (uidInput && passInput) {
        uidInput.value = idVal;
        passInput.value = passVal;
      }
    } else if (role === 'head') {
      const fIdInput = document.getElementById("head_faculty_id");
      const passInput = document.getElementById("head_password");
      if (fIdInput && passInput) {
        fIdInput.value = idVal;
        passInput.value = passVal;
      }
    } else if (role === 'teacher') {
      const fIdInput = document.getElementById("teacher_faculty_id");
      const passInput = document.getElementById("teacher_password");
      if (fIdInput && passInput) {
        fIdInput.value = idVal;
        passInput.value = passVal;
      }
    }
  }, 100);
}

// Fast Attendance Marking: Mark All as Present or Absent
function markAllAttendance(status) {
  const radios = document.querySelectorAll(`input[type="radio"][value="${status}"]`);
  radios.forEach((radio) => {
    radio.checked = true;
  });
  updateAttendanceCounter();
}

// Update live attendance counters on marking sheet
function updateAttendanceCounter() {
  const presentCount = document.querySelectorAll('input[type="radio"][value="P"]:checked').length;
  const absentCount = document.querySelectorAll('input[type="radio"][value="A"]:checked').length;
  
  const pBadge = document.getElementById("live-present-count");
  const aBadge = document.getElementById("live-absent-count");
  if (pBadge) pBadge.textContent = presentCount;
  if (aBadge) aBadge.textContent = absentCount;
}

// Copy to Clipboard utility
function copyToClipboard(text, label) {
  navigator.clipboard.writeText(text).then(() => {
    alert(`Copied ${label || 'text'}: ${text}`);
  });
}
