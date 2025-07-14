# import pandas as pd
import matplotlib.pyplot as plt

# Read the CSV as a raw list of lines (without assuming a fixed structure)
with open("dataset\splits\Boston\samples.csv", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Count the number of items (columns) in each row
row_lengths = [len(line.strip().split(",")) - 1 for line in lines]  # Change delimiter if needed

# Plot the histogram of row lengths
plt.figure(figsize=(8, 5))
plt.hist(row_lengths, bins=range(min(row_lengths), max(row_lengths) + 1), edgecolor='black', alpha=0.7)
plt.xlabel("Number of Columns in a Row")
plt.ylabel("Frequency")
plt.title("Distribution of Column Count Per Row")
plt.show()
