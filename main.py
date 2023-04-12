"""Video Dynamic Optimizer
<Long description>
Author: Chemin Davide <mail>
Created: 13 Oct 2022
"""

import os #to access system folders
import sys #to exit the process
import getopt #to separate input string into parameters
import subprocess #to access ffmpeg in the system
import shutil #to remove directories
import numpy as np #easy vector operations
import copy #to create list shadow copies
import json #to handle json files

#import from custom scripts
from code import global_ as gb_ #global varibles and functions
from code import fx #fixed CRF method
from code import bf #brute force method
from code import lg #lagrangian method
from code import cf #curve fitting method

# -----------------------------------------------------------------------------
#                               Folders pathes
# -----------------------------------------------------------------------------

p_elemental_encodes =  "tests_vids/temp_encoded" + "/" #encoded shots folder
p_rd_log = "tests_rd" + "/"#optional JSON output folder with RD results


# -----------------------------------------------------------------------------
#                               Init e import variables
# -----------------------------------------------------------------------------

#default values
gb_.config = {
    "ENC": {
        "CODEC": "",
        "WIDTH": 0,
        "HEIGHT": 0,
        "FPS": 0,
        "PX_FMT": "",
        "CRF_RANGE": [],
        "NUM_PTS": 0
        },
    "OPT": {
        "DIST_TARGETS": [],
        "RATE_TARGETS": [],
        "DIST_METRIC": "",
        "OPT_METHOD": "",
        "SHOT_DETECT_TH": 0.
        },
    "DIR": {
        "DIST_PATH": p_elemental_encodes,
        "OUT_PATH": "",
        "RD_FOLDER": p_rd_log
        },
    "DEBUG": {
        "ENC": True, #if False it takes already computed RD values from existing RD file
        "DEL": True #if False it keeps all encoded shots at the end of execution
        }
}

#encoding paramethers
PARAM_AVC = {"crfs": 52, "opr_range": [0,51], "lib": "libx264", "container": "mp4", "add_param": ""}
PARAM_HEVC = {"crfs": 52, "opr_range": [0,51], "lib": "libx265", "container": "mp4", "add_param": "-x265-params log-level=none"}
PARAM_VP9 = {"crfs": 64, "opr_range": [0,63], "lib": "libvpx-vp9", "container": "mp4", "add_param": "-b:v 0"}
PARAM_AV1 = {"crfs": 64, "opr_range": [0,63], "lib": "libsvtav1", "container": "mp4", "add_param": ""}

argumentList = sys.argv[1:] # list of command line arguments, skip the first one
options = "i:m:r:d:c:o:h" #options list
long_options = ["help","ires=","ifps=","ipx_fmt=","range=","pts=","dmetric=","dth=","skip","keep"]

