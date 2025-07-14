import os
import numpy as np
from collections import Counter, defaultdict

def compute_overlap(bbox1, bbox2):
    length = max(min(bbox2[2] - bbox1[0], bbox1[2] - bbox2[0]), 0)
    width = max(min(bbox2[3] - bbox1[1], bbox1[3] - bbox2[1]), 0)
    return length * width

def calculate_coverage_area(bbox_dict):
    """Calculate total geographic coverage area"""
    total_area = 0
    for bbox in bbox_dict.values():
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        total_area += area
    return total_area

def analyze_image_diversity(samples):
    """Analyze ground-level image diversity per aerial image"""
    diversity_stats = {}
    all_ground_images = set()
    
    for sample in samples[1:]:
        sample_images = sample.strip().split(',')
        aerial_name = sample_images[0]
        ground_images = sample_images[1:]
        
        diversity_stats[aerial_name] = {
            'count': len(ground_images),
            'unique_ratio': len(set(ground_images)) / len(ground_images) if ground_images else 0
        }
        all_ground_images.update(ground_images)
    
    return diversity_stats, len(all_ground_images)

def compute_redundancy_scores(aer_overlap_dict, threshold=0.8):
    """Identify highly redundant samples based on overlap"""
    redundancy_scores = {}
    redundant_samples = []
    
    for aerial_name, overlaps in aer_overlap_dict.items():
        # Count how many other samples this one overlaps significantly with
        high_overlap_count = sum(1 for overlap in overlaps.values() if overlap > threshold)
        redundancy_scores[aerial_name] = high_overlap_count
        
        if high_overlap_count > 0:
            redundant_samples.append((aerial_name, high_overlap_count))
    
    return redundancy_scores, sorted(redundant_samples, key=lambda x: x[1], reverse=True)

def geographic_distribution_analysis(bbox_dict):
    """Analyze spatial distribution patterns"""
    if not bbox_dict:
        return {
            'total_samples': 0,
            'mean_area': 0,
            'std_area': 0,
            'min_area': 0,
            'max_area': 0,
            'mean_centroid_distance': 0,
            'std_centroid_distance': 0,
            'coverage_area': 0
        }
    
    centroids = []
    areas = []
    
    for bbox in bbox_dict.values():
        centroid_x = (bbox[0] + bbox[2]) / 2
        centroid_y = (bbox[1] + bbox[3]) / 2
        centroids.append([centroid_x, centroid_y])
        
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        areas.append(area)
    
    centroids = np.array(centroids)
    areas = np.array(areas)
    
    # Calculate distribution statistics
    centroid_distances = []
    for i in range(len(centroids)):
        for j in range(i+1, len(centroids)):
            dist = np.linalg.norm(centroids[i] - centroids[j])
            centroid_distances.append(dist)
    
    return {
        'total_samples': len(bbox_dict),
        'mean_area': np.mean(areas) if len(areas) > 0 else 0,
        'std_area': np.std(areas) if len(areas) > 1 else 0,
        'min_area': np.min(areas) if len(areas) > 0 else 0,
        'max_area': np.max(areas) if len(areas) > 0 else 0,
        'mean_centroid_distance': np.mean(centroid_distances) if centroid_distances else 0,
        'std_centroid_distance': np.std(centroid_distances) if len(centroid_distances) > 1 else 0,
        'coverage_area': np.sum(areas)
    }

def calculate_density_metrics(bbox_dict, city_name):
    """Calculate samples per unit area and density patterns"""
    if not bbox_dict:
        return {
            'city': city_name,
            'sample_count': 0,
            'total_coverage_area': 0,
            'samples_per_unit_area': 0,
            'average_sample_area': 0
        }
    
    total_area = sum((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) for bbox in bbox_dict.values())
    sample_count = len(bbox_dict)
    
    return {
        'city': city_name,
        'sample_count': sample_count,
        'total_coverage_area': total_area,
        'samples_per_unit_area': sample_count / total_area if total_area > 0 else 0,
        'average_sample_area': total_area / sample_count if sample_count > 0 else 0
    }


for city in os.listdir(os.path.join("dataset", "splits")):
    city_splits_path = os.path.join("dataset", "splits", city)
    aer_overlap_dict = {}
    gl_overlap_dict = {}
    
    print(f"\n=== Analyzing {city} ===")
    
    with open(os.path.join(city_splits_path, "samples.csv"), "r") as f:
        lines = f.readlines()
        bbox_dict = {}

        for line in lines[1:]:
            aer_image_name = line.strip().split(',')[0]

            bbox = aer_image_name[:-4].split("_")[1:]
            bbox = [float(edge) for edge in bbox]
            bbox_dict[aer_image_name] = bbox

        # Check if we have any samples
        if not bbox_dict:
            print(f"No valid samples found in {city}")
            continue

        # Calculate new metrics
        coverage_area = calculate_coverage_area(bbox_dict)
        diversity_stats, total_unique_ground = analyze_image_diversity(lines)
        geo_stats = geographic_distribution_analysis(bbox_dict)
        density_stats = calculate_density_metrics(bbox_dict, city)
        
        print(f"Coverage Area: {coverage_area:.6f}")
        print(f"Total Unique Ground Images: {total_unique_ground}")
        print(f"Geographic Stats: {geo_stats}")
        print(f"Density Stats: {density_stats}")

        for sample1 in lines[1:]:
            sample1_images = sample1.strip().split(',')
            sample1_aerial = sample1_images[0]
            sample1_gls = set(sample1_images[1:])

            aer_overlap = {}
            gl_overlap = {}

            sample1_bbox = bbox_dict[sample1_aerial]

            area = (sample1_bbox[2] - sample1_bbox[0]) * (sample1_bbox[3] - sample1_bbox[1])

            for sample2 in lines[1:]:
                sample2_images = sample2.strip().split(',')
                sample2_aerial = sample2_images[0]
                sample2_gls = set(sample2_images[1:])

                aer_perc_overlap = compute_overlap(sample1_bbox, bbox_dict[sample2_aerial]) / area
                gl_perc_overlap = len(sample1_gls & sample2_gls) / len(sample1_gls)

                aer_overlap[sample2_aerial] = aer_perc_overlap
                gl_overlap[sample2_aerial] = gl_perc_overlap

            aer_overlap_dict[sample1_aerial] = aer_overlap
            gl_overlap_dict[sample1_aerial] = gl_overlap

        # Calculate redundancy scores
        redundancy_scores, redundant_samples = compute_redundancy_scores(aer_overlap_dict)
        
        print(f"\nRedundancy Analysis:")
        print(f"Most redundant samples (top 5):")
        for sample, score in redundant_samples[:5]:
            print(f"  {sample}: {score} high-overlap connections")
        
        print(f"\nDiversity Analysis:")
        if diversity_stats:
            avg_diversity = np.mean([stats['unique_ratio'] for stats in diversity_stats.values()])
            print(f"Average ground-level image diversity: {avg_diversity:.3f}")
        else:
            print("No diversity data available")
        
        # Print original overlap sums
        print(f"\nOriginal Overlap Sums:")
        for item in aer_overlap_dict:
            print(f"{item}: {sum(aer_overlap_dict[item].values()):.3f}")
    
    # with open("overlap.csv", "w") as f:
    #     f.write("")

