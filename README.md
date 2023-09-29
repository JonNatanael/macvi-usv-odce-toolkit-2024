
# USV Obstacle Detection Challenge Evaluation Toolkit

This repository contains source code of the evaluation toolkit for the
*USV Obstacle Detection Challenge*, hosted at the *2nd Workshop on Maritime
Computer Vision (MaCVi)* as part of the WACV2024.

The official site for the challenge can be found [here](https://macvi.org/workshop/macvi24).

The evaluation protocol is based on the paper by *Bovcon et al.*:

Bovcon Borja, Muhovič Jon, Vranac Duško, Mozetič Dean, Perš Janez and Kristan Matej,
*"MODS -- A USV-oriented object detection and obstacle segmentation benchmark"*,
IEEE Transactions on Intelligent Transportation Systems, 2021.
[Pre-print version available on arXiv](https://arxiv.org/abs/2105.02359).


The evaluation code is based on the implementation provided by
the authors in https://github.com/bborja/mods_evaluation
in `object_detection` sub-directory in `bbox_obstacle_detection` branch
([here](https://github.com/bborja/mods_evaluation/tree/bbox_obstacle_detection/object_detection)).


## Getting started

### 1. Download the LaRS dataset

Download and unpack [the LaRS dataset](https://vision.fe.uni-lj.si/public/mods).

### 2. Process the dataset with your detection method

Use your algorithm to process the validation subset of the LaRS dataset.

For training data, you can use any other dataset that is available to
you, including the [MODD2 dataset](https://box.vicos.si/borja/viamaro/index.html)
and the older [MODD dataset](https://www.vicos.si/resources/modd).

The algorithm should output the detections with rectangular axis-aligned
bounding boxes of waterborne objects belonging to the following semantic
classes: *vessel*, *person*, and *other*. The results should be stored
in a single JSON file using the format described below.

#### Results file format

The results JSON file, expected by the evaluation tool, is very similar
to the `panoptic_annotations.json` file from the LaRS dataset, except that each frame
object provides a `detections` array describing detected obstacles:

```json
{
  "info": {},
  "images": [
    {
      "id": 3995,
      "width": 1280,
      "height": 720,
      "file_name": "yt028_01_00030.jpg"
    },
    <...>
  ],
  "annotations": [
    {
      "image_id": 3995,
      "file_name": "yt028_01_00030.png",
      "detections": [
        {
          "id": 1,
          "bbox": [
            0,
            0,
            1280,
            413
          ],
        },
        <...>
      ]
    },
    <...>
  ]
}

```
The JSON file must contain the list of LaRS images, then the list of annotations, one annotation per image. The annotation element must contain the appropriate `id` filed (that matches the corresponding image ID). Each annotation element must contain a `detections` array, which contains the detections produced by your algorithm. If there are no detections in the frame, the `detections` should be empty. Otherwise, it should contain one object per detection, consisting of an `id` which should be unique within the image, and `bbox` (bounding box; `[x, y, width, height]`).

The above example shows the structure of the results file. In fact, the easiest way of generating a correct results file would be to load the data from `panotpic_annotations.json` and, for each element of the `annotations` list, add the `detections` array.

For reference, we provide an exemplar result JSON file for the methods YOLOv5:
* [detection-results-original.zip](https://rokm.dynu.net/macvi2023_detection/detection-results-original.zip):
  this archive contains original JSON files, as provided by the authors.
* [detection-results-minimal.zip](https://rokm.dynu.net/macvi2023_detection/detection-results-minimal.zip):
  this archive contains JSON files with minimum content required by the evaluation toolkit.

These reference detection JSON files can also be used in the subsequent
steps to verify that the evaluation toolkit has been properly installed
and is functioning as expected. They also illustrate various options
discussed above (for example, results for SSD omit empty `detections`
array; results for FCOS and SSD use numeric class `type`, while MaskRCNN
and YOLOv4 use string-based class `type`).

### 3. Install the evaluation toolkit

The evaluation toolkit requires a recent version of python3 (>= 3.6)
and depends on `pycocotools`, `numpy`, and `opencv-python-headless` (or
a "regular" `opencv-python`).

To prevent potential conflicts with python packages installed in the
global/base python environment, it is recommended to use a separate
python virtual environment using python's `venv` module:

1. Create the virtual environment:

```python3 -m venv venv-usv```

This will create a new virtual environment called `venv-usv` in the
current working directory.

2. Activate the virtual environment:

On Linux and macOS (assuming `bash` shell), run:

```
. venv-usv/bin/activate
```

On Windows, run:

```
venv-usv/Scripts/activate
```

3. Once virtual environment is activated, update `pip`, `wheel`, and `setuptools`:

```
python3 -m pip install --upgrade pip wheel setuptools
```

4a. Install the toolkit (recommended approach)

The toolkit can be installed directly from the git repository, using the
following command

```
python3 -m pip install git+https://github.com/rokm/macvi-usv-odce-toolkit.git
```

This will automatically check out the source code from the repository,
and install it into your (virtual) environment. It should also create
an executable called ``macvi-usv-odce-tool`` in your environment's
scripts directory. Running

```
macvi-usv-odce-tool --help
```

should display the help message:

```
usage: macvi_usv_odce_tool [-h] [--version] command ...

MaCVi USV Obstacle Detection Challenge Evaluation Toolkit

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

valid commands:
  command               command description
    evaluate (e)        Evaluate the results.
    prepare-submission (s)
                        Evaluate the results and prepare archive for submission.
    unpack-submission (u)
                        Unpack the submission archive.
```

The tool provides three commands (`evaluate`, `prepare-submission`,
and `unpack-submission`); the help for each can be obtained by adding
`--help` argument *after* the command name:

```
macvi_usv_odce_tool evaluate --help
macvi_usv_odce_tool prepare-submission --help
```

NOTE: Runing the tool via the ``macvi-usv-odce-tool`` requires your
environment's scripts directory to be in `PATH`. This is usually the
case when using virtual environments, but may not be the case if you
are using your base python environment (especially on Windows). If
the system cannot find the ``macvi-usv-odce-tool`` command, try
using

```
python3 -m macvi_usv_odce_toolkit
```

instead of `macvi_usv_odce_tool`. If neither works, the toolkit was
either not installed, or you have forgotten to activate your virtual
environment.


4b. Install the toolkit (alternative approach)

Alternatively, you can also check out the source code from the repository,
and run the ``macvi_usv_odce_tool.py`` script to launch the evaluation
tool from within the check-out directory:

```
git clone https://github.com/rokm/macvi-usv-odce-toolkit.git
cd macvi-usv-odce-toolkit
python3 -m pip install --requirement requirements.txt
python3 macvi_usv_odce_tool.py --help
```

### 4. Evaluate the results

While testing your algorithm locally, you can use the `evaluate` command
to perform evaluation and receive immediate feedback. Assuming that your
current working directory contains unpacked MODS dataset in `mods`
sub-directory and the results JSON file called `results.json`,
run:

```
macvi-usv-odce-tool evaluate mods/mods.json results.json
```

This should run the evaluation using all three detection evaluation
setups from the *Bovcon et al.* paper:
* Setup 1: evaluation using sea-edge based mask, taking into account the
  class labels of ground truth and detections.
* Setup 2: evaluation using sea-edge based mask, ignoring the class
  labels (detection without recognition).
* Setup 3: evaluation using danger-zone based mask (the radial area
  with radius 15 meters in front of the USV), ignoring the class
  labels.

```
MaCVi USV Obstacle Detection Challenge Evaluation Toolkit

Settings:
 - mode: 'evaluate'
 - dataset JSON file: 'mods/mods.json'
 - results JSON file: 'results.json'
 - output file: None
 - sequence(s): None

Evaluating Setup 1...
Evaluation complete in 16.37 seconds!
Evaluating Setup 2...
Evaluation complete in 15.39 seconds!
Evaluating Setup 3...
Evaluation complete in 16.37 seconds!

Results: F_all F_small F_medium F_large
Setup_1: 0.122 0.065 0.209 0.260
Setup_2: 0.172 0.090 0.385 0.522
Setup_3: 0.964 0.976 0.958 0.968

Challenge results (F_avg, F_s1, F_s2, F_s3):
0.419 0.122 0.172 0.964

Done!
```

The ranking metric for the challenge is the average of the overall
F-score values obtained in each of the three setups (in the above
example, `0.419 = (0.122 + 0.172 + 0.964) / 3`. In the case of the
tie, the overall F-score from Setup 1 is used as the tie-breaker
(in the above example, `0.122`).


### 5. Prepare submission

Having obtained the results, you can prepare the submission archive.
To do so, use the `macvi-usv-odce-tool` and `prepare-submission`
command. Its behavior is similar to the `evaluate` command, except
that it requires an additional argument - the path to the source
code of the algorithm, which needs to be supplied as part of the
submission.

The tool performs the evaluation, and generates the archive that
contains raw detection results (the results JSON file that was used
for evaluation), the evaluation results, and the collected source code.

If the source code path points to a directory, its contents are
recursively collected into the submission archive. If the source code
path points to a file (a single-file source, or a pre-generated archive
containing the whole source code), the file is collected into archive
as-is.

To continue the example from the previous step, assuming that your
current working directory contains unpacked MODS dataset in `mods`
sub-directory, the results JSON file called `results.json`, and source
code archive called `source-code.zip`, run:

```
macvi-usv-odce-tool prepare-submission mods/mods.json results.json sample-code.zip
```

The output of the tool should look similar to:

```
MaCVi USV Obstacle Detection Challenge Evaluation Toolkit

Settings:
 - mode: 'prepare-submission'
 - dataset JSON file: 'mods/mods.json'
 - results JSON file: 'results.json'
 - source code path: 'sample-code.zip'
 - output file: 'submission.zip'

Evaluating Setup 1...
Evaluation complete in 13.08 seconds!
Evaluating Setup 2...
Evaluation complete in 12.17 seconds!
Evaluating Setup 3...
Evaluation complete in 14.96 seconds!

Results: F_all F_small F_medium F_large
Setup_1: 0.122 0.065 0.209 0.260
Setup_2: 0.172 0.090 0.385 0.522
Setup_3: 0.964 0.976 0.958 0.968

Challenge results (F_avg, F_s1, F_s2, F_s3):
0.419 0.122 0.172 0.964

Preparing submission archive 'submission.zip'...
Collecting raw results file 'results.json'...
Collecting evaluation results file...
Collecting source code from 'sample-code.zip'...

Done!
```

and the tool should generate a file called `submission.zip˙ in the
current working directory.

To use a different name or a different target directory, you can provide
a custom path via the `--output-file <filename>` command-line argument.


### 6. Submit the archive

Once the submission archive is generated, you can submit it on the
challenge's web page.

Once the archive is submitted, the submission server backend will
unpack the archive's contents using the `unpack-submission` command,
and (optionally) re-evaluate the results using the local copy of the
toolkit and the dataset annotations.
