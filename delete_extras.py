import os
import csv

folder_path = "dataset\Boston\ground"
csv_path = "dataset\splits\Boston\samples.csv"

images = set(os.listdir(folder_path))

csv_images = set()

with open(csv_path, "r", newline="") as infile:
    rows = list(csv.reader(infile))
    for image in images:
        is_in_csv = False
        for row in rows:
            for col in row[1:]:
                csv_images.add(col)

images_to_save = images & csv_images
print(len(images_to_save))

# output_file = "dataset\splits\Boston\cleaned_samples.csv"

# with open(csv_path, "r", newline="") as infile, open(output_file, "w", newline="") as outfile:
#     reader = csv.reader(infile)
#     writer = csv.writer(outfile)

#     for row in reader:
#         new_row = [row[0]]
#         for col in row[1:]:
#             if col in images_to_save:
#                 new_row.append(col)
#         if len(new_row) >= 2:
#             writer.writerow(new_row)

# for image in images:
#     if image not in images_to_save:
#         # os.remove(os.path.join(folder_path, image))