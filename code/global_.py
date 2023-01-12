import subprocess #to access ffmpeg in the system
import json #to handle json files
import random #to generate random numbers

#global variables init
num_shots = 0 #number of shots, from shot detection method
duration = 0.0 #sequence duration
npts = [] #crf values to encode, from interval method
id_exe = str(random.randint(100000,999999)) #execution unique id
s_cod = {} #coding parameters selection
data = {} #RD values and info from json results file

def encode(s,i,c):
    """
    Encode the input video file according to coding options

    Input:
    - s : string
        Source file name
    - i : int
        Shot index
    - c : int
        CRF value
    Output:
    - o : string
        Encoded file path
    """
    o = config["DIR"]["DIST_PATH"] + str(i) + "/" + str(c) + "_" \
        + config["ENC"]["CODEC"].upper() + "." + s_cod["container"]
    if s.endswith(".yuv") or s.endswith(".y4m"):
        t = f"-f rawvideo -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} \
            -r {config['ENC']['FPS']} -pixel_format yuv420p "
    else:
        t = ""
    enc = f"ffmpeg {t}-i {config['DIR']['REF_PATH'] + s} \
        -c:v {s_cod['lib']} -crf {c} {s_cod['add_param']} {o} -hide_banner -loglevel error"
    subprocess.call(enc, shell=True)
    print("-encode: " + o)
    return o

def assess(s,f):
    """
    Execute quality assessment and store the results into the log file

    Input:
    - s : string
        [ref] Source reference file
    - f : string
        [dist] Video to assess
    """
    if s.endswith(".yuv") or s.endswith(".y4m"):
        t = f"-f rawvideo -r {config['ENC']['FPS']} -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} "
    else:
        t = ""
    c_vmaf = f"ffmpeg {t}-i {config['DIR']['REF_PATH'] + s} -i {f} -hide_banner -loglevel error\
            -lavfi \"[0:v]setpts=PTS-STARTPTS[ref];\
                    [1:v]scale={config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']}:flags=bicubic, setpts=PTS-STARTPTS[dist];\
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
    data["shots"][i]["assessment"]["dist"][c] = i_data["pooled_metrics"]["vmaf"]["mean"]
    #data["shots"][i]["assessment"]["psnr"][c] = (6*i_data["pooled_metrics"]["psnr_y"]["mean"] + \
        #i_data["pooled_metrics"]["psnr_cb"]["mean"] + i_data["pooled_metrics"]["psnr_cr"]["mean"])/8
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

