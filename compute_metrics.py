import os

def compute_overlap(bbox1, bbox2):
    length = min(bbox2[0] - bbox1[2], bbox1[0] - bbox2[2])
    width = min(bbox2[1] - bbox1[3], bbox1[1] - bbox2[3])
    return max(length * width, 0)


for city in os.listdir(os.path.join("dataset", "splits")):
    city_splits_path = os.path.join("dataset", "splits", city)
    overlap_dict = {}
    with open(os.path.join(city_splits_path, "samples.csv"), "r") as f:
        lines = f.readlines()
        bbox_dict = {}

        for line in lines[1:]:
            aer_image_name = line.strip().split(',')[0]

            bbox = aer_image_name[:-4].split("_")[1:]
            bbox = [float(edge) for edge in bbox]
            bbox_dict[aer_image_name] = bbox

        for sample1 in lines[1:]:
            sample1_aerial = sample1.strip().split(',')[0]
            overlap = {}

            for sample2 in lines[1:]:
                sample2_aerial = sample2.strip().split(',')[0]
                intersect_area = compute_overlap(bbox_dict[sample1_aerial], bbox_dict[sample2_aerial])
                overlap[sample2] = intersect_area

            overlap_dict[sample1_aerial] = overlap
    print(f"{city}: {sample1_aerial}")
    print(overlap_dict[sample1_aerial])

    # with open("overlap.csv", "w") as f:
    #     f.write("")

