// Clinic Management System Reception Desk Script

document.addEventListener("DOMContentLoaded", () => {
    initLiveClock();
    initPatientSearch();
    initDoctorTokenTracker();
    initPhoneValidationTracker();
});

// Dynamic Doctor OPD Token Tracker on Reception Desk
function initDoctorTokenTracker() {
    const docSelect = document.getElementById("doctor");
    const tokenBadge = document.getElementById("selectedDoctorTokenBadge");
    const statToken = document.getElementById("statDoctorToken");

    function updateToken() {
        if (!docSelect) return;
        const selectedOption = docSelect.options[docSelect.selectedIndex];
        if (!selectedOption) return;
        const token = selectedOption.getAttribute("data-token") || "1";
        const docName = selectedOption.value;
        if (tokenBadge) {
            tokenBadge.textContent = `Next OPD for ${docName}: #${token}`;
        }
        if (statToken) {
            statToken.textContent = `#${token}`;
        }
    }

    if (docSelect) {
        docSelect.addEventListener("change", updateToken);
        updateToken();
    }
}

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
        const relationBadge = p.relation_info 
            ? `<span class="badge bg-info-subtle text-info-emphasis border border-info-subtle ms-1 small py-0"><i class="bi bi-people-fill me-1"></i>${p.relation_info}</span>`
            : '';
        html += `
            <div class="search-item d-flex justify-content-between align-items-center" onclick="selectReturningPatient(${JSON.stringify(p).replace(/"/g, '&quot;')})">
                <div>
                    <div class="fw-bold text-dark">
                        ${p.name} 
                        <span class="badge-mr ms-2">${p.mr_number}</span>
                        ${relationBadge}
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

// Live Phone Duplicate Detection & Family Relation Linking
function initPhoneValidationTracker() {
    const phoneInput = document.getElementById("phone_number");
    const spinner = document.getElementById("phoneCheckSpinner");
    const container = document.getElementById("phoneLookupContainer");
    const primaryName = document.getElementById("fetchedPrimaryName");
    const primaryMR = document.getElementById("fetchedPrimaryMR");
    const primaryMeta = document.getElementById("fetchedPrimaryMeta");
    const primaryVisits = document.getElementById("fetchedPrimaryVisits");
    const labelPrimaryBold = document.getElementById("labelPrimaryNameBold");
    const familyBadges = document.getElementById("fetchedFamilyBadges");
    const familyList = document.getElementById("fetchedFamilyMembersList");
    const isFamilySwitch = document.getElementById("is_family_member");
    const familyRelationFields = document.getElementById("familyRelationFields");
    const relationSelect = document.getElementById("relation_to_primary");
    const btnBookReturning = document.getElementById("btnBookReturningFromPhone");
    const btnCopyAddress = document.getElementById("btnCopyAddress");
    const addressInput = document.getElementById("address");
    const newPatientForm = document.getElementById("newPatientForm");

    if (!phoneInput || !container) return;

    let debounceTimer;
    let currentPrimaryPatient = null;
    let isDuplicatePhone = false;

    // Toggle Family switch
    if (isFamilySwitch && familyRelationFields) {
        isFamilySwitch.addEventListener("change", () => {
            if (isFamilySwitch.checked) {
                familyRelationFields.style.display = "flex";
                if (relationSelect) relationSelect.required = true;
            } else {
                familyRelationFields.style.display = "none";
                if (relationSelect) {
                    relationSelect.required = false;
                    relationSelect.value = "";
                }
            }
        });
    }

    // Copy Address Button
    if (btnCopyAddress) {
        btnCopyAddress.addEventListener("click", () => {
            if (currentPrimaryPatient && currentPrimaryPatient.address && addressInput) {
                addressInput.value = currentPrimaryPatient.address;
                btnCopyAddress.innerHTML = `<i class="bi bi-check2 text-success me-1"></i> Address Copied!`;
                setTimeout(() => {
                    btnCopyAddress.innerHTML = `<i class="bi bi-geo-alt me-1"></i> Copy Family Address`;
                }, 2000);
            }
        });
    }

    // Phone input typing tracker
    phoneInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        const rawVal = e.target.value.trim();
        const digits = rawVal.replace(/\D/g, "");

        if (digits.length < 10) {
            container.style.display = "none";
            isDuplicatePhone = false;
            currentPrimaryPatient = null;
            if (isFamilySwitch) isFamilySwitch.checked = false;
            if (familyRelationFields) familyRelationFields.style.display = "none";
            if (relationSelect) {
                relationSelect.required = false;
                relationSelect.value = "";
            }
            return;
        }

        if (spinner) spinner.classList.remove("d-none");

        debounceTimer = setTimeout(() => {
            fetch(`/api/check_phone?phone=${encodeURIComponent(rawVal)}`)
                .then(res => res.json())
                .then(data => {
                    if (spinner) spinner.classList.add("d-none");
                    if (data.found && data.primary_patient) {
                        isDuplicatePhone = true;
                        currentPrimaryPatient = data.primary_patient;
                        container.style.display = "block";

                        if (primaryName) primaryName.textContent = data.primary_patient.name;
                        if (primaryMR) primaryMR.textContent = data.primary_patient.mr_number;
                        if (primaryMeta) {
                            primaryMeta.textContent = `Age: ${data.primary_patient.age} yrs | Gender: ${data.primary_patient.gender} | Blood: ${data.primary_patient.blood_group || 'N/A'} | Area: ${data.primary_patient.address || 'N/A'}`;
                        }
                        if (primaryVisits) primaryVisits.textContent = `${data.primary_patient.visits_count} past visits`;
                        if (labelPrimaryBold) labelPrimaryBold.textContent = data.primary_patient.name;

                        // List family members if any exist
                        if (familyList && familyBadges) {
                            if (data.family_members && data.family_members.length > 0) {
                                familyList.classList.remove("d-none");
                                familyBadges.innerHTML = data.family_members.map(fm => `
                                    <span class="badge bg-secondary-subtle text-secondary border">
                                        ${fm.name} (${fm.relation} - ${fm.mr_number})
                                    </span>
                                `).join("");
                            } else {
                                familyList.classList.add("d-none");
                                familyBadges.innerHTML = "";
                            }
                        }

                        // Attach Quick Returning Visit handler
                        if (btnBookReturning) {
                            btnBookReturning.onclick = () => {
                                selectReturningPatient(data.primary_patient);
                                const card = document.getElementById("selectedPatientCard");
                                if (card) card.scrollIntoView({ behavior: 'smooth' });
                            };
                        }
                    } else {
                        isDuplicatePhone = false;
                        currentPrimaryPatient = null;
                        container.style.display = "none";
                        if (isFamilySwitch) isFamilySwitch.checked = false;
                        if (familyRelationFields) familyRelationFields.style.display = "none";
                        if (relationSelect) {
                            relationSelect.required = false;
                            relationSelect.value = "";
                        }
                    }
                })
                .catch(err => {
                    if (spinner) spinner.classList.add("d-none");
                    console.error("Phone check error:", err);
                });
        }, 300);
    });

    // Form submission validation
    if (newPatientForm) {
        newPatientForm.addEventListener("submit", (e) => {
            const nameInput = document.getElementById("patient_name");
            const ageInput = document.getElementById("age");

            // Client-side validation checks
            if (nameInput && nameInput.value.trim().length < 2) {
                e.preventDefault();
                alert("Please enter a valid patient full name (at least 2 characters).");
                nameInput.focus();
                return;
            }

            if (ageInput) {
                const ageVal = parseInt(ageInput.value, 10);
                if (isNaN(ageVal) || ageVal < 1 || ageVal > 125) {
                    e.preventDefault();
                    alert("Please enter a valid patient age between 1 and 125 years.");
                    ageInput.focus();
                    return;
                }
            }

            // Duplicate phone enforcement: Cannot register with duplicate phone unless marked as family member
            if (isDuplicatePhone && isFamilySwitch && !isFamilySwitch.checked) {
                e.preventDefault();
                alert(`Phone number is already registered to ${currentPrimaryPatient?.name || 'an existing patient'}. Registered phone numbers cannot be used twice unless you check 'Register as Family Member' and select their relation.`);
                container.scrollIntoView({ behavior: 'smooth' });
                return;
            }

            if (isDuplicatePhone && isFamilySwitch && isFamilySwitch.checked) {
                if (!relationSelect || !relationSelect.value) {
                    e.preventDefault();
                    alert(`Please select the family relationship to ${currentPrimaryPatient?.name || 'the primary patient'}.`);
                    if (relationSelect) relationSelect.focus();
                    return;
                }
            }
        });
    }
}
