"""Video Dynamic Optimizer
<Long description>
Author: Chemin Davide <mail>
Created: 13 Oct 2022
"""

import os #to access system folders
import sys #to exit the process
import subprocess #to access ffmpeg in the system
import shutil #to remove directories
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
from scipy.optimize import curve_fit #to fit points along a curve
import json #to handle json files
import tkinter as tk #to import files
from tkinter import filedialog #to open import dialog box

#custom import
import global_
import fx
import bf
import lg
import cf

# -----------------------------------------------------------------------------
#                               Init variables
# -----------------------------------------------------------------------------

#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)
    
#encoding paramethers
PARAM_AVC = {"crfs": 52, "opr_range": [0,51], "lib": "libx264", "container": "mp4", "add_param": ""}
PARAM_HEVC = {"crfs": 52, "opr_range": [0,51], "lib": "libx265", "container": "mp4", "add_param": "-x265-params log-level=none"}
PARAM_VP9 = {"crfs": 64, "opr_range": [0,63], "lib": "libvpx-vp9", "container": "webm", "add_param": "-b:v 0"} 
target_list = {"dist": config["OPT"]["DIST_TARGETS"], "rate": (np.array(config["OPT"]["RATE_TARGETS"])*1000).tolist()}

#input file
root = tk.Tk()
root.withdraw()
source_path = os.path.relpath(filedialog.askopenfilename())
source_name = os.path.basename(source_path).split('.')[0]
if config["DEBUG"]["ENC"]:
    [os.remove(config["DIR"]["REF_PATH"] + f) for f in os.listdir(config["DIR"]["REF_PATH"])] #clean temp_refs folder
    [shutil.rmtree(config["DIR"]["DIST_PATH"] + f) for f in os.listdir(config["DIR"]["DIST_PATH"])] #clean temp_encoded folder

#assessment files path
tm_file = "config/template.json"
rd_file = "tests_rd/" + source_name + ".json"
if not os.path.isfile(rd_file): #if file does not exists create it
    with open(rd_file, 'w') as f:
        pass

#all computed points, by row: crf, bitrate and distortion metric
str_matrix = {"crf": None, "rate": None, "dist": None}


# -----------------------------------------------------------------------------
#                              Methods
# -----------------------------------------------------------------------------

def init_res_matrix(x):
    """
    Create the RD empty base matrix

    Input:
    - x : int
        Number of CRF points
    """
    str_matrix["crf"] = np.zeros(x, dtype=int).tolist()
    str_matrix["rate"] = np.zeros(x, dtype=int).tolist()
    str_matrix["dist"] = np.zeros(x).tolist()

def shot_change_detection(p):
    """
    Detect shot changes in the scene and split it into shots

    Input:
    - p : string
        File path
    Output:
    - n : int
        Number of scenes
    """
    print("-analyse: detecting shots...")
    TIME_LOGS = "config/tmp_shot_dect_" + global_.id_exe + ".log"
    with open(TIME_LOGS, 'w') as f: #create times log file
        pass
    start_t = end_t = 0.0
    #return when the shot changes
    det = f"ffmpeg -i {p} -hide_banner -loglevel error -filter_complex:v \
    \"select='gt(scene,{config['OPT']['SHOT_DETECT_TH']})',metadata=print:file={TIME_LOGS}\" -f null -"
    subprocess.call(det, shell=True)
    
    with open(TIME_LOGS, 'r') as r:
        tm_log = r.read().splitlines()[::2]
    tm_log.append("end pts_time:" + str(global_.duration))
    for i,l in enumerate(tm_log): #for each cut
        #create a folder for each scene
        new_dir = str(i)
        new_path = os.path.join(config["DIR"]["DIST_PATH"], new_dir)
        os.mkdir(new_path)
        
        #cut the video
        end_t = l.split("pts_time:",1)[1]
        if p.endswith(".yuv") or p.endswith(".y4m"):
            cut = f"ffmpeg -ss {start_t} -to {end_t} -i {p} -hide_banner -loglevel error\
            -pix_fmt yuv420p {config['DIR']['REF_PATH']}scene{str(i).zfill(7)}.yuv"
        else:
            cut = f"ffmpeg -ss {start_t} -to {end_t} -i {p} -hide_banner -loglevel error\
            -c copy -copyts {config['DIR']['REF_PATH']}scene{str(i).zfill(7)+p[-4:]}"
        subprocess.call(cut, shell=True)
        start_t = end_t
    print("-analyse: " + str(i+1) + " detected shots")
    return i+1

