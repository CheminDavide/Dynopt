import subprocess #to access ffmpeg in the system
import json #to handle json files

#TODO add comments
num_shots = 0
duration = 0.0
npts = []

s_cod = {}
data = {}

def encode(s,i,c):
    """
    Encode the raw video file according to coding options

    Input:
    - s : string
        Source file
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
    enc = f"ffmpeg -f rawvideo -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} \
        -r {config['ENC']['FPS']} -pixel_format yuv420p -i {config['DIR']['REF_PATH'] + s} \
        -c:v {s_cod['lib']} -crf {c} {s_cod['add_param']} {o} -hide_banner -loglevel error"
    subprocess.call(enc, shell=True)
    print("-encode: " + o)
    return o

def assess(s,f):
    """
    Execute quality assessment and store the results into the log file

    Input:
    - s : string
        Source reference file
    - f : string
        Video to assess
    """
    vmaf_log = "config/" + config["DIR"]["VMAF_LOGS"]
    c_vmaf = f"ffmpeg -f rawvideo -r {config['ENC']['FPS']} -video_size {config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']} \
            -i {config['DIR']['REF_PATH'] + s} -i {f} -hide_banner -loglevel error\
            -lavfi \"[0:v]setpts=PTS-STARTPTS[ref];\
                    [1:v]scale={config['ENC']['WIDTH']}x{config['ENC']['HEIGHT']}:flags=bicubic, setpts=PTS-STARTPTS[dist];\
                    [dist][ref]libvmaf=feature=name=psnr:log_path={vmaf_log}:log_fmt=json\" \
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
    with open("config/" + config["DIR"]["VMAF_LOGS"], 'r') as r: #extract quality and rate values
        i_data = json.load(r)
    data["shots"][i]["assessment"]["crf"][c] = c
    data["shots"][i]["assessment"]["dist"][c] = i_data["pooled_metrics"]["vmaf"]["mean"]
    #data["shots"][i]["assessment"]["psnr"][c] = (6*i_data["pooled_metrics"]["psnr_y"]["mean"] + \
        #i_data["pooled_metrics"]["psnr_cb"]["mean"] + i_data["pooled_metrics"]["psnr_cr"]["mean"])/8
    info = f"ffprobe -v error -select_streams v:0 -show_entries format:stream -print_format json {f}"
    cout = json.loads(subprocess.run(info.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
    data["shots"][i]["assessment"]["rate"][c] = int(cout["format"]["bit_rate"])
    data["shots"][i]["duration"] = float(cout["format"]["duration"])


#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)