try:
    arguments, values = getopt.getopt(argumentList, options, long_options) # parsing argument
    for currentArgument, currentValue in arguments: # checking each argument
        
        if currentArgument == "-i":
            gb_.source_path = currentValue
            if not os.path.exists(gb_.source_path):
                print("ERROR: not a valid input file")
                sys.exit()
            source_name = os.path.basename(gb_.source_path).split('.')[0]
             
        elif currentArgument == "--ires":
            try:
                gb_.config["ENC"]["WIDTH"] = int(currentValue.split('x')[0])
                gb_.config["ENC"]["HEIGHT"] = int(currentValue.split('x')[1])
            except:
                print("ERROR: not a valid input resolution")
             
        elif currentArgument == "--ifps":
            try:
                gb_.config["ENC"]["FPS"] = float(currentValue)
            except:
                print("ERROR: not a valid input frame rate")
            
        elif currentArgument == "--ipx_fmt":
            gb_.config["ENC"]["PX_FMT"] = currentValue
             
        elif currentArgument == "-m":
            if currentValue in ("fx","bf","lg","cf"):
                gb_.config["OPT"]["OPT_METHOD"] = currentValue
            else:
                print("ERROR: not an optimization method")
                sys.exit()
            
        elif currentArgument == "--range":
            gb_.config["ENC"]["CRF_RANGE"] = list(map(int,currentValue.replace("[","").replace("]","").split(',')))
            if not len(gb_.config["ENC"]["CRF_RANGE"]) == 2:
                print("ERROR: failed to initialize the input CRF range")
                sys.exit()
            if gb_.config["ENC"]["CRF_RANGE"][0] > gb_.config["ENC"]["CRF_RANGE"][1]:
                print("ERROR: wrong CRF range")
                sys.exit()
            
        elif currentArgument == "--pts":
            gb_.config["ENC"]["NUM_PTS"] = int(currentValue)
             
        elif currentArgument == "-d":
            try:
                gb_.config["OPT"]["DIST_TARGETS"] = list(map(int,currentValue.replace("[","").replace("]","").split(',')))
            except:
                print("ERROR: failed to initialize DIST targets")
                sys.exit()
            
        elif currentArgument == "-r":
            try:
                gb_.config["OPT"]["RATE_TARGETS"] = list(map(int,currentValue.replace("[","").replace("]","").split(',')))
            except:
                print("ERROR: failed to initialize RATE targets")
                sys.exit()
            
        elif currentArgument == "--dmetric":
            gb_.config["OPT"]["DIST_METRIC"] = currentValue
             
        elif currentArgument == "--dth":
            gb_.config["OPT"]["SHOT_DETECT_TH"] = currentValue
            if gb_.config["OPT"]["SHOT_DETECT_TH"] < 0 or gb_.config["OPT"]["SHOT_DETECT_TH"] > 1:
                print("ERROR: invalid shot detection threshold")
                sys.exit()
            
        elif currentArgument == "-c":
            gb_.config["ENC"]["CODEC"] = currentValue
            #init values based on the selected output codec
            if gb_.config["ENC"]["CODEC"] == "avc":
                gb_.s_cod = PARAM_AVC
            elif gb_.config["ENC"]["CODEC"] == "hevc":
                gb_.s_cod = PARAM_HEVC
            elif gb_.config["ENC"]["CODEC"] == "vp9":
                gb_.s_cod = PARAM_VP9
            elif gb_.config["ENC"]["CODEC"] == "av1":
                gb_.s_cod = PARAM_AV1
            else:
                print("ERROR: " + gb_.config["ENC"]["CODEC"] + " is not a codec")
                sys.exit()
            #create the empty RD base matrix
            str_matrix = {"crf": np.zeros(gb_.s_cod["crfs"], dtype=int).tolist(),
                          "rate": np.zeros(gb_.s_cod["crfs"], dtype=int).tolist(),
                          "dist": np.zeros(gb_.s_cod["crfs"]).tolist()}
             
        elif currentArgument == "-o":
            gb_.config["DIR"]["OUT_PATH"] = currentValue
            if not os.path.exists(gb_.config["DIR"]["OUT_PATH"]):
                print("ERROR: the output folder does not exist")
                sys.exit()
            if not gb_.config["DIR"]["OUT_PATH"][-1] == "/":
                gb_.config["DIR"]["OUT_PATH"] = gb_.config["DIR"]["OUT_PATH"] + "/"
        
        elif currentArgument == "--skip":
            gb_.config["DEBUG"]["ENC"] = False
        
        elif currentArgument == "--keep":
            gb_.config["DEBUG"]["DEL"] = False

        elif currentArgument in ("-h", "--help"):
            print("python3 code/main.py -i <*inputfile> --ires <widthxheight> --ifps <framerate> --ipx_fmt <pixelfromat> -m <optimizationmethod> --range <CRFrange> --pts <CRFpoints> -r <*ratetargets> -d <*disttargets> --dmetric <distortionmetric> --dth <shotthreshold> -c <*outputcodec> -o <outputolder> --skip --keep")
            
except getopt.error as err:
    print(str(err)) # output error, and return with an error code
    sys.exit()

if gb_.source_path == "":
    print("ERROR: -i <inputfile> is a mandatory option")
    sys.exit()
    
if not gb_.config["OPT"]["DIST_TARGETS"] and not gb_.config["OPT"]["RATE_TARGETS"]:
    print("ERROR: at least one rate or dist target must be specified")
    sys.exit() 

