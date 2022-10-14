# video_dynopt_thesis

Dynamic vido optimization based on Quality and Rate targets.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install required modules.
Run the following code in the root of your working directory:

```bash
#install virtual environment
python3 -m venv env

#activate the environment
source env/bin/activate

#install required modules
python3 -m pip install -r requirements.txt
```
Your system must have installed also:
* [ffmpeg](https://ffmpeg.org/download.html)
* [ffmpeg dependencies](https://ffmpeg.org/download.html) if not already installed:
    - libx264 AVC video encoder
    - libx265 HEVC video encoder
    - libvpx VP9 video encoder
    - libvmaf VMAF library

Execute the code from your working directory to run main.py inside the installed environment:
```bash
#when the environment is installed but not active
source env/bin/activate

#run code
python3 code/main.py
```

## Usage

#### 1. Before running the code, configure settings in `config/config.json`

* These are the encoding variables you can configure:
    * `"CODEC" [string]` : output codec
        - values: "avc", "hevc", "vp9", !!not implemented: "av1", "vvc"
    * `"WIDTH" [int]` : input and output width
    ex.1920
    * `"HEIGHT" [int]` : input and output height
    ex.1080
    * `"FPS" [float]` : input and output frame rate
    ex.29.97
    * `"CRF_RANGE" [list(2)]` : CRF encoding range
    ex.[10,40]
    * `"NUM_INTERVALS" [int]` : number of CRF or points per interval, more for more precision
    ex.10 the interval [10,40] is splitted into 10 intervals (N+1 CRF points)

* These are the optimization settings you can configure
    * `"DIST_TARGETS [list(N)]"` : list of quality targets
        ex.[75,90] - a value between 0 and 100 in case of VMAF, also empty
    * `"RATE_TARGETS" [list(N)]` : list of bitrate targets
        ex.[5000000] - also empty
    * `"DIST_METRIC" [string]` : quality metric
        values "vmaf" !!not implemented: "psnr","ssim", "mssim"
    * `"OPT_METHOD" [string]` : optimization method
        values: #bf = brute force, lg = lagrange, cf = curve fitting
    * `"SHOT_DETECT_TH" [float]` : shot detection threshold
        ex.0.25
        
* In the DIR section you can configure also directories and files paths.

#### 2. Run the main script:
```bash
python3 code/main.py
```

#### 3. Select from the dialogue box the raw video to input.
Results will be displayed in the console. Optimal encoded videos are stored in the specified folder.

## How it works