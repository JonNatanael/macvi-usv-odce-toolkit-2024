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

# Danger zone parameters
# NOTE: estimated camera HFoV is actually around 66 degrees, but we use 80 degrees to ensure that we project at least
# one sampled point beyond the image borders.
DANGER_ZONE_RANGE = 15  # danger zone range, in meters
DANGER_ZONE_CAMERA_HEIGHT = 1.0  # height of the camera (in meters)
DANGER_ZONE_CAMERA_FOV = 80  # camera HFoV, in degrees
DANGER_ZONE_IMAGE_MARGIN = 10  # image margin, in pixels

# Obstacle classes
OBSTACLE_CLASSES = ('ship', 'person', 'other')
OBSTACLE_CLASS_NAME_TO_ID_MAP = {name: idx for idx, name in enumerate(OBSTACLE_CLASSES)}


def convert_to_coco_structures(dataset_json_file, results_json_file, sequences=None, mode='full', ignore_class=False):
    """
    Convert the dataset annotations and detection results in COCO-compatible data structures.

    Parameters
    ----------
    dataset_json_file : str
        Full path to dataset JSON file.
    results_json_file : str
        Full path to detection results JSON file.
    sequences : iterable, optional
        Optional list of sequence IDs to process. By default, all sequences are processed.
    mode : str, optional
        Evaluation mode:
            'full': use only static ignore mask provided by camera calibration.
            'edge': use sea-edge based ignore mask in addition to static mask.
            'dz': use danger-zone based ignore mask in addition to static mask.
    ignore_class : bool, optional
        Flag indicating whether to ignore class labels or not.

    Returns
    -------
    coco_dataset : dict
        Dictionary containing dataset annotations in COCO-compatible data structure.
    coco_results : list
        List containing detection results in COCO-compatible data structure.
    """

    assert mode in {'edge', 'dz', 'full'}

    sequences = set(sequences) if sequences is not None else set()

    # Load dataset JSON file
    with open(dataset_json_file, 'r') as fp:
        dataset = json.load(fp)
    # dataset = dataset['dataset']
    dataset_path = os.path.dirname(dataset_json_file)  # Dataset root directory

    # Load results (detections) file
    with open(results_json_file, 'r') as fp:
        results = json.load(fp)
    # results = results['dataset']

    # Select sequences
    # if sequences:
    #     dataset_sequences = [seq for seq in dataset['sequences'] if seq['id'] in sequences]
    #     results_sequences = [seq for seq in results['sequences'] if seq['id'] in sequences]
    # else:
    #     dataset_sequences = dataset['sequences']
    #     results_sequences = results['sequences']

    dataset_annotations = dataset['annotations']
    results_annotations = results['annotations']

    # Sanity check
    assert len(dataset_annotations) == len(results_annotations), "Mismatch in dataset and result sequences length!"

    # Ensure sequences are ordered by ID, just in case
    # dataset_sequences.sort(key=lambda seq: seq['id'])
    # results_sequences.sort(key=lambda seq: seq['id'])

    # Global lists of images, annoations, and detections - we are going to merge individual sequences into a single one.
    image_entries = []
    annotation_entries = []
    detection_entries = []

    image_id = 0
    annotation_id = 0

    for data_ann, result_ann in zip(dataset_annotations, results_annotations):

        assert data_ann['file_name'] == result_ann['file_name'], "Dataset and results sequence ID mismatch!"

        # drop image data to image entries, annotation data to annotation entries (in correct format)
        # check if result data lies within ignore region and ignore it, otherwise drop it into detection entries

        # TODO get ignore mask
        # TODO build filename for panoptic and segmentation masks

        lars_path = dataset_json_file.split('/')
        lars_path = '/'.join(lars_path[:-1])
        # print("lars_path", lars_path)

        im_fn = f'{lars_path}/images/{data_ann["file_name"]}'
        im_fn = im_fn.replace('png', 'jpg')

        pan_ann_fn = f'{lars_path}/panoptic_masks/{data_ann["file_name"]}'
        # print(pan_ann_fn, os.path.exists(pan_ann_fn))
        sem_ann_fn = f'{lars_path}/semantic_masks/{data_ann["file_name"]}'
        # print(sem_ann_fn, os.path.exists(sem_ann_fn))

        im = cv2.imread(im_fn)
        pan_ann = cv2.imread(pan_ann_fn)[...,-1]
        sem_ann = cv2.imread(sem_ann_fn)[...,0]

        image_height, image_width = sem_ann.shape

        # pan_ann==1 => static obstacle        
        # sem_ann==255 => ignore label

        ignore_mask = np.zeros_like(sem_ann, dtype=np.uint8)
        ignore_mask[(pan_ann==1) | (sem_ann==255)]=1


        

        annotated_obstacles = data_ann.get('segments_info', [])
        # detected_obstacles = data_ann.get('segments_info', []) # WARNING
        detected_obstacles = result_ann.get('detections', [])

        # process GT
        for annotated_obstacle in annotated_obstacles:
            bbox = annotated_obstacle['bbox']
            bbox = [int(x) for x in bbox]
            # Add negative annotations to the mask
            ignore = False

            # overlap_values = utils.compute_iou_overlaps(bbox, detected_obstacles)
            # print(overlap_values)
            # input()

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
            bbox = [int(x) for x in bbox]

            ignore = False

            # print(bbox)
            ignore = utils.bbox_in_mask(ignore_mask, bbox, thr=0.75)
            if ignore:
                # print(bbox)

                p1, p2, w, h = bbox
                
                # plt.clf()
                # plt.imshow(im)
                # plt.imshow(ignore_mask, alpha=0.5)
                # plt.gca().add_patch(Rectangle((p1,p2),w,h,linewidth=1,edgecolor='r',facecolor='none'))
                # plt.draw(); plt.pause(0.01)
                # plt.waitforbuttonpress()

            class_id = 0

            detection_entries.append({
                'image_id': image_id,
                'category_id': class_id,
                'bbox': bbox,
                'score': 1,
                'ignore': int(ignore),  # bool -> int
            })



        # print(image_width, image_height)

        image_entries.append({
            'id': image_id,
            'width': image_width,
            'height': image_height,
            'file_name': data_ann["file_name"],
        })
        image_id += 1  # Increment global image ID

        # print(annotation_entries)
        # print()
        # print(detection_entries)
        # input()

    

    # COCO dataset/ground truth structure
    coco_dataset = {
        'info': {
            'year': 2023,
        },
        'categories': [{
            'id': idx,
            'name': name,
            'supercategory': 'obstacle',
        } for idx, name in enumerate(OBSTACLE_CLASSES)],
        'annotations': annotation_entries,
        'images': image_entries,
    }

    # COCO results
    coco_results = detection_entries

    return coco_dataset, coco_results

