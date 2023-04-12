import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
import code.global_ as gb_

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
    curr_opt = {"l": np.zeros(gb_.num_shots, dtype=int),
                "r": np.zeros(gb_.num_shots, dtype=int)} #new optimal inteval bounds
    prev_opt = {"l": np.ones(gb_.num_shots, dtype=int),
                "r": np.ones(gb_.num_shots, dtype=int)} #previous optimal inteval bounds
    s_pts = {"crf": np.zeros(gb_.num_shots, dtype=int),
            "rate": np.zeros(gb_.num_shots),
            "dist": np.zeros(gb_.num_shots)} #info current optimal combination
    t_ext = {"l": [], "r": [], "slope": 0.0} #general slope
    t_pts = {"crf": gb_.npts,
            "rate": np.zeros((gb_.num_shots, gb_.config["ENC"]["NUM_PTS"])),
            "dist": np.zeros((gb_.num_shots, gb_.config["ENC"]["NUM_PTS"]))} #info encoded shots
    s_slopes = np.zeros((gb_.num_shots, gb_.config["ENC"]["NUM_PTS"] - 1)) #single slopes

    for shot_index in range(gb_.num_shots): #for each shot
        for n_crf, val_crf in enumerate(t_pts["crf"]): #for each init crf
            if ti == 0 and gb_.config["DEBUG"]["ENC"]:
                path = gb_.encode(shot_index, val_crf) #encoding
                gb_.assess(shot_index, path) #quality assessment
                gb_.set_results(shot_index, int(val_crf), path)
            #store results in t_pts dictionary, weighted by duration
            r = gb_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = gb_.dist_max_val - gb_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            t_pts["rate"][shot_index][n_crf] = r * gb_.data["shots"][shot_index]["duration"] / gb_.duration
            t_pts["dist"][shot_index][n_crf] = d * gb_.data["shots"][shot_index]["duration"] / gb_.duration
        for n_crf in range(1,gb_.config["ENC"]["NUM_PTS"]): #compute and store slope between all close points
            s_slopes[shot_index][n_crf-1] = gb_.compute_slope(t_pts["rate"][shot_index][n_crf],
                                                          t_pts["dist"][shot_index][n_crf],
                                                          t_pts["rate"][shot_index][n_crf-1],
                                                          t_pts["dist"][shot_index][n_crf-1])
    
    r_min = np.einsum('ij->j',t_pts["rate"])[-1]
    r_max = np.einsum('ij->j',t_pts["rate"])[0]
    d_min = np.einsum('ij->j',t_pts["dist"])[0]
    d_max = np.einsum('ij->j',t_pts["dist"])[-1]
    t_ext["l"] = [r_min, d_max] #last elements, crfs 51
    t_ext["r"] = [r_max, d_min] #first elements, crfs 0
    t_ext["slope"] = gb_.compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])

    if tn == "rate": #check target out of interval bounds
        if tv > r_max:
            return np.zeros(gb_.num_shots, dtype=int) + gb_.config["ENC"]["CRF_RANGE"][0] #ex all 0
        elif tv < r_min:
            return np.zeros(gb_.num_shots, dtype=int) + gb_.config["ENC"]["CRF_RANGE"][1] #ex all 51
    elif tn == "dist":
        if tv > d_max:
            return np.zeros(gb_.num_shots, dtype=int) + gb_.config["ENC"]["CRF_RANGE"][1] #ex all 51
        elif tv < d_min:
            return np.zeros(gb_.num_shots, dtype=int) + gb_.config["ENC"]["CRF_RANGE"][0] #ex all 0
    
    #when new solution is the same as the past one
    while not all(curr_opt["r"] == prev_opt["r"]) or not all(curr_opt["l"] == prev_opt["l"]):
        prev_opt = curr_opt.copy() #keep track of the previous optimal combination
        diffs = abs(s_slopes - t_ext["slope"]) #difference between all and current slope
        s_mins = np.argmin(diffs, axis=1) #find the min difference
        for shot_index in range(0,gb_.num_shots): #save current mins
            if np.einsum('i->',s_slopes[shot_index]) != 0: #handle 0 slope shots ex. short black screen
                s_curr = gb_.check_side(shot_index, t_pts, s_mins[shot_index], -t_ext["slope"])
            else:
                s_curr = -1
            s_pts["crf"][shot_index] = t_pts["crf"][s_curr]
            s_pts["rate"][shot_index] = t_pts["rate"][shot_index][s_curr]
            s_pts["dist"][shot_index] = t_pts["dist"][shot_index][s_curr]
            
        if np.einsum('i->',s_pts[tn]) > tv: #if current opt go beyond the target
            if tn == "dist":
                t_ext["l"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])] #new total point
                curr_opt["l"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["r"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])]
                curr_opt["r"] = s_pts["crf"].copy()
        else:
            if tn == "dist":
                t_ext["r"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])] #new total point
                curr_opt["r"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["l"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])]
                curr_opt["l"] = s_pts["crf"].copy()
        t_ext["slope"] = gb_.compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])
    
    if tn == "dist":
        return curr_opt["r"]
    elif tn == "rate":
        return curr_opt["l"]