# Dynopt

Dynamic video optimization based on quality and rate targets.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install required modules.
Run the following code in the root of your working directory:

```bash
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


## Usage


#### Run [main.py](code/main.py) script

```bash
python3 code/main.py <custom_parameters>
```


#### Custom parameters

* Mandatory:
    * `-i [string]` : input file path, absolute or relative
        - ex. test_vids/test.y4m or /home/ubuntu/dynopt/test_vids/test.y4m
    * `-d [list(N)]` : list of quality targets, not mandatory or empty if at least one bitrate target is specified
        - ex. [40,50,60,75,80,85,90,93,96] - a value between 0 and 100 in case of VMAF
        - ex. [30] - a value between 0 and 60 in case of PSNR
    * `-r [list(N)]` : list of bitrate targets in kbps, not mandatory or empty if at least one quality target is specified
        - ex. [100,250,500,1000]
    * `-c [float]` : output codec, it also depends on the FFmpeg intallation
        - values: avc, hevc, vp9, av1

* Optional:
    * `-o [string]` : output folder, absolute or relative
        - ex. opt_vids/ or /home/ubuntu/dynopt/opt_vids/
        - if not specified, the system will print RD results in the console instead of muxing the final file
    * `-m` : optimization method
        - values: fx, bf, lg, cf
        - DEFAULT: lg
    * `--range [list(2)]"` : CRF encoding range
        - ex. [10,40] or [15,35]
        - DEFAULT: range of CRF values supported by the encoder, excluding the lossless option
    * `--pts [int]` : number of encodings or points per shot, more for more precision
        - ex. 10
        - DEFAULT: all possible points in the specified range
    * `--dmetric [string]` : quality metric used for optimization
        - values: vmaf, psnr
        - DEFAULT: vmaf
    * `--dth [float]` : shot detection threshold
        - values: a value in between 0 and 1
        - DEFAULT: 0.25
    * `-h or --help` : get help
        
* Mandatory only for .yuv input:
    * `--ires [int]x[int]` : input and output height
        - ex. 1920x1080
    * `--ifps [float]` : input and output frame rate
        - ex. 29.97
    * `--ipx_fmt [string]` : pixel format
        - ex. yuv420p

* Debug parameters:
    * `--skip` : do not encode shots, proceed only with computations
        - Use this when you already have RD results stored in a JSON file
    * `--keep` : do not delete elemental encodes and temporary files in the temp folder when code has finished running
        - Use this when you still need encoded shots after execution

* Directories:
    To change folder pathes please modify the values in [main.py](code/main.py). Your can change directories for the following folders:
    * `p_elemental_encodes` : encoded shots folder
        - In this folder the same number of folders as the number of shots will be created. Inside each one you will find a number of elemental encodes per shot as specified in `--pts` parameter.
    * `p_rd_log` : optional JSON output folder with RD results
        - You can store RD results in a JSON file in order to avoid to encode again all shots in the next execution, when inputting the same sequence, and for debugging purposes.


#### Examples
Input .yuv test sequence, optimized with Curve Fitting method in the AV1 range [25,55] at 5 CRF points per shot, only with quality targets.
```bash
python3 code/main.py -i test.yuv --ires 1920x1080 --ifps 25 --px_fmt yuv420p -d [40,50,60,70,80,85,90,95] -c av1 --range [25,55] --pts 5 -m cf -o test/optimized/
```

Input .y4m test sequence, optimized with Lagrangian method in the whole range of AVC at 26 points with both rate and quality targets measured with PSNR.
```bash
python3 code/main.py -i test.y4m -r [500,1000,1500,2000] -d [28,30,32,34] --dmetric psnr -c avc --pts 26 -m lg -o test/optimized/
```

Input .y4m test sequence already optimized in a previous execution, without generating any output file besides the RD results printed in the console.
```bash
python3 code/main.py -i test.y4m -r [1000,2000,3000,5000] -d [60] -c avc --pts 26 -m lg --skip
```
**Remember.** If you want to run optimization without re-encoding, you first have to run the scrit with `--keep` and set a folder in the `p_rd_log` variable. Then, you can run the next script with `--skip --keep` as much as you like.



## Directory tree
```bash
__code/
____ bf.py #brute force script
____ cf.py #curve fitting script
____ fx.py #brute force script
____ global_.py #global variables and methods
____ lg.py #lagrangian method script
____ main.py

__config/ #temporary files
____ tmp_shot_dect.log #timestamps of the shots in the scene
____ tmp_shot_list.txt #file list of encoded shots to merge
____ tmp_vmaf_log.json #VMAF library results

__env/ #virtual environment with required modules
```