def save_opt(i, t, opt):
    """
    Store final results optimized back to the json file

    Input:
    - i : int
        Shot index
    - t : string
        Target name
    - opt : int
        Optimal CRF value for the current shot
    """
    global_.data["shots"][i]["opt_points"][t]["crf"] = int(opt)
    with open(rd_file, 'w') as w:
        json.dump(global_.data, w, separators=(',',': '))

def interval(l,n):
    """
    Split an interval (l[0],l[1]) into n values

    Input:
    - l : list(2)
        Boundaries of the interval to split
    - l : int
        Number of sub-intervals to define
    Output:
    - out : np.array(n+1)
        Array of CRFs values
    """
    w = (l[1] - l[0]) / (n - 1)
    return np.array([round(l[0]+i*w) for i in range(n)])

def mux(t_i, t_n, t_v):
    """
    Muxing of the all single optimal encoded shots

    Input:
    - t_i : index
        Target index
    - t_n : string
        Current target type
    - t_v : int
        Current target value
    """
    if t_n == "dist":
        t_n = config["OPT"]["DIST_METRIC"]
        if config["OPT"]["DIST_METRIC"] == "vmaf":
            out_name = str(100 - t_v).zfill(len(str(target_list[t_name][-1])))
    elif t_n == "rate":
        out_name = str(int(t_v / 1000)).zfill(len(str(target_list[t_name][-1])) - 3)
    
    file_list = "" #list of encoded vids to be stored in shot_list file
    with open(rd_file, 'r') as f:
        global_.data = json.load(f)
    for shot in range(0,global_.num_shots):
        opt_crf = global_.data["shots"][shot]["opt_points"][t_i]["crf"]
        file_list = file_list + "file '../" + config["DIR"]["DIST_PATH"] + str(shot) + "/" \
        + str(opt_crf) + "_" + config["ENC"]["CODEC"].upper() + "." + global_.s_cod["container"] + "' \n"
    with open("config/tmp_shot_list_" + global_.id_exe + ".txt", 'w') as w:
        w.write(file_list)
    o = config["DIR"]["OUT_PATH"] + source_name[:9] + "_" + t_n + out_name \
        + config["OPT"]["OPT_METHOD"] + "_" + config["ENC"]["CODEC"].upper() + "." + global_.s_cod["container"]
    mux = f"ffmpeg -f concat -safe 0 -i {'config/tmp_shot_list_' + global_.id_exe + '.txt'} \
        -c copy {o} -hide_banner -loglevel error"
    print("-mux: " + o)
    subprocess.call(mux, shell=True)
    

# -----------------------------------------------------------------------------
#                       Init and shot detection
# -----------------------------------------------------------------------------

#init folders and files check
#if not os.path.isfile(rd_file):

if source_path.endswith(".yuv"):
    print("-input: yuv")
elif source_path.endswith(".y4m"):
    print("-input: y4m")
else:
    print("-input: not rawvideo")
    
#init values based on the selected output codec
if config["ENC"]["CODEC"] == "avc":
    global_.s_cod = PARAM_AVC
    init_res_matrix(PARAM_AVC["crfs"])
elif config["ENC"]["CODEC"] == "hevc":
    global_.s_cod = PARAM_HEVC
    init_res_matrix(PARAM_HEVC["crfs"])
elif config["ENC"]["CODEC"] == "vp9":
    global_.s_cod = PARAM_VP9
    init_res_matrix(PARAM_VP9["crfs"])
else:
    print("ERROR: not a codec")
    sys.exit()

#init checks
if config["ENC"]["NUM_PTS"] > config["ENC"]["CRF_RANGE"][1] - config["ENC"]["CRF_RANGE"][0] + 1:
    print("ERROR: too many encodings")
    sys.exit()
if config["ENC"]["CRF_RANGE"][0] > config["ENC"]["CRF_RANGE"][1]:
    print("ERROR: wrong CRF range")
    sys.exit()
if config["ENC"]["CRF_RANGE"][0] < global_.s_cod["opr_range"][0] or \
   config["ENC"]["CRF_RANGE"][1] > global_.s_cod["opr_range"][1]:
    print("ERROR: CRF out of range")
    sys.exit()
    