if gb_.config["ENC"]["CODEC"] == "":
    print("ERROR: -c <outputcodec> is a mandatory option")
    sys.exit()
    
if not gb_.config["ENC"]["CRF_RANGE"]:
    gb_.config["ENC"]["CRF_RANGE"] = [gb_.s_cod["opr_range"][0]+1,gb_.s_cod["opr_range"][1]]
    print("WARNING: default CRF range applied: " + str(gb_.config["ENC"]["CRF_RANGE"]))
    
if gb_.config["ENC"]["NUM_PTS"] == 0:
    gb_.config["ENC"]["NUM_PTS"] = gb_.config["ENC"]["CRF_RANGE"][1] - gb_.config["ENC"]["CRF_RANGE"][0] + 1
    print("WARNING: default number of CRF points applied: " + str(gb_.config["ENC"]["NUM_PTS"]))
    
if gb_.config["OPT"]["DIST_METRIC"] == "":
    gb_.config["OPT"]["DIST_METRIC"] = "vmaf"
    print("WARNING: default distortion metric applied: VMAF")
    
if gb_.config["OPT"]["OPT_METHOD"] == "":
    gb_.config["OPT"]["OPT_METHOD"] = "lg"
    print("WARNING: default optimization strategy applied: LG")
    
if gb_.config["OPT"]["SHOT_DETECT_TH"] == 0.:
    gb_.config["OPT"]["SHOT_DETECT_TH"] = 0.25
    print("WARNING: default shot detection threshold applied: 0.25")
    
if gb_.config["ENC"]["CRF_RANGE"][0] < gb_.s_cod["opr_range"][0] or gb_.config["ENC"]["CRF_RANGE"][1] > gb_.s_cod["opr_range"][1]:
    print("ERROR: CRF out of range")
    sys.exit()
    
if gb_.config["ENC"]["NUM_PTS"] > gb_.config["ENC"]["CRF_RANGE"][1] - gb_.config["ENC"]["CRF_RANGE"][0] + 1:
    print("ERROR: too many points to encode in the interval " + str(gb_.config["ENC"]["CRF_RANGE"]))
    sys.exit()
if gb_.config["OPT"]["OPT_METHOD"] == "cf" and (gb_.config["ENC"]["CRF_RANGE"][1] - gb_.config["ENC"]["CRF_RANGE"][0])/gb_.config["ENC"]["NUM_PTS"] < 5:
    print("ERROR: too many CRF points for the CF method, reduce them or expand the range")
    sys.exit()
if gb_.config["OPT"]["OPT_METHOD"] == "cf" and gb_.config["ENC"]["NUM_PTS"] < 3:
    print("ERROR: not enough CRF points for the CF method, increase their number")
    sys.exit()
    
if gb_.config["OPT"]["DIST_METRIC"] == "vmaf":
    gb_.dist_max_val = 100
elif gb_.config["OPT"]["DIST_METRIC"] == "psnr":
    gb_.dist_max_val = 60
else:
    print("ERROR: not supported quality metric")
    sys.exit()

rd_file = gb_.config["DIR"]["RD_FOLDER"] + source_name + ".json"
if gb_.config["DEBUG"]["ENC"] == False:
    if not os.path.isfile(rd_file): #if file does not exists 
        print("ERROR: it is not possible to avoid encoding without an already stored RD file")
        sys.exit()
else:
    [shutil.rmtree(gb_.config["DIR"]["DIST_PATH"] + f) for f in os.listdir(gb_.config["DIR"]["DIST_PATH"])] #clean temp_encoded folder
    
target_list = {"dist": (gb_.dist_max_val - np.asarray(gb_.config["OPT"]["DIST_TARGETS"])).tolist(), "rate": (np.array(gb_.config["OPT"]["RATE_TARGETS"])*1000).tolist()}


