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
    
    Input:
    - sc : list (num_shots,npts)
        Array of elemental encodes
    - tn : string
        Current target name
    - tv : float
        Current target value
    Output:
    - o : list (num_shots)
        Best CRF combination for the current target
    """
    o = []
    if tn == "rate":
        y_min = global_.dist_max_val
        to_min = "dist"
        xf, xg, yf, yg = 0, -1, global_.dist_max_val, 1
    elif tn == "dist":
        y_min = math.inf
        to_min = "rate"
        xf, xg, yf, yg = global_.dist_max_val, 1, 0, -1
    print("-combine: comparing " + str(np.shape(sc)[1]**np.shape(sc)[0]) + " options...")
    
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
        if tn == "rate":
            print("no encodings satisfy the target - encoding at min quality")
            o = list(comb)
        elif tn == "dist":
            print("no encodings satisfy the target - encoding at max quality")
            o = np.zeros(global_.num_shots,dtype=int) + config["ENC"]["CRF_RANGE"][0]
    return o

def run(ti, tn, tv):
    """
    Brute force implementation
    Create all encoded points possible combinations and find the closest to the target

    Input:
    - ti : int
        Current target index
    - tn : string
        Current target name
    - tv : float
        Current target value
    Output:
    - out : list(num_shots)
        Optimal CRF combination for the current target
    """
    s_crfs = np.zeros((global_.num_shots, len(global_.npts)), dtype=int) #init structure
    for shot_index in range(global_.num_shots): #for each shot
        for curr_crf in global_.npts:
            if ti == 0 and config["DEBUG"]["ENC"]:
                path = global_.encode(shot_index, curr_crf) #encoding
                global_.assess(shot_index, path) #quality assessment
                global_.set_results(shot_index, int(curr_crf), path)
        s_crfs[shot_index] = [c for c in global_.data["shots"][shot_index]["assessment"]["crf"] if c != 0]
    opt_crfs = combine(s_crfs, tn, tv) #create all combinations
    return opt_crfs

#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)


