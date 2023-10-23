


# USV Obstacle Detection Challenge Evaluation Toolkit

This repository contains source code of the evaluation toolkit for the
*USV Obstacle Detection Challenge*, hosted at the *2nd Workshop on Maritime
Computer Vision (MaCVi)* as part of the WACV2024.

The official site for the challenge can be found [here](https://macvi.org/workshop/macvi24).

The evaluation protocol is the standard IoU-based bounding box evaluation roughly based on the paper by *Bovcon et al.*:

Bovcon Borja, Muhovič Jon, Vranac Duško, Mozetič Dean, Perš Janez and Kristan Matej,
*"MODS -- A USV-oriented object detection and obstacle segmentation benchmark"*,
IEEE Transactions on Intelligent Transportation Systems, 2021.
[Pre-print version available on arXiv](https://arxiv.org/abs/2105.02359).


The evaluation code is based on the implementation provided by
the authors in https://github.com/bborja/mods_evaluation
in `object_detection` sub-directory in `bbox_obstacle_detection` branch
([here](https://github.com/bborja/mods_evaluation/tree/bbox_obstacle_detection/object_detection)).
The evaluation code for MaCVi 2024 is based on evaluation code from MaCVi 2023, written by Rok Mandeljc: https://github.com/rokm/macvi-usv-odce-toolkit.


## Getting started

### 1. Download the LaRS dataset

Download and unpack [the LaRS dataset](https://lojzezust.github.io/lars-dataset/).

### 2. Process the dataset with your detection method

Use your algorithm to process the test subset of the LaRS dataset.

For training data, you can use LaRS as well as other publicly available data to train your method. In this case, please disclose this during the submission process.

The algorithm should output the detections with rectangular axis-aligned
bounding boxes of waterborne objects. The class of the obstacle is not important and will be ignored in the evaluation process. The results should be stored in a single JSON file using the format described below.

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
python3 -m pip install git+https://github.com/JonNatanael/macvi-usv-odce-toolkit-2024.git
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

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

valid commands:
  command               command description
    evaluate (e)        Evaluate the results.
    prepare-submission (s)
                        Evaluate the results and prepare archive for
                        submission.
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

NOTE: Running the tool via the ``macvi-usv-odce-tool`` requires your
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
current working directory contains unpacked LaRS dataset in `LaRS`
sub-directory and the results JSON file called `results.json`,
run:

```
macvi-usv-odce-tool evaluate LaRS/ val results.json
```

This should run the evaluation on the validation set of the LaRS dataset. Since the test set annotations are not publicly available, empty json files for test and validation sets are provided along with the evaluation tool.

The ranking metric for the challenge is the F1 score with the IoU threshold being set at 0.3 In the case of a
tie, the threshold will be raised until the tie is broken.


### 6. Submit the archive

Having obtained the results, you can submit them on the challenge's web page.

Once the json file is submitted, the submission server backend will evaluate the results using the local copy of the
toolkit and the dataset annotations. The score will then be displayed on the leaderboard.
