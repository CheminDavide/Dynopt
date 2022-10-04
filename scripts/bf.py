# imports
import os #to access system folders
import subprocess #to access ffmpeg in the system
import shutil #to remove directories
import numpy as np #easy vector operations
import math #for operation with infinite
import itertools
import copy #dict shadow copies
from scipy.optimize import curve_fit #fittin of the curve
import json #to handle json files
import matplotlib.pyplot as pl #to display plots
import tkinter as tk #to import file
from tkinter import filedialog #to open import dialog

#constants
PARAM_AVC = {"crfs": 52, "starting_range": [15,40], "lib": "libx264", "container": "mp4", "add_param": ""}
PARAM_HEVC = {"crfs": 52, "starting_range": [15,46], "lib": "libx265", "container": "mp4", "add_param": ""}
PARAM_VP9 = {"crfs": 64, "starting_range": [15,51], "lib": "libvpx-vp9", "container": "webm", "add_param": "-b:v 0"}

#variables - CUSTOM
codec = "avc" #values: "avc", "hevc", "vp9", !!not implemented: "av1", "vvc"
raw_width = 480
raw_height = 270
raw_fps = 29.97
#values "rate","vmaf", "psnr" !!not implemented: "ssim", "mssim"
target_list = {"vmaf": [75], "rate": []}

#input file
root = tk.Tk()
root.withdraw()
source_path = os.path.relpath(filedialog.askopenfilename())
source_name = os.path.basename(source_path).split('.')[0]
REF_PATH = "test_vids/tempRAW_refs/" #raw files for each shot
[os.remove(REF_PATH+f) for f in os.listdir(REF_PATH)] #clean temp_refs folder
DIST_PATH = "test_vids/temp_encoded/" #encoded files for each shot
[shutil.rmtree(DIST_PATH+f) for f in os.listdir(DIST_PATH)] #clean temp_encoded folder

#assessment files path
tm_file = "rd_results/template.json"
rd_file = "rd_results/" + source_name + ".json"
if not os.path.isfile(rd_file): #if file does not exists create it
    with open(rd_file, 'w') as f:
        pass
VMAF_LOGS = "rd_results/vmaf_logs.json"

#shot detection
TIME_LOGS = "shot_detection.log"
shot_th = 0.25 #change shot threshold
num_scenes = 0
duration = 0.0

#output file
OUT_LIST = "shot_list.txt"
OUT_PATH = "test_vids/OPT_vids/"

#all computed points, by row: crf, bitrate, vmaf, psnr
str_matrix = {"crf": None, "rate": None, "vmaf": None, "psnr": None}

print("init done")

##--------------- FUNCTIONS ----------------##
#an empty json structure is generated to be filled and to store computed values
def init_res_matrix(x):
    str_matrix["crf"] = np.zeros(x, dtype=int).tolist()
    str_matrix["rate"] = np.zeros(x, dtype=int).tolist()
    str_matrix["vmaf"] = np.zeros(x).tolist()
    str_matrix["psnr"] = np.zeros(x).tolist()
    
