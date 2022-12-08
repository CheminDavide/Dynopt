import os #to access system folders
import json #to handle json files
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
import global_

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
    if xl-xr == 0:
        return 0
    else:
        return -(yl-yr)/(xl-xr)

def check_side(i,pts,m,s):
    """
    Check if, when drawing a line intersectin a point with a given slope, none of the points are in the left side of the line.
    The direction of the line is lower-right to upper-left.

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
        l0 = [(s*pts["rate"][i][m] - pts["dist"][i][m])/s,0]
        l1 = [0,pts["dist"][i][m] - s*pts["rate"][i][m]]
        count = 0
        for n in range(0, len(pts["dist"][i])):
            py = pts["dist"][i][n]
            px = pts["rate"][i][n]
            crss = (l1[0] - l0[0])*(py - l0[1]) - (px - l0[0])*(l1[1] - l0[1])
            if crss > 0.1:
                m = n
                count += 1
    return m

def run(ti, tn, tv):
    """
    Lagrange implementation

    Input:
    - ti : int
        Current target index
    - tn : string
        Current target name
    - tv : float
        Current target value
    Output:
    - out : np.array(num_shots)
        List of optimal CRFs for each shot
    """
    curr_opt = {"l": np.zeros(global_.num_shots), "r": np.zeros(global_.num_shots)} #new optimal inteval bounds
    prev_opt = {"l": np.ones(global_.num_shots), "r": np.ones(global_.num_shots)} #previous optimal inteval bounds
    s_pts = {"crf": np.zeros(global_.num_shots, dtype=int), \
            "rate": np.zeros(global_.num_shots), \
            "dist": np.zeros(global_.num_shots)} #info current optimal combination
    t_ext = {"l": [], "r": [], "slope": 0.0} #general slope
    t_pts = {"crf": global_.npts, \
            "rate": np.zeros((global_.num_shots, config["ENC"]["NUM_INTERVALS"])), \
            "dist": np.zeros((global_.num_shots, config["ENC"]["NUM_INTERVALS"]))} #info encoded shots
    s_slopes = np.zeros((global_.num_shots, config["ENC"]["NUM_INTERVALS"] - 1)) #single slopes
    
    shot_index = 0
    for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
        for n_crf, val_crf in enumerate(t_pts["crf"]): #for each init crf
            if ti == 0 and global_.new_enc:
                path = global_.encode(shot, shot_index, val_crf) #encoding
                global_.assess(shot, path) #quality assessment
                global_.set_results(shot_index, int(val_crf), path)
            #store results in t_pts dictionary, weighted by duration
            r = global_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = 100 - global_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            t_pts["rate"][shot_index][n_crf] = r * global_.data["shots"][shot_index]["duration"] / global_.duration
            t_pts["dist"][shot_index][n_crf] = d * global_.data["shots"][shot_index]["duration"] / global_.duration
        for n_crf in range(1,config["ENC"]["NUM_INTERVALS"]): #compute and store slope between all close points
            s_slopes[shot_index][n_crf-1] = compute_slope(t_pts["rate"][shot_index][n_crf],\
                                                          t_pts["dist"][shot_index][n_crf],\
                                                          t_pts["rate"][shot_index][n_crf-1],\
                                                          t_pts["dist"][shot_index][n_crf-1])
        shot_index += 1
    t_rate = np.einsum('ij->j',t_pts["rate"]) #sum rate results per crf
    t_dist = np.einsum('ij->j',t_pts["dist"]) #sum dist results per crf
    t_ext["l"] = [t_rate[-1], t_dist[-1]] #last element, crfs 51
    t_ext["r"] = [t_rate[0], t_dist[0]] #first element, crfs 0
    t_ext["slope"] = compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])
    
    #when new solution is the same as the past one
    while not all(curr_opt["r"] == prev_opt["r"]) or not all(curr_opt["l"] == prev_opt["l"]):
        prev_opt = curr_opt.copy() #keep track of the previous optimal combination
        diffs = abs(s_slopes - t_ext["slope"]) #difference between all and current slope
        s_mins = np.argmin(diffs, axis=1) #find the min difference
        for shot_index in range(0,global_.num_shots):
            if np.einsum('i->',s_slopes[shot_index]) != 0: #handle 0 slope shots ex. short black screen
                s_curr = check_side(shot_index, t_pts, s_mins[shot_index], -t_ext["slope"])
            else:
                s_curr = -1
            s_pts["crf"][shot_index] = t_pts["crf"][s_curr]
            s_pts["rate"][shot_index] = t_pts["rate"][shot_index][s_curr]
            s_pts["dist"][shot_index] = t_pts["dist"][shot_index][s_curr]
        t_rate = np.einsum('i->',s_pts["rate"]) #sum rate results per crf
        t_dist = np.einsum('i->',s_pts["dist"]) #sum dist results per crf
        if np.einsum('i->',s_pts[tn]) > tv: #if current opt go beyond the target
            if tn == "dist":
                t_ext["l"] = [t_rate, t_dist] #new general point
                curr_opt["l"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["r"] = [t_rate, t_dist]
                curr_opt["r"] = s_pts["crf"].copy()
        else:
            if tn == "dist":
                t_ext["r"] = [t_rate, t_dist] #new general point
                curr_opt["r"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["l"] = [t_rate, t_dist]
                curr_opt["l"] = s_pts["crf"].copy()
        t_ext["slope"] = compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])
    
    if tn == "dist":
        return curr_opt["r"]
    elif tn == "rate":
        return curr_opt["l"]


#get custom variables from config.json
with open("config/config.json", 'r') as f:
    config = json.load(f)
    