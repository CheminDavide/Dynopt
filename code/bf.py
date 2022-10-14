import os #to access system folders
import json #to handle json files
import itertools #to combine options
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
import global_

def combine(sc, tn, tv):
    """
    Create all encoded points possible combinations and find the closest to the target
    
    Output:
    - o : list (num_scenes)
        Best CRF combination for the current target
    """
    o = []
    if tn == "dist":
        y_min = math.inf
        to_min = "rate"
        xf, xg, yf, yg = 100, 1, 0, -1
    elif tn == "rate":
        y_min = 100
        to_min = "dist"
        xf, xg, yf, yg = 0, -1, 100, 1
    for comb in itertools.product(*sc): #for each combination
        x = y = 0
        for i,val in enumerate(comb):
            x += (xf-xg*global_.data["shots"][i]["assessment"][tn][val]) * global_.data["shots"][i]["duration"]
            y += (yf-yg*global_.data["shots"][i]["assessment"][to_min][val]) * global_.data["shots"][i]["duration"]
        x = x / global_.duration
        y = y / global_.duration
        if x < tv and y < y_min:
            y_min = y
            o = list(comb)
            x_min = x
    if not o:
        o = list(comb)
    return o

def run(ti, tn, tv):
    """
    Create all encoded points possible combinations and find the closest to the target
    
    Output:
    - o : list (num_scenes)
        Optimal CRF combination for the current target
    """
    shot_index = 0
    s_crfs = np.zeros((global_.num_scenes, len(global_.npts)), dtype=int) #init structure
    for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
        for current_crf in global_.npts:
            if ti == 0:
                out = global_.encode(shot, shot_index, current_crf) #encoding
                global_.assess(shot, out) #quality assessment
                global_.store_results(shot_index, current_crf, out)
        s_crfs[shot_index] = [c for c in global_.data["shots"][shot_index]["assessment"]["crf"] if c != 0]
        shot_index += 1
    opt_crfs = combine(s_crfs, tn, tv) #create all combinations
    return opt_crfs

#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)


