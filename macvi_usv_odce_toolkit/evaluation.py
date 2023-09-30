import os
import json
import tempfile
import contextlib  # redirect_stdout

import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import pycocotools.coco
import pycocotools.cocoeval

from .dataset import load_camera_calibration
from .danger_zone_mask import construct_mask_from_danger_zone
from .sea_edge_mask import construct_mask_from_sea_edge
from . import utils

def convert_to_coco_structures(lars_path, eval_set, results_json_file):
    """
    Convert the dataset annotations and detection results in COCO-compatible data structures.

    Parameters
    ----------
    lars_path : str
        Path to the LaRS dataset.
    eval_set : str
        Subset to evaluate, either train, test or val
    results_json_file : str
        Full path to detection results JSON file.

    Returns
    -------
    coco_dataset : dict
        Dictionary containing dataset annotations in COCO-compatible data structure.
    coco_results : list
        List containing detection results in COCO-compatible data structure.
    """

    assert eval_set in {'train', 'test', 'val'}

    dataset_json_filename = f'{lars_path}/{eval_set}/panoptic_annotations.json'    

    # Load dataset JSON file
    with open(dataset_json_filename, 'r') as fp:
        dataset = json.load(fp)

    # Load results (detections) file
    with open(results_json_file, 'r') as fp:
        results = json.load(fp)

    dataset_annotations = dataset['annotations']
    results_annotations = results['annotations']

    # Sanity check
    assert len(dataset_annotations) == len(results_annotations), "Mismatch in dataset and result sequences length! Did you perhaps supply results for the wrong LaRS subset?"

    # Global lists of images, annoations, and detections - we are going to merge individual sequences into a single one.
    image_entries = []
    annotation_entries = []
    detection_entries = []

    image_id = 0
    annotation_id = 0

    for data_ann, result_ann in zip(dataset_annotations, results_annotations):

        assert data_ann['file_name'] == result_ann['file_name'], "Dataset and results sequence ID mismatch!"

        pan_ann_fn = f'{lars_path}/{eval_set}/panoptic_masks/{data_ann["file_name"]}'
        sem_ann_fn = f'{lars_path}/{eval_set}/semantic_masks/{data_ann["file_name"]}'

        pan_ann = cv2.imread(pan_ann_fn)[...,-1]
        sem_ann = cv2.imread(sem_ann_fn)[...,0]

        image_height, image_width = sem_ann.shape

        ignore_mask = np.zeros_like(sem_ann, dtype=np.uint8)
        ignore_mask[(pan_ann==1) | (sem_ann==255)]=1        

        annotated_obstacles = data_ann.get('segments_info', [])
        detected_obstacles = result_ann.get('detections', [])

        # process GT
        for annotated_obstacle in annotated_obstacles:
            bbox = annotated_obstacle['bbox']
            bbox = [int(x) for x in bbox]
            ignore = False

            class_id = 0

            annotation_entries.append({
                'id': annotation_id,
                'image_id': image_id,
                'category_id': class_id,
                'bbox': bbox,
                'iscrowd': 0,
                'area': annotated_obstacle['area'],
                'segmentation': [],
                'ignore': int(ignore),  # bool -> int
            })
            annotation_id += 1  # Increment global annotation ID

        # iterate over detections and check overlap with mask
        for detected_obstacle in detected_obstacles:
            bbox = detected_obstacle['bbox']

            ignore = utils.bbox_in_mask(ignore_mask, bbox, thr=0.75)

            class_id = 0

            detection_entries.append({
                'image_id': image_id,
                'category_id': class_id,
                'bbox': bbox,
                'score': 1,
                'ignore': int(ignore),  # bool -> int
            })

        image_entries.append({
            'id': image_id,
            'width': image_width,
            'height': image_height,
            'file_name': data_ann["file_name"],
        })
        image_id += 1  # Increment global image ID    

    # COCO dataset/ground truth structure
    coco_dataset = {
        'info': {
            'year': 2023,
        },
        'categories': [{
            'id': 0,
            'name': 'obstacle',
            'supercategory': 'obstacle',
        }],
        'annotations': annotation_entries,
        'images': image_entries,
    }

    # COCO results
    coco_results = detection_entries

    return coco_dataset, coco_results

def evaluate_detection_results(lars_path, eval_set, results_json_file):
    """
    Evaluate detection results.

    This function loads the dataset annotations and detection results from their respective files, converts them to
    COCO-compatible data structures, and performs evaluation using pycocotools.

    Parameters
    ----------
    lars_path : str
        Path to the LaRS dataset.
    eval_set : str
        Subset to evaluate, either train, test or val
    results_json_file : str
        Full path to detection results JSON file.

    Returns
    -------
    f_scores : tuple
        A four-element tuple containing F-score values: F_all, F_small, F_medium, and F_large.
    """

    # Convert annotations and results to COCO-compatible structures
    dataset_dict, results_list = convert_to_coco_structures(
        lars_path,
        eval_set,
        results_json_file,
    )

    # handle empty json results
    if not results_list:
        return 0, 0, 0, 0

    # Capture pycocotools' output to prevent spamming stdout with its diagnostic messages
    with contextlib.redirect_stdout(None):
        # Initialize COCO helper classes from in-memory data, to avoid having to write them to temporary files...
        coco_dataset = pycocotools.coco.COCO()
        # This is equivalent to passing filename to pycocotools.coco.COCO()
        coco_dataset.dataset = dataset_dict
        coco_dataset.createIndex()

        # coco_dataset.loadRes() can be passed either filename or a list
        print(results_list)
        coco_results = coco_dataset.loadRes(results_list)

        # Create evaluation...
        coco_evaluation = pycocotools.cocoeval.COCOeval(coco_dataset, coco_results, iouType='bbox')
        coco_evaluation.params.iouThrs = np.array([0.3, 0.3])  # IoU thresholds for evaluation

        # ... and evaluate
        coco_evaluation.evaluate()
        coco_evaluation.accumulate()
        coco_evaluation.summarize()

    stats = np.nan_to_num(coco_evaluation.stats)
    stats[stats == -1] = 0

    # Compute F-scores
    def _f_score(precision, recall):
        if precision != 0 and recall != 0:
            return 2 * (precision * recall) / (precision + recall)
        else:
            return 0

    f_all = _f_score(stats[0], stats[8])
    f_small = _f_score(stats[3], stats[9])
    f_medium = _f_score(stats[4], stats[10])
    f_large = _f_score(stats[5], stats[11])

    return f_all, f_small, f_medium, f_large
