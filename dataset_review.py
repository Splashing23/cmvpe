import os

DATASET_DIR = '/storage1/jacobsn/Active/user_h.nia/projects/cmvpe/dataset'
CITY_FOLDERS = ['Colorado_Springs',
                'Lorain',
                'Southington',
                'Montpelier',
                'Portland',
                'Phoenix',
                'Denver',
                'Oklahoma City',
                'Des Moines',
                'Little Rock',
                'New Orleans',
                'Cleveland',
                'Miami',
                'Baltimore',
                'Dover',
                'Jersey City',
                'Hartford',
                'Providence',
                'Boston',
                'Burlington',
                'Nashua',
                'Houston',
                'Seattle',
                'Washington_DC',
                'Detroit',
                'San_Francisco'
                ]
SUB_FOLDERS = ['aerial', 'ground']


print('---')
for city in CITY_FOLDERS:
    for sub in SUB_FOLDERS:
        # count the number of .png files within the folder
        # print the number of files
        folder_path = os.path.join(DATASET_DIR, city, sub)
        if os.path.exists(folder_path):
            png_count = len([f for f in os.listdir(folder_path) if f.endswith('.png')])
            print(f'{city}/{sub}: {png_count}')
        else:
            print(f'##### {city}/{sub}: Folder not found')
print('---')