#get the total duration for the last cut
idu = f"ffprobe -v error -select_streams v:0 -show_entries format:stream \
    -print_format json {source_path} -hide_banner -loglevel error"
dta = json.loads(subprocess.run(idu.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
global_.duration = float(dta['format']['duration'])

if config["DEBUG"]["ENC"]:

    struct_points = [] #structure of target points for the json file
    struct_shots = [] #structure of shots for the json file

    with open(tm_file, 'r') as f:
        global_.data = json.load(f)

    #add source name and results matrix
    global_.data["content"] = source_name
    global_.data["codec"] = config["ENC"]["CODEC"]
    global_.data["width"] = config["ENC"]["WIDTH"]
    global_.data["height"] = config["ENC"]["HEIGHT"]
    global_.data["fps"] = config["ENC"]["FPS"]
    global_.data["shots"][0]["assessment"] = str_matrix
    
    global_.num_shots = shot_change_detection(source_path)

    #add emplty target points
    base_point = global_.data["shots"][0]["opt_points"][0]
    for t_name in target_list:
        for t_val in target_list[t_name]:
            base_point["metric"] = t_name
            base_point["target"] = t_val
            struct_points.append(copy.deepcopy(base_point))
    global_.data["shots"][0]["opt_points"] = struct_points

    #add empty shots
    base_shot = global_.data["shots"][0]
    for i in range(0, global_.num_shots):
        base_shot["index"] = i #assign index to shots in json file
        struct_shots.append(copy.deepcopy(base_shot))
    global_.data["shots"] = struct_shots

    with open(rd_file, 'w') as w:
        json.dump(global_.data, w, separators=(',',': '))
else:
    with open(rd_file, 'r') as f:
        global_.data = json.load(f)
    global_.num_shots = len(global_.data["shots"])
    
if config["OPT"]["DIST_METRIC"] == "vmaf":
    target_list["dist"] = 100 - np.asarray(target_list["dist"])
elif config["OPT"]["DIST_METRIC"] == "psnr":
    print("not yet implemented")
    #TODO normalize psnr and set a max
    sys.exit()
else:
    print("ERROR: not a target")
    sys.exit()
    
print("-init: done")

# -----------------------------------------------------------------------------
#                              Exe
# -----------------------------------------------------------------------------

target_index = 0
for t_name in target_list:
    for t_val in target_list[t_name]:
        
        global_.npts = interval(config["ENC"]["CRF_RANGE"], config["ENC"]["NUM_PTS"]).tolist()
        
        if config["OPT"]["OPT_METHOD"] == "fx": #brute force approach
            opt = fx.run(target_index, t_name, t_val)
            print("-out: crfs " + str(opt))
            
        elif config["OPT"]["OPT_METHOD"] == "bf": #brute force approach
            opt = bf.run(target_index, t_name, t_val)
            print("-out: crfs " + str(opt))
            
        elif config["OPT"]["OPT_METHOD"] == "lg": #lagrangian optimization
            opt = lg.run(target_index, t_name, t_val)
            print("-out: crfs " + str(opt))
        
        elif config["OPT"]["OPT_METHOD"] == "cf": #curve fitting
            opt = cf.run(target_index, t_name, t_val)
            print("-out: crfs " + str(opt))
            if config["DEBUG"]["MUX"]:
                #do not override, skip the encoding instead, if the file already exists
                global_.s_cod["add_param"] = global_.s_cod["add_param"] + " -n"
                print("-encode: encoding in-between points...")
                shot_index = 0
                for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
                    out = global_.encode(shot, shot_index, opt[shot_index]) #encoding
                    shot_index += 1
                
        else:
            print("ERROR: not an opt method")
            sys.exit()

        if config["DEBUG"]["MUX"]:
            for i in range(0,global_.num_shots): #save the opt crf for each shot
                save_opt(i, target_index, opt[i])
            mux(target_index, t_name, t_val)
        
        target_index += 1

if config["DEBUG"]["DEL"]: #delete temp files
    os.remove("config/tmp_shot_dect_" + global_.id_exe + ".log")
    os.remove("config/tmp_vmaf_log_" + global_.id_exe + ".json")
    os.remove("config/tmp_shot_list_" + global_.id_exe + ".txt")