# -----------------------------------------------------------------------------
#                              Methods
# -----------------------------------------------------------------------------

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
    print("-analysis: detecting shots...")
    TIME_LOGS = "config/tmp_shot_dect.log"
    with open(TIME_LOGS, 'w') as f: #create times log file
        pass
    start_t = end_t = 0.0
    det = f"ffmpeg -i {p} -hide_banner -loglevel error -filter_complex:v \
    \"select='gt(scene,{gb_.config['OPT']['SHOT_DETECT_TH']})',metadata=print:file={TIME_LOGS}\" -f null -"
    subprocess.call(det, shell=True)
    
    with open(TIME_LOGS, 'r') as r:
        gb_.shot_list = r.read().splitlines()[::2]
    gb_.shot_list.append("end pts_time:" + str(gb_.duration))
    
    for shot in range(len(gb_.shot_list)): #for each cut
        #create a folder for each scene
        new_dir = str(shot)
        new_path = os.path.join(gb_.config["DIR"]["DIST_PATH"], new_dir)
        os.mkdir(new_path)
    print("-analysis: " + str(len(gb_.shot_list)) + " detected shots")
    return len(gb_.shot_list)

def save_json_file():
    """
    Store final results optimized back to the json file
    """
    if not os.path.isfile(rd_file): #if file does not exists create it
        with open(rd_file, 'w') as f:
            pass
    with open(rd_file, 'w') as w:
        json.dump(gb_.data, w, separators=(',',': '))

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
        t_n = gb_.config["OPT"]["DIST_METRIC"]
        out_name = str(gb_.dist_max_val - t_v).zfill(len(str(target_list[t_name][-1])))
    elif t_n == "rate":
        out_name = str(int(t_v / 1000)).zfill(len(str(target_list[t_name][-1])) - 3)
    
    file_list = "" #list of encoded vids to be stored in shot_list file
    for shot in range(0,gb_.num_shots):
        opt_crf = gb_.data["shots"][shot]["opt_points"][t_i]["crf"]
        file_list = file_list + "file '../" + gb_.config["DIR"]["DIST_PATH"] + str(shot) + "/" \
        + str(opt_crf) + "_" + gb_.config["ENC"]["CODEC"].upper() + "." + gb_.s_cod["container"] + "' \n"
    with open("config/tmp_shot_list.txt", 'w') as w:
        w.write(file_list)
    o = gb_.config["DIR"]["OUT_PATH"] + source_name[:9] + "_" + t_n + out_name \
        + gb_.config["OPT"]["OPT_METHOD"] + "_" + gb_.config["ENC"]["CODEC"].upper() + "." + gb_.s_cod["container"]
    mux = f"ffmpeg -f concat -safe 0 -i {'config/tmp_shot_list.txt'} \
        -c copy {o} -hide_banner -loglevel error"
    print("-mux: " + o)
    subprocess.call(mux, shell=True)
    

# -----------------------------------------------------------------------------
#                       Init and shot detection
# -----------------------------------------------------------------------------

#get the total duration for the last cut
idu = f"ffprobe -v error -select_streams v:0 -show_entries format:stream \
    -print_format json {gb_.source_path} -hide_banner -loglevel error"
