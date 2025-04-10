import csv
import random

file_path = "dataset\splits\Boston\samples copy 2.csv"

with open(file_path, "r", newline="") as infile:
    rows = list(csv.reader(infile))

with open(file_path, "w", newline="") as outfile:
    writer = csv.writer(outfile)

    for row in rows:
        if len(row) > 26:
            indices_to_remove = random.sample(range(1, len(row)), len(row) - 26)
            row = [col for i, col in enumerate(row) if i not in indices_to_remove]

        writer.writerow(row)