def evaluate_detection_results(dataset_json_file, results_json_file, sequences=None, mode='full', ignore_class=False):
    """
    Evaluate detection results.

    This function loads the dataset annotations and detection results from their respective files, converts them to
    COCO-compatible data structures, and performs evaluation using pycocotools.

    Parameters
    ----------
    dataset_json_file : str
        Full path to dataset JSON file.
    results_json_file : str
        Full path to detection results JSON file.
    sequences : iterable, optional
        Optional list of sequence IDs to process. By default, all sequences are processed.
    mode : str, optional
        Evaluation mode:
            'full': use only static ignore mask provided by camera calibration.
            'edge': use sea-edge based ignore mask in addition to static mask.
            'dz': use danger-zone based ignore mask in addition to static mask.
    ignore_class : bool, optional
        Flag indicating whether to ignore class labels or not.

    Returns
    -------
    f_scores : tuple
        A four-element tuple containing F-score values: F_all, F_small, F_medium, and F_large.
    """

    # Convert annotations and results to COCO-compatible structures
    dataset_dict, results_list = convert_to_coco_structures(
        dataset_json_file,
        results_json_file,
        sequences,
        mode,
        ignore_class,
    )

    # Capture pycocotools' output to prevent spamming stdout with its diagnostic messages
    with contextlib.redirect_stdout(None):
        # Initialize COCO helper classes from in-memory data, to avoid having to write them to temporary files...
        coco_dataset = pycocotools.coco.COCO()
        # This is equivalent to passing filename to pycocotools.coco.COCO()
        coco_dataset.dataset = dataset_dict
        coco_dataset.createIndex()

        # coco_dataset.loadRes() can be passed either filename or a list
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

    print(stats)

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