dta = json.loads(subprocess.run(idu.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
gb_.duration = float(dta['format']['duration'])

struct_points = [] #structure of target points for the json file
struct_shots = [] #structure of shots for the json file

if gb_.config["DEBUG"]["ENC"]:
    
    gb_.num_shots = shot_change_detection(gb_.source_path)

    gb_.data = {
        "content": "",
        "codec": "",
        "shots": [
            {
                "index": 0,
                "duration": 0.0,
                "assessment": [],
                "opt_points": [
                    {
                        "metric": "",
                        "target": 0,
                        "crf": 0
                    }
                ]
            }
        ]
    }

    #add source name and results matrix
    gb_.data["content"] = source_name
    gb_.data["codec"] = gb_.config["ENC"]["CODEC"]
    gb_.data["shots"][0]["assessment"] = str_matrix
    
    #add emplty target points
    base_point = gb_.data["shots"][0]["opt_points"][0]
    for t_name in target_list:
        for t_val in target_list[t_name]:
            base_point["metric"] = t_name
            base_point["target"] = t_val
            struct_points.append(copy.deepcopy(base_point))
    gb_.data["shots"][0]["opt_points"] = struct_points
    
    #add empty shots
    base_shot = gb_.data["shots"][0]
    for i in range(0, gb_.num_shots):
        base_shot["index"] = i #assign index to shots in json file
        struct_shots.append(copy.deepcopy(base_shot))
    gb_.data["shots"] = struct_shots

else: #restore optimal points values
    with open(rd_file, 'r') as f:
        gb_.data = json.load(f)
    gb_.num_shots = len(gb_.data["shots"])
    
    base_point = {
        "metric": "",
        "target": 0,
        "crf": 0}
    for i in range(0, gb_.num_shots):
        for t_name in target_list:
            for t_val in target_list[t_name]:
                base_point["metric"] = t_name
                base_point["target"] = t_val
                struct_points.append(copy.deepcopy(base_point))
        gb_.data["shots"][i]["opt_points"] = struct_points
    
if gb_.source_path.endswith(".yuv"):
    print("-init: done. input: yuv")
elif gb_.source_path.endswith(".y4m"):
    print("-init: done. input: y4m")
else:
    print("-init: done. input: not rawvideo")

    
# -----------------------------------------------------------------------------
#                              Exe
# -----------------------------------------------------------------------------

pr = np.zeros(len(target_list["rate"])+len(target_list["dist"]))
pd = np.zeros(len(target_list["rate"])+len(target_list["dist"]))
    
target_index = 0
for t_name in target_list:
    for t_val in target_list[t_name]:
        
        gb_.npts = interval(gb_.config["ENC"]["CRF_RANGE"], gb_.config["ENC"]["NUM_PTS"]).tolist()
        
        if gb_.config["OPT"]["OPT_METHOD"] == "fx": #fixed CRF
            opt = fx.run(target_index, t_name, t_val)
            
        elif gb_.config["OPT"]["OPT_METHOD"] == "bf": #brute force approach
            opt = bf.run(target_index, t_name, t_val)
            
        elif gb_.config["OPT"]["OPT_METHOD"] == "lg": #lagrangian optimization
            opt = lg.run(target_index, t_name, t_val)
        
        elif gb_.config["OPT"]["OPT_METHOD"] == "cf": #curve fitting
            opt = cf.run(target_index, t_name, t_val)
            #do not override, skip the encoding instead, if the file already exists
            gb_.s_cod["add_param"] = gb_.s_cod["add_param"] + " -n"
            print("-encode: encoding in-between points...")
            shot_index = 0
            for shot in range(gb_.num_shots): #for each shot
                out = gb_.encode(shot_index, opt[shot_index]) #encoding
                gb_.assess(shot_index,out)
                gb_.set_results(shot_index,int(opt[shot_index]),out)
                shot_index += 1
        print("-out: crfs " + str(opt))
        
        for i in range(0,gb_.num_shots): #save the opt crf for each shot
            gb_.data["shots"][i]["opt_points"][target_index]["crf"] = int(opt[i])
        if not gb_.config["DIR"]["RD_FOLDER"] == "":
            save_json_file()
            
        if gb_.config["DIR"]["OUT_PATH"] == "":
            r = np.zeros(gb_.num_shots)
            d = np.zeros(gb_.num_shots)
            for shot_index in range(gb_.num_shots): #for each shot
                r[shot_index] = gb_.data["shots"][shot_index]["assessment"]["rate"][int(opt[shot_index])] \
                    * gb_.data["shots"][shot_index]["duration"] / gb_.duration
                d[shot_index] = gb_.data["shots"][shot_index]["assessment"]["dist"][int(opt[shot_index])] \
                    * gb_.data["shots"][shot_index]["duration"] / gb_.duration
            pr[target_index] = np.einsum('i->',r)
            pd[target_index] = np.einsum('i->',d)
        else:
            mux(target_index, t_name, t_val)
        
        target_index += 1

if gb_.config["DIR"]["OUT_PATH"] == "":
    print("r:"+str(pr)+" d:"+str(pd))

if gb_.config["DEBUG"]["DEL"]: #delete temp files
    os.remove("config/tmp_shot_dect.log")
    os.remove("config/tmp_vmaf_log.json")
    os.remove("config/tmp_shot_list.txt")
    [shutil.rmtree(gb_.config["DIR"]["DIST_PATH"] + f) for f in os.listdir(gb_.config["DIR"]["DIST_PATH"])]