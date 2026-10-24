// Clinic Management System Reception Desk Script

document.addEventListener("DOMContentLoaded", () => {
    initLiveClock();
    initPatientSearch();
});

// Update Digital Clock at Reception Header
function initLiveClock() {
    const clockElem = document.getElementById("liveClock");
    if (!clockElem) return;

    function tick() {
        const now = new Date();
        const options = {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        };
        clockElem.textContent = now.toLocaleString('en-US', options);
    }

    tick();
    setInterval(tick, 1000);
}

// Live Search for Existing / Returning Patients
function initPatientSearch() {
    const searchInput = document.getElementById("searchPatientInput");
    const resultsBox = document.getElementById("patientSearchResults");
    if (!searchInput || !resultsBox) return;

    let debounceTimer;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            resultsBox.style.display = "none";
            resultsBox.innerHTML = "";
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search_patient?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    renderSearchResults(data, resultsBox);
                })
                .catch(err => {
                    console.error("Search error:", err);
                });
        }, 250);
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !resultsBox.contains(e.target)) {
            resultsBox.style.display = "none";
        }
    });
}

function renderSearchResults(patients, container) {
    if (!patients || patients.length === 0) {
        container.innerHTML = `
            <div class="search-item text-muted text-center py-3">
                <i class="bi bi-info-circle me-1"></i> No matching patient found. Please register as New Patient.
            </div>
        `;
        container.style.display = "block";
        return;
    }

    let html = "";
    patients.forEach(p => {
        html += `
            <div class="search-item d-flex justify-content-between align-items-center" onclick="selectReturningPatient(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                <div>
                    <div class="fw-bold text-dark">
                        ${p.name} 
                        <span class="badge-mr ms-2">${p.mr_number}</span>
                    </div>
                    <small class="text-muted">
                        <i class="bi bi-person"></i> ${p.age} yrs (${p.gender}) | 
                        <i class="bi bi-telephone"></i> ${p.phone} | 
                        <i class="bi bi-clock-history"></i> Visits: ${p.visits_count}
                    </small>
                </div>
                <button type="button" class="btn btn-sm btn-outline-primary fw-semibold">
                    <i class="bi bi-calendar-plus"></i> Select
                </button>
            </div>
        `;
    });

    container.innerHTML = html;
    container.style.display = "block";
}

function selectReturningPatient(patient) {
    const resultsBox = document.getElementById("patientSearchResults");
    const searchInput = document.getElementById("searchPatientInput");
    if (resultsBox) resultsBox.style.display = "none";
    if (searchInput) searchInput.value = `${patient.mr_number} - ${patient.name}`;

    const card = document.getElementById("selectedPatientCard");
    const idInput = document.getElementById("return_patient_id");
    const nameDisplay = document.getElementById("return_patient_name");
    const mrDisplay = document.getElementById("return_patient_mr");
    const detailsDisplay = document.getElementById("return_patient_details");

    if (card && idInput && nameDisplay && mrDisplay) {
        idInput.value = patient.id;
        nameDisplay.textContent = patient.name;
        mrDisplay.textContent = patient.mr_number;
        detailsDisplay.textContent = `Age: ${patient.age} yrs | Gender: ${patient.gender} | Contact: ${patient.phone} | Past Visits: ${patient.visits_count} (Last: ${patient.last_visit})`;
        card.style.display = "block";
    }
}

// Modal Quick Pre-fill for Patient Directory "Book Visit" button
function openQuickVisitModal(patientId, mrNumber, patientName) {
    const modalPatientId = document.getElementById("modal_patient_id");
    const modalMr = document.getElementById("modal_patient_mr");
    const modalName = document.getElementById("modal_patient_name");

    if (modalPatientId && modalMr && modalName) {
        modalPatientId.value = patientId;
        modalMr.textContent = mrNumber;
        modalName.textContent = patientName;
    }

    const modal = new bootstrap.Modal(document.getElementById("quickVisitModal"));
    modal.show();
}

// Slip Print Toggle: Standard A5 or 80mm Thermal Receipt
function toggleSlipFormat(format) {
    if (format === 'thermal') {
        document.body.classList.add('thermal-mode');
        document.getElementById('btnThermal')?.classList.add('active', 'btn-primary');
        document.getElementById('btnThermal')?.classList.remove('btn-outline-primary');
        document.getElementById('btnA5')?.classList.remove('active', 'btn-primary');
        document.getElementById('btnA5')?.classList.add('btn-outline-primary');
    } else {
        document.body.classList.remove('thermal-mode');
        document.getElementById('btnA5')?.classList.add('active', 'btn-primary');
        document.getElementById('btnA5')?.classList.remove('btn-outline-primary');
        document.getElementById('btnThermal')?.classList.remove('active', 'btn-primary');
        document.getElementById('btnThermal')?.classList.add('btn-outline-primary');
    }
}
