# CentTracker
A trainable, machine learning-based tool for large-scale analyses of intravital imaging of *C. elegans* germline stem cell mitosis.

<!--- # The full description of CentTracker and its application on live imaging microscopy datasets are available in ... (to be added once on bioarxiv).
-->
This repository includes detailed instructions for installation, requirements, demos for single movie as well as batch processing.



## Contents ##

1. [Pipeline overview](#overview)
2. [Installation](#installation)
3. [Usage](#usage)
  - [Module 1: Registration](#registration)
  - [Module 2: Tracking](#tracking)
  - [Module 3: Track pair classificatino](#tpc)
  - [Module 4: Cell scoring](#scoring)
4. [The trainable option](#trainable)


<a name="overview"></a>
## 1 Pipeline overview
- TODO: add the model figure and caption from manuscript (REDA or YIFAN)

<a name="installation"></a>
## 2 Installation

### Install Conda
1. Install conda. Detailed installation instructions can be found [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/). Now, check if conda is installed and in your PATH by
  - Open a terminal client.
  - Enter ```conda -V``` into the terminal command line and press enter. If conda is installed you should see something like the following:
```
$ conda -V
conda 4.9.0
```
2. Create and activate a virtual environment, by entering
```
$ conda create -n "mitosis" python=3.8.5
$ conda activate mitosis
```
Please see [here](https://docs.python.org/3/tutorial/venv.html) for why we need virtual environment.

Note that everytime you need to use CentTracker, you will need to enter ```conda activate mitosis``` in the terminal.
Example
```
$ conda activate mitosis
$ cd CentTracker-master
$ jupyter notebook
```


### Clone this repository, either by GitHub desktop, direct download, or by entering the following in the terminal
```
$ cd CentTracker-master
$ pip install -r requirements.txt
$ conda install scikit-image==0.15.0
```

### Install MATLAB 2020b
https://www.mathworks.com/products/matlab.html

### Install Fiji
Detailed instructions can be found [here](https://imagej.net/Fiji). The version used for our experiments is 1.52v.


<a name="usage"></a>
## 3 Usage

<a name="registration"></a>
### Module 1: Registration
#### 1. Create a x-y translation matrix.
Pre-requisite:
Group your original movies that are under the same conditions in the same folder and assign each of them a folder labeled with their name without extension.
Example :
```
Controls/
├── 2018-01-16_GSC_L4_L4440_RNAi_1
│   └── 2018-01-16_GSC_L4_L4440_RNAi_1.tif
├── 2018-01-16_GSC_L4_L4440_RNAi_2
│   └── 2018-01-16_GSC_L4_L4440_RNAi_2.tif
└── 2018-01-16_GSC_L4_L4440_RNAi_3
    └── 2018-01-16_GSC_L4_L4440_RNAi_3.tif
```

1. Open Fiji, drag and drop automatedregistrationtool.ijm then run it.
2. First window will ask you for the original movies directory ( according to the example, it would be the “Controls” folder.
3. First movie in your folder will open and channels will be splitted if your movie has more than 1 channel, a window will then ask you to select the centrosomes channel.
4. A max z-projection of your movie will then be generated, ROI Manager will open and a window prompting “click when done tracking”, do not click on done until step 7 is done.
5. Look for a pair of prominently congressing centrosomes. You might need to watch the movie a few times to identify such a pair. But it gets very easy with a little practice.
6. At t = 0, draw a straight line in the middle of the two centrosomes that you identified in the previous step. This line should approximate the metaphase plate (see Figure 1). Then, enter "t" on your keyboard (shortcut for "Add" in ROI manager).
7. Go to the next time point. If the metaphase plate position changes, move your line accordingly using "->" or "<-" on your keyboard. Enter "t" to add the line. Repeat this step until the last time point is reached or the metaphase plate for this cell cannot be tracked accurately anymore then click on done.
8. A window will ask you if you need to "track an additional cell ?", click Yes if the metaphase plate tracking did not reach the last time point. Repeat then step 5 to 7 but starting at the last time point tracked and looking for a new pair of centrosomes. Repeat this step as long as you did not reach the last time point, there is no limit of additional cells then click on No for "track an additional cell ?".
![Figure 1](https://github.com/yifnzhao/Semi-automated-GSC-registration/blob/master/figures/Figure%202.png)


#### 2. Register
- To open a jupyter notebook, simply enter the following in the terminal
```
$ conda activate mitosis
$ jupyter notebook
```
which should open in your default web browser.

- For single movie, a jupyter notebook with detailed instructions can be found [here](/src/singlemovie.ipynb).
- For batch mode, a jupyter notebook with detailed instructions can be found [here](/src/batchmode.ipynb).

<a name="tracking"></a>
### Module 2: Tracking
- TrackMate is our recommended software. Detailed installation and usage instructions can be found [here](https://imagej.net/TrackMate).
1. Open Fiji, drag and drop automatedfixhyperstack.ijm then run it.
2. First window will ask you for the original movies directory (according to the example, it would be the “Controls” folder. At this stage each movie subfolder should contain the original movie, the registered movie starting with “r_” and a subfolder “roi”.
3. First original movie will open in the background to extract dimensions then registered movie will open with correct dimensions.
4. A window will then ask you to draw a rectangle around the border of your movie reducing the best possible the surrounding extra borders resulting from registration then click on Done.
5. A window asking to "generate a .xml using Trackmate" will prompt (do not click on done until step 5 completion) and Trackmate window will open, then click on next. Select LoG detector then click on next. Choose the channel of centrosomes. We used 2.5 microns for GSCs centrosomes estimated blob diameter and lowered the threshold until all centrosomes were detected (important step ! use button preview to ensure that all centrosomes were detected), it does no matter if some spurious spots were also detected. Click on next 6 times until linking max distance is asked. We used for GSCs centrosomes 2.7  microns for linking max distance, gap closing max distance and we used 2 for Gap-closing max frame gap. Click next 2 times until the display options window appear and then click on save and save the Trackmate output ( a .xml file) in same folder as your registered movie and ensure that that file is labeled the same as the registered movie.
5. Click on done when done generating the xml.


<a name="tpc"></a>
### Module 3: Track pair classification
- For single movie, a jupyter notebook with detailed instructions can be found [here](/notebooks/singlemovie.ipynb).
- For batch mode, a jupyter notebook with detailed instructions can be found [here](/notebooks/batchmode.ipynb).


<a name="scoring"></a>
### Module 4: Cell scoring
1.  Open Matlab and run Step1_import_textfile_and_align_cent_tracks.m that will import the tracking output to Matlab. A window will ask you to select the folder containing your movies ( according to the example, it would be the “Controls” folder) and the script will generate 2 additional txt files per movie with the coordinates of the spindle midpoint that will be use as an input for fiji macro Step2_CropCells_.ijm.
2. Open fiji, run Step2_CropCells_.ijm, a window will ask you to select the folder containing your movies ( according to the example, it would be the “Controls” folder) when script is done, return to Matlab.
3. Run Step3_score_mitosis.m. This script will then plot each cell spindle length versus time. It will allows you to score NEBD and the start and end of congression by clicking on the graph of spindle length versus time for each cell by positioning the cross hairs and click to select the nearest x-coordinate (i.e. frame) for NEBD, congression start (CongS) and congression end (CongE), in that order. If an event occurs before or after the end of the timelapse (e.g. before frame 1 or after frame 80), click to the left or right of the graph (outside of its borders), respectively.
4. If the graph is unclear, click any keyboard button to open a cropped, max projection of the cell in question (this step will allow you to verify if the centrosomes pair used for this graph is a true pair); You will be prompted to enter a frame for NEBD, CongS and CongE and these values will then be displayed on the graph to guide your selection using the cross hairs. 'If you make a mistake, take note of the cell and continue scoring.
5. When done scoring, run Step4_calc_fits.m in Matlab. This script will process the scoring and calculate the duration of congression for cells for which both the start and end of congression occurred during the image acquisition using lines of best fit, if for a cell the fitting fails or the fitting values differ of more than 2 frames from the scored values, the concerned plot will be opened again to ask to choose between scored values and fitting values.
The generated variables “GermlineOutput” and “CellOutput” contains various mitotic parameters.
6. if you want to correct or verify your scoring, run Check_fit_and_scoring.m which will plot each spindle length versus time (frames) for each cell, lines corresponding to the scored events and fitted curves obtained by Step4_calc_fits.m. Use a mouse click to pass to the next graph or click any button in your keyboard to open a cropped, max projection of the cell in question (this step will allow you to verify if the centrosomes pair used for this graph is a true pair); You will be prompted to enter a frame for NEBD, CongS and CongE and these values will then be displayed on the graph to guide your selection using the cross hairs. You can then rescore (point 3).
	

<a name="trainable"></a>
## 4 The trainable option
- These steps should be done using a folder organised as explained in the module 1 but containing only the subset of movies you desire to use for training a model
- A step-to-step walkthrough can be found [here](/notebooks/trainable.ipynb).
- About step 3 :
1. Open Fiji, drag and drop verify_true_pairs.ijm then run it.
2. First window will ask you for the “cropped tiffs” directory generated in module 4 and the original movies directory that will be used for training.
3. cropped tiff will open one by one and a window will ask if it "Is it a true pair", click yes or no accordingly.
4. When done with all cropped tiffs, a True.csv file should be find in each movie folder.


