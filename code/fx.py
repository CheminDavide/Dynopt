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
    - o : list (num_shots)
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
    Fixed CRF implementation
    Encode each shot at the same CRF until the sequence satisfies the target

    Input:
    - ti : int
        Current target index
    - tn : string
        Current target name
    - tv : float
        Current target value
    Output:
    - out : list(num_shots)
        Set of CRFs of equal value for the current target
    """
    s_pts = {"rate": np.zeros((global_.num_shots, len(global_.npts))), \
                 "dist": np.zeros((global_.num_shots, len(global_.npts)))}
    t_pts = {"rate": np.zeros(len(global_.npts)), \
                 "dist": np.zeros(len(global_.npts))}
    n_crf = len(global_.npts) - 1
    curr_crf = global_.npts[-1]
    shot_index = 0
    crf_index = 0
    
    for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
        for n_crf, val_crf in enumerate(global_.npts):
            if ti == 0 and global_.new_enc:
                path = global_.encode(shot, shot_index, val_crf) #encoding
                global_.assess(shot, path) #quality assessment
                global_.set_results(shot_index, int(val_crf), path)
            r = global_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = global_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            s_pts["rate"][shot_index][n_crf] = r * global_.data["shots"][shot_index]["duration"] / global_.duration
            s_pts["dist"][shot_index][n_crf] = d * global_.data["shots"][shot_index]["duration"] / global_.duration
        shot_index += 1
    
    if tn == "dist":
        tv = 100 - tv #if target is quality convert IVMAF to VMAF
    #iterate the points starting from the end until the target is no more satisfied
    while np.einsum('ij->j',s_pts[tn])[n_crf] < tv and n_crf != 0:
        curr_crf = global_.npts[n_crf]
        n_crf -= 1
    #if the min CRF metric turns out less than the target
    if n_crf == len(global_.npts) - 1:
        print("no encodings satisfy the target - encoding at min CRF")
    return np.zeros(global_.num_shots) + curr_crf

#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)


