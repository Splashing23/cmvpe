import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv(r"dataset\splits\Boston\samples.csv")

# Count non-null values per column
column_counts = df.count()

# Plot histogram
plt.figure(figsize=(10, 5))
plt.hist(column_counts, bins=20, edgecolor='black')
plt.xlabel("Number of Non-Empty Items per Column")
plt.ylabel("Frequency")
plt.title("Distribution of Column Item Counts")
plt.show()