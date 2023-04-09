import subprocess #to access ffmpeg in the system
import json #to handle json files
import random #to generate random numbers

#global variables init
source_path = ""
shot_list = [] #shot time bounds
num_shots = 0 #number of shots, from shot detection method
duration = 0.0 #sequence duration
npts = [] #crf values to encode, from interval method
id_exe = str(random.randint(100000,999999)) #execution unique id
s_cod = {} #coding parameters selection
data = {} #RD values and info from json results file
dist_max_val = 0 #maximum value of the quality metric

def encode(i,c):
    """
    Encode the input video file according to coding options

    Input:
    - i : int
        Shot index
    - c : int
        CRF value
    Output:
    - o : string
        Encoded file path
    """
    start_t = 0.0
    if i != 0:
        start_t = shot_list[i-1].split("pts_time:",1)[1]
    end_t = shot_list[i].split("pts_time:",1)[1]
    
    o = config["DIR"]["DIST_PATH"] + str(i) + "/" + str(c) + "_" \
        + config["ENC"]["CODEC"].upper() + "." + s_cod["container"]
    print("-encoding: " + o)
    if source_path.endswith(".yuv"):
        t = f"-f rawvideo -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} \
            -r {config['ENC']['FPS']} -pixel_format {config['ENC']['PX_FMT']} "
    else:
        t = ""
    
    enc = f"ffmpeg -ss {start_t} -to {end_t} {t}-i {source_path} -c:v {s_cod['lib']} \
        -crf {c} {s_cod['add_param']} -pix_fmt yuv420p -an {o} -hide_banner -loglevel error"
    subprocess.call(enc, shell=True)
    return o

def assess(i,f):
    """
    Execute quality assessment and store the results into the log file

    Input:
    - i : int
        [ref] Shot index
    - f : string
        [dist] Video to assess
    """
    start_t = 0.0
    end_t = float(shot_list[i].split("pts_time:",1)[1])
    if i != 0:
        start_t = float(shot_list[i-1].split("pts_time:",1)[1])
     
    if source_path.endswith(".yuv"):
        t = f"-f rawvideo -r {config['ENC']['FPS']} -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} "
    else:
        t = ""
    c_vmaf = f"ffmpeg -ss {start_t} -to {end_t} -i {source_path} -i {f} \
        -hide_banner -loglevel error\
        -lavfi \"[0:v]setpts=PTS-STARTPTS[ref];\
                 [1:v]setpts=PTS-STARTPTS[dist];\
                 [dist][ref]libvmaf=feature=name=psnr:log_path=config/tmp_vmaf_log_{id_exe}.json:log_fmt=json\" \
        -f null -"
    subprocess.call(c_vmaf, shell=True)

def set_results(i,c,f):
    """
    Store the quality and rate results for each shot at each encoded CRF

    Input:
    - i : int
        Shot index
    - c : int
        CRF value
    - f : string
        Evaluated file
    """
    with open("config/tmp_vmaf_log_" + id_exe + ".json", 'r') as r: #extract quality and rate values
        i_data = json.load(r)
    data["shots"][i]["assessment"]["crf"][c] = c
    if config['OPT']['DIST_METRIC'] == "vmaf":
        data["shots"][i]["assessment"]["dist"][c] = i_data["pooled_metrics"]["vmaf"]["mean"]
    elif config['OPT']['DIST_METRIC'] == "psnr":
        data["shots"][i]["assessment"]["dist"][c] = (6*i_data["pooled_metrics"]["psnr_y"]["mean"] + \
        i_data["pooled_metrics"]["psnr_cb"]["mean"] + i_data["pooled_metrics"]["psnr_cr"]["mean"])/8
    data["shots"][i]["assessment"]["dist"][c] = i_data["pooled_metrics"]["vmaf"]["mean"]
    info = f"ffprobe -v error -select_streams v:0 -show_entries format:stream -print_format json {f}"
    cout = json.loads(subprocess.run(info.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
    data["shots"][i]["assessment"]["rate"][c] = int(cout["format"]["bit_rate"])
    data["shots"][i]["duration"] = float(cout["format"]["duration"])
    
def compute_slope(xl,yl,xr,yr):
    """
    Calculate the slope value between the current min and max scene points

    Input:
    - xl : float
        Left and min rate
    - yl : float
        Left and max distortion
    - xr : float
        Right and max rate
    - yr : float
        Right and min distorition
    Output:
    - out : float
        Slope between the two points
    """
    if xl-xr == 0: #return 0 if horizontally flat
        return 0
    else:
        return -(yl-yr)/(xl-xr)
    
def check_side(i,pts,m,s):
    """
    Check if, when drawing a line intersecting a point with a given slope, 
    none of the points are on the left side of a vector, segment of the line.
    The direction of the vector is lower-right to upper-left.

    Input:
    - i : int
        Shot index
    - pts : dict
        Encoded shot info (crf,rate,dist)
    - m : int
        Index of the minimum value of the array
    - s : float
        Total slope
    Output:
    - m : int
        Updated minimum value: point with the closest slope to the total
    """
    count = 1
    while count > 0:
        l0 = [(s*pts["rate"][i][m] - pts["dist"][i][m])/s,0] #vector start, y axis intersection
        l1 = [0,pts["dist"][i][m] - s*pts["rate"][i][m]] #vector end, x axis intersection
        count = 0 #number of points on the left side
        for n in range(0, len(pts["dist"][i])):
            py = pts["dist"][i][n]
            px = pts["rate"][i][n]
            crss = (l1[0] - l0[0])*(py - l0[1]) - (px - l0[0])*(l1[1] - l0[1])
            if crss > 0.1: #if cross product is positive (with a tolerance) the point is on the left side
                m = n
                count += 1
    return m


#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)

