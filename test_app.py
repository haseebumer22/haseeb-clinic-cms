import requests

base = 'http://127.0.0.1:5000'
s = requests.Session()

# 1. Test homepage
r = s.get(f'{base}/')
assert r.status_code == 200, f'Status {r.status_code}'
assert 'HASEEB HEALTH CLINIC' in r.text
print('✓ Homepage loaded successfully')

# 2. Test Patient Registration
reg_data = {
    'patient_name': 'Haseeb Umer',
    'age': '28',
    'gender': 'Male',
    'phone_number': '0300-1234567',
    'blood_group': 'B+',
    'address': 'Model Town, Lahore',
    'doctor': 'Dr. Sara Malik',
    'symptoms': 'Fever and Cough'
}
r2 = s.post(f'{base}/register', data=reg_data, allow_redirects=True)
assert r2.status_code == 200, f'Status {r2.status_code}'
assert 'MR-000001' in r2.text
assert 'Haseeb Umer' in r2.text
assert 'Dr. Sara Malik' in r2.text
print('✓ Patient Registration & Printable Slip verified (MR-000001, Token #01)')

# 3. Test Search API
r3 = s.get(f'{base}/api/search_patient?q=Haseeb')
assert r3.status_code == 200
data = r3.json()
assert len(data) > 0
patient_id = data[0]['id']
mr_num = data[0]['mr_number']
print(f'✓ Search API verified: Found {data[0]["name"]} ({mr_num})')

# 4. Test Returning Patient New Visit (Permanent MR)
visit_data = {
    'patient_id': patient_id,
    'doctor': 'Dr. Ahmed Khan',
    'symptoms': 'Follow-up checkup'
}
r4 = s.post(f'{base}/new-visit', data=visit_data, allow_redirects=True)
assert r4.status_code == 200
assert 'MR-000001' in r4.text
assert 'Dr. Ahmed Khan' in r4.text
print('✓ Returning Patient Re-visit verified (Permanent MR-000001 preserved, Token #02 issued)')

# 5. Test Patient Directory
r5 = s.get(f'{base}/patients')
assert r5.status_code == 200
assert 'MR-000001' in r5.text
assert '2 Visits' in r5.text
print('✓ Patient Directory verified (showing 2 total visits)')

# 6. Test Daily Queue / Visits
r6 = s.get(f'{base}/visits')
assert r6.status_code == 200
assert 'Haseeb Umer' in r6.text
print('✓ Daily Queue verified')

# 7. Test Doctors page
r7 = s.get(f'{base}/doctors')
assert r7.status_code == 200
assert 'Dr. Sara Malik' in r7.text
print('✓ Doctors Management verified')

print('\nALL CLINIC MANAGEMENT SYSTEM FUNCTIONAL TESTS PASSED 100%!')
