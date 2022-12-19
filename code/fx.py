import os #to access system folders
import json #to handle json files
import itertools #to combine options
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
import global_

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
    crf_index = len(global_.npts) - 1
    curr_crf = global_.npts[-1]
    shot_index = 0
    if tn == "dist":
        tv = 100 - tv
    
    for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
        for n_crf, val_crf in enumerate(global_.npts):
            if ti == 0 and config["DEBUG"]["ENC"]:
                path = global_.encode(shot, shot_index, val_crf) #encoding
                global_.assess(shot, path) #quality assessment
                global_.set_results(shot_index, int(val_crf), path)
            r = global_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = global_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            s_pts["rate"][shot_index][n_crf] = r * global_.data["shots"][shot_index]["duration"] / global_.duration
            s_pts["dist"][shot_index][n_crf] = d * global_.data["shots"][shot_index]["duration"] / global_.duration
        shot_index += 1
    
    #iterate the points starting from the end until the target is no more satisfied
    while np.einsum('ij->j',s_pts[tn])[crf_index] < tv and crf_index != 0:
        curr_crf = global_.npts[crf_index]
        crf_index -= 1
    
    if crf_index == len(global_.npts) - 1: #if target is below min CRF metric value
        print("no encodings satisfy the target - encoding at min CRF")
    elif crf_index == 0: #if target is above max CRF
        print("no encodings satisfy the target - encoding at max CRF")
    elif tn == "dist":
        crf_index -= 1
        
    return np.zeros(global_.num_shots) + curr_crf

#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)


