phones = [
    {'make': 'Google', 'model': 216, 'color': 'Black'},
    {'make': 'Mi Max', 'model': '2', 'color': 'Gold'},
    {'make': 'Samsung', 'model': 7, 'color': 'Blue'}
]
 
print("Original list:", phones)
 
sorted_phones = sorted(phones, key=lambda x: x['color'])
 
print("Sorted by color:", sorted_phones)