#detect shot changes in the scene and split it into shots
def shot_change_detection(p):
    start_t = 0.0
    end_t = 0.0
    global duration
    #return when the shot changes
    det = f"ffmpeg -i {p} -filter_complex:v \"select='gt(scene,{shot_th})', \
        metadata=print:file={TIME_LOGS}\" -f null -"
    subprocess.call(det, shell=True)
    #get the total duration for the last cut
    idu = f"ffprobe -v error -select_streams v:0 -show_entries format:stream -print_format json {p}"
    dta = json.loads(subprocess.run(idu.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
    duration = float(dta['format']['duration'])
    
    with open("shot_detection.log", 'r') as r:
        tm_log = r.read().splitlines()[::2]
    tm_log.append("end pts_time:" + str(duration))
    n = len(tm_log)
    for i,l in enumerate(tm_log): #for each cut
        #create a folder for each scene
        new_dir = str(i)
        new_path = os.path.join(DIST_PATH, new_dir)
        os.mkdir(new_path)
        
        #cut the video
        end_t = l.split("pts_time:",1)[1]
        cut = f"ffmpeg -ss {start_t} -to {end_t} -i {p} \
            -pix_fmt yuv420p {REF_PATH}scene{str(i).zfill(7)}.yuv"
        subprocess.call(cut, shell=True)
        start_t = end_t
    return n

def encode(s,i,c):
    add_info = s_cod["add_param"]
    lib = s_cod["lib"]
    o = DIST_PATH + str(i) + "/" + str(c) + "_" + codec.upper() + "." + s_cod["container"]
    enc = f"ffmpeg -f rawvideo -video_size {raw_width}x{raw_height} -r {raw_fps} \
        -pixel_format yuv420p -i {REF_PATH + s} -c:v {lib} -crf {c} {add_info} {o} -hide_banner -loglevel error"
    subprocess.call(enc, shell=True)
    print("-encoded= " + o)
    return o

def assess(s,o):
    c_vmaf = f"ffmpeg -f rawvideo -r {raw_fps} -video_size {raw_width}x{raw_height} -i {REF_PATH + s} \
            -i {o} -hide_banner -loglevel error\
            -lavfi \"[0:v]setpts=PTS-STARTPTS[ref];\
                    [1:v]scale={raw_width}x{raw_height}:flags=bicubic, setpts=PTS-STARTPTS[dist];\
                    [dist][ref]libvmaf=feature=name=psnr:log_path={VMAF_LOGS}:log_fmt=json\" \
            -f null -" #|name=float_ssim|name=float_ms_ssim to compute the other metrics
    subprocess.call(c_vmaf, shell=True)

#store the quality and rate results for each shot at each encoded crf
def store_results(i,c,o):
    with open(VMAF_LOGS, 'r') as r: #extract quality and rate values
        i_data = json.load(r)
    o_data["shots"][i]["assessment"]["crf"][c] = c
    o_data["shots"][i]["assessment"]["vmaf"][c] = i_data["pooled_metrics"]["vmaf"]["mean"]
    o_data["shots"][i]["assessment"]["psnr"][c] = (6*i_data["pooled_metrics"]["psnr_y"]["mean"] + \
        i_data["pooled_metrics"]["psnr_cb"]["mean"] + i_data["pooled_metrics"]["psnr_cr"]["mean"])/8
    info = f"ffprobe -v error -select_streams v:0 -show_entries format:stream -print_format json {o}"
    cout = json.loads(subprocess.run(info.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
    o_data["shots"][i]["assessment"]["rate"][c] = int(cout["format"]["bit_rate"])
    o_data["shots"][i]["duration"] = float(cout["format"]["duration"])
    
def save_opt(i, t, opt):
    o_data["shots"][i]["opt_points"][t]["crf"] = int(opt)
    with open(rd_file, 'w') as w:
        json.dump(o_data, w, separators=(',',': '))

def combine():
    min_rate = math.inf
    min_dist = 100
    o = []
    for comb in itertools.product(*s_crfs): #for each combination
        dist = 0
        rate = 0
        for i,v in enumerate(comb):
            dist = dist + (100 - o_data["shots"][i]["assessment"]["vmaf"][v]) * o_data["shots"][i]["duration"]
            rate = rate + o_data["shots"][i]["assessment"]["rate"][v] * o_data["shots"][i]["duration"]
        dist = dist / duration
        rate = rate / duration
        if t_name == "vmaf":
            if dist < (100 - t_val) and rate < min_rate:
                min_rate = rate
                o = list(comb)
        elif t_name == "rate":
            if rate < t_val and dist < min_dist:
                min_dist = dist
                o = list(comb)
        else:
            print("ERROR - not a target")
            exit()
    if not o:
        o = list(comb)
    return o

def mux(t_i, t_name, t_val):
    file_list = "" #list of encoded vids to be stored in OUT_LIST
    with open(rd_file, 'r') as f:
        o_data = json.load(f)
    for shot in range(0,num_scenes):
        opt_crf = o_data["shots"][0]["opt_points"][t_i]["crf"]
        file_list = file_list + "file '" + DIST_PATH + str(shot) + "/" \
        + str(opt_crf) + "_" + codec.upper() + "." + s_cod["container"] + "' \n"
    with open(OUT_LIST, 'w') as w:
        w.write(file_list)
    o = OUT_PATH+source_name[:9] + "_" + t_name + str(t_val) + "_" + codec.upper() + "." + s_cod["container"]
    mux = f"ffmpeg -f concat -i {OUT_LIST} -c copy {o} -hide_banner -loglevel error"
    subprocess.call(mux, shell=True)
    print("--out_path= " + o)


##------------------EXE--------------------##
struct_points = [] #structure of target points for the json file
struct_shots = [] #structure of shots for the json file

if source_path.endswith(".yuv"):
    print("yuv input")
elif source_path.endswith(".y4m"):
    print("y4m input")
else:
    print("No such an input type")
    exit()

num_scenes = shot_change_detection(source_path)
    
#init values based on the selected output codec
if codec == "avc":
    s_cod = PARAM_AVC
    init_res_matrix(PARAM_AVC["crfs"])
elif codec == "hevc":
    s_cod = PARAM_HEVC
    init_res_matrix(PARAM_HEVC["crfs"])
elif codec == "vp9":
    s_cod = PARAM_VP9
    init_res_matrix(PARAM_VP9["crfs"])
else:
    print("No such an codec")
    exit()

min_range_crf = s_cod["starting_range"][0]
max_range_crf = s_cod["starting_range"][1]

with open(tm_file, 'r') as f:
    o_data = json.load(f)
    
#add source name and results matrix
o_data["content"] = source_name
o_data["codec"] = codec
o_data["width"] = raw_width
o_data["height"] = raw_height
o_data["fps"] = raw_fps
o_data["shots"][0]["assessment"] = str_matrix
    
#add emplty target points
base_point = o_data["shots"][0]["opt_points"][0]
for t_name in target_list:
    for t_val in target_list[t_name]:
        base_point["metric"] = t_name
        base_point["target"] = t_val
        struct_points.append(copy.deepcopy(base_point))
o_data["shots"][0]["opt_points"] = struct_points
    
#add empty shots
base_shot = o_data["shots"][0]
for i in range(0, num_scenes):
    base_shot["index"] = i #assign index to shots in json file
    struct_shots.append(copy.deepcopy(base_shot))
o_data["shots"] = struct_shots

with open(rd_file, 'w') as w:
    json.dump(o_data, w, separators=(',',': '))

target_index = 0
point_index = 0
for t_name in target_list:
    for t_val in target_list[t_name]:
        
        shot_index = 0
        if target_index == 0:
            s_crfs = np.zeros(shape=(num_scenes, (max_range_crf+1)-min_range_crf), dtype=int) #init structure
            for shot in sorted(os.listdir(REF_PATH)): #for each shot
                for current_crf in range(min_range_crf, max_range_crf+1):
                    out = encode(shot, shot_index, current_crf) #encoding
                    assess(shot, out) #quality assessment
                    store_results(shot_index, current_crf, out)
                s_crfs[shot_index] = [c for c in o_data["shots"][shot_index]["assessment"]["crf"] if c != 0] #take only encoded shots
                shot_index += 1
        opt_crfs = combine() #create all combinations
        print("--out_crfs= " + str(opt_crfs))
        for i in range(0,num_scenes): #save the opt crf for each shot
            save_opt(i, target_index, opt_crfs[i])

        target_index += 1

#OUT
target_index = 0
for t_name in target_list:
    for t_val in target_list[t_name]:
        mux(target_index, t_name, t_val)
        target_index += 1


