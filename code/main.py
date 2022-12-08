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
PARAM_AVC = {"crfs": 52, "opr_range": config["ENC"]["CRF_RANGE"], "lib": "libx264", "container": "mp4", "add_param": ""}
PARAM_HEVC = {"crfs": 52, "opr_range": config["ENC"]["CRF_RANGE"], "lib": "libx265", "container": "mp4", "add_param": ""}
PARAM_VP9 = {"crfs": 64, "opr_range": config["ENC"]["CRF_RANGE"], "lib": "libvpx-vp9", "container": "webm", "add_param": "-b:v 0"} 

target_list = {"dist": config["OPT"]["DIST_TARGETS"], "rate": config["OPT"]["RATE_TARGETS"]}
dist_metric = config["OPT"]["DIST_METRIC"]
opt_type = config["OPT"]["OPT_METHOD"]

#input file
root = tk.Tk()
root.withdraw()
source_path = os.path.relpath(filedialog.askopenfilename())
source_name = os.path.basename(source_path).split('.')[0]
ref_path = config["DIR"]["REF_PATH"]
dist_path = config["DIR"]["DIST_PATH"]
if global_.new_enc:
    [os.remove(ref_path+f) for f in os.listdir(ref_path)] #clean temp_refs folder
    [shutil.rmtree(dist_path+f) for f in os.listdir(dist_path)] #clean temp_encoded folder

#assessment files path
tm_file = "config/template.json"
rd_file = "tests_rd/" + source_name + ".json"
if not os.path.isfile(rd_file): #if file does not exists create it
    with open(rd_file, 'w') as f:
        pass

#shot detection
TIME_LOGS = "config/" + config["DIR"]["TIME_LOGS"]
shot_th = config["OPT"]["SHOT_DETECT_TH"] #change shot threshold

#output file
OUT_LIST = "config/" + config["DIR"]["OUT_LIST"]
OUT_PATH = config["DIR"]["OUT_PATH"]

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
        File
    Output:
    - n : int
        Number of scenes
    """
    print("-analyse: detecting shots...")
    start_t = 0.0
    end_t = 0.0
    #return when the shot changes
    det = f"ffmpeg -i {p} -hide_banner -loglevel error -filter_complex:v \"select='gt(scene,{shot_th})', \
        metadata=print:file={TIME_LOGS}\" -f null -"
    subprocess.call(det, shell=True)
    
    with open(TIME_LOGS, 'r') as r:
        tm_log = r.read().splitlines()[::2]
    tm_log.append("end pts_time:" + str(global_.duration))
    n = len(tm_log)
    for i,l in enumerate(tm_log): #for each cut
        #create a folder for each scene
        new_dir = str(i)
        new_path = os.path.join(dist_path, new_dir)
        os.mkdir(new_path)
        
        #cut the video
        end_t = l.split("pts_time:",1)[1]
        cut = f"ffmpeg -ss {start_t} -to {end_t} -i {p} -hide_banner -loglevel error\
            -pix_fmt yuv420p {ref_path}scene{str(i).zfill(7)}.yuv"
        subprocess.call(cut, shell=True)
        start_t = end_t
    print("-analyse: " + str(n) + " detected shots")
    return n

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
        t_n = dist_metric
        if dist_metric == "vmaf":
            t_v = 100 - t_v
    file_list = "" #list of encoded vids to be stored in OUT_LIST
    with open(rd_file, 'r') as f:
        global_.data = json.load(f)
    for shot in range(0,global_.num_shots):
        opt_crf = global_.data["shots"][shot]["opt_points"][t_i]["crf"]
        file_list = file_list + "file '../" + dist_path + str(shot) + "/" \
        + str(opt_crf) + "_" + config["ENC"]["CODEC"].upper() + "." + global_.s_cod["container"] + "' \n"
    with open(OUT_LIST, 'w') as w:
        w.write(file_list)
    o = OUT_PATH+source_name[:9] + "_" + t_n + str(t_v).zfill(len(str(target_list[t_name][-1]))) + opt_type +\
        "_" + config["ENC"]["CODEC"].upper() + "." + global_.s_cod["container"]
    mux = f"ffmpeg -f concat -safe 0 -i {OUT_LIST} -c copy {o} -hide_banner -loglevel error"
    print("-mux: " + o)
    subprocess.call(mux, shell=True)
    

# -----------------------------------------------------------------------------
#                       Init and shot detection
# -----------------------------------------------------------------------------

if source_path.endswith(".yuv"):
    print("-input: yuv")
elif source_path.endswith(".y4m"):
    print("-input: y4m")
else:
    print("ERROR: not an input type")
    sys.exit()
    
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

if config["ENC"]["NUM_INTERVALS"] > global_.s_cod["opr_range"][1] - global_.s_cod["opr_range"][0]:
    print("ERROR: too many encodings")
    sys.exit()
if global_.s_cod["opr_range"][0] > global_.s_cod["opr_range"][1]:
    print("ERROR: wrong CRF range")
    sys.exit()
    
#get the total duration for the last cut
idu = f"ffprobe -v error -select_streams v:0 -show_entries format:stream \
    -print_format json {source_path} -hide_banner -loglevel error"
dta = json.loads(subprocess.run(idu.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
global_.duration = float(dta['format']['duration'])

if global_.new_enc:

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
    
if dist_metric == "vmaf":
    target_list["dist"] = 100 - np.asarray(target_list["dist"])
elif dist_metric == "psnr":
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
        
        global_.npts = interval(global_.s_cod["opr_range"], config["ENC"]["NUM_INTERVALS"]).tolist()
        
        if opt_type == "fx": #brute force approach
            opt = fx.run(target_index, t_name, t_val)
            
        elif opt_type == "bf": #brute force approach
            opt = bf.run(target_index, t_name, t_val)
            
        elif opt_type == "lg": #lagrangian optimization
            opt = lg.run(target_index, t_name, t_val)
        
        elif opt_type == "cf": #curve fitting
            opt = cf.run(target_index, t_name, t_val)
            shot_index = 0
            for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
                out = global_.encode(shot, shot_index, opt[shot_index]) #encoding
                shot_index += 1
                
        else:
            print("ERROR: not an opt method")
            sys.exit()
        
        print("-out_crfs= " + str(opt))
        for i in range(0,global_.num_shots): #save the opt crf for each shot
            save_opt(i, target_index, opt[i])

        mux(target_index, t_name, t_val)
        
        target_index += 1