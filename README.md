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

Before executing the code always remember to run it inside of the installed virtual environment.
```bash
#when the environment is installed but not active
source env/bin/activate
```

## Usage

#### 1. Before running the code, configure settings in [config.json](config/config.json)

* These are the encoding variables you can configure:
    * `"CODEC" [string]` : output codec
        - values: "avc", "hevc", "vp9", !!not implemented: "av1", "vvc"
    * `"WIDTH" [int]` : input and output width
        - ex.1920
    * `"HEIGHT" [int]` : input and output height
        - ex.1080
    * `"FPS" [float]` : input and output frame rate
        - ex.29.97
    * `"CRF_RANGE" [list(2)]` : CRF encoding range
        - ex.[10,40]
    * `"NUM_PTS" [int]` : number of encodings or points per shot, more for more precision
        - ex.10 in the interval [10,40]

* These are the optimization settings you can configure
    * `"DIST_TARGETS [list(N)]"` : list of quality targets
        - ex.[75,90] - a value between 0 and 100 in case of VMAF, also empty
    * `"RATE_TARGETS" [list(N)]` : list of bitrate targets
        - ex.[5000000] - also empty
    * `"DIST_METRIC" [string]` : quality metric
        - values "vmaf" !!not implemented: "psnr","ssim", "mssim"
    * `"OPT_METHOD" [string]` : optimization method
        - values: fx = fixed CRF, bf = brute force, lg = lagrange, cf = curve fitting
    * `"SHOT_DETECT_TH" [float]` : shot detection threshold
        - ex.0.25
        
* In the DIR section you can also change directories and files paths.

* Debug settings:
    * `"ENC" [boolean]` : do not encode shots, proceed only with computations
        - False when you have all the shots already encoded and assessed
    * `"MUX" [boolean]` : do not create the final optimized version
        - False when no video output is needed

#### 2. Run the main script:
```bash
python3 code/main.py
```

#### 3. Select from the dialogue box the video to input.
Supported formats:
* `.yuv`: raw video
* `.y4m`: raw video

The support of any other input format and codec, like `.mp4` or `AVC`, depends on ffmpeg installation.

#### 4. Output
Results will be displayed in the console.
Optimal encoded videos are stored in the specified folder.

## Directory tree
```bash
__code/
____ bf.py #brute force code
____ cf.py #curve fitting implementation
____ fx.py #brute force code
____ global_.py #global variables and methods
____ lg.py #lagrange method
____ main.py

__config/
____ config.json #config file
____ shot_detection.log #timestamps of the shots in the scene
____ shot_list.txt #file list of encoded shots to merge
____ template.json #RD results structure
____ vmaf_logs.json #VMAF library results

__env/ #virtual environment with required modules

__tests_rd/ #plots and json files to store CRF, distortion and rate values for later uses

__tests_vids/ #raw input files, temporary encoded shots, optimized output videos
```
