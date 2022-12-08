import os #to access system folders
import json #to handle json files
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from scipy.integrate import cumtrapz
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

def eq_fit(x, a, b, c):
    """
    Define the function that allows to describe the trend of a set of points with a curve y=1/x

    Input:
    - x : float
        X value of the function
    - a : float
        Parameter of the function
    - b : float
        Parameter of the function
    - c : float
        Parameter of the function
    Output:
    - out : float
        Y value of the function
    """
    return a / (x + b) + c

def eq_slope(x, a):
    return a / (x ** 2)

def expand(x,i,p):
    ti = global_.npts[i+1]-global_.npts[i]
    tx = np.linspace(x[i],x[i+1],num=ti,endpoint=False)
    cps = cumtrapz(eq_fit(tx,*p), tx, initial=0)
    cps *= (1/cps[-1]) #normalize [0,1]
    intfunc = interp1d(cps, tx)
    ty = intfunc(np.linspace(0, 1, ti, endpoint=False))
    return ty

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
    t_ext = {"l": [], "r": [], "slope": 0.0} #general slope
    init_pts = {"rate": np.zeros((global_.num_shots, config["ENC"]["NUM_INTERVALS"])), \
            "dist": np.zeros((global_.num_shots, config["ENC"]["NUM_INTERVALS"]))} #info encoded shots
    t_pts = {"crf": np.arange(config["ENC"]["CRF_RANGE"][1],config["ENC"]["CRF_RANGE"][0]-1,-1,dtype=int), \
            "rate": np.zeros((global_.num_shots, config["ENC"]["CRF_RANGE"][1]-config["ENC"]["CRF_RANGE"][0]+1)), \
            "dist": np.zeros((global_.num_shots, config["ENC"]["CRF_RANGE"][1]-config["ENC"]["CRF_RANGE"][0]+1))}
    t_tan = np.zeros((global_.num_shots, config["ENC"]["CRF_RANGE"][1]-config["ENC"]["CRF_RANGE"][0]+1)) #single tan slopes
    s_pts = {"crf": np.zeros(global_.num_shots, dtype=int), \
            "rate": np.zeros(global_.num_shots), \
            "dist": np.zeros(global_.num_shots)} #info current optimal combination
    
    shot_index = 0
    for shot in sorted(os.listdir(config["DIR"]["REF_PATH"])): #for each shot
        for n_crf, val_crf in enumerate(global_.npts): #for each init crf
            if ti == 0 and global_.new_enc:
                path = global_.encode(shot, shot_index, val_crf) #encoding
                global_.assess(shot, path) #quality assessment
                global_.set_results(shot_index, int(val_crf), path)
            #store results in t_pts dictionary, weighted by duration
            r = global_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = 100 - global_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            init_pts["rate"][shot_index][n_crf] = r * global_.data["shots"][shot_index]["duration"] / global_.duration
            init_pts["dist"][shot_index][n_crf] = d * global_.data["shots"][shot_index]["duration"] / global_.duration
        par, cov = curve_fit(eq_fit, init_pts["rate"][shot_index], init_pts["dist"][shot_index], bounds=(0,np.inf))
        x = np.flip(init_pts["rate"][shot_index])
        #t_pts["rate"][shot_index] = np.append(np.concatenate([np.linspace(x[i],x[i+1], \
        #num=global_.npts[i+1]-global_.npts[i],endpoint=False) for i in range(config["ENC"]["NUM_INTERVALS"]-1)]),x[-1])
        t_pts["rate"][shot_index] = np.append(np.concatenate([expand(np.flip(init_pts["rate"][shot_index]),i,par) \
                                                              for i in range(config["ENC"]["NUM_INTERVALS"]-1)]),x[-1])
        t_pts["dist"][shot_index] = eq_fit(t_pts["rate"][shot_index], *par)
        t_tan[shot_index] = eq_slope(t_pts["rate"][shot_index], par[0])
        shot_index += 1
    t_rate = np.einsum('ij->j',t_pts["rate"]) #sum rate results per crf
    t_dist = np.einsum('ij->j',t_pts["dist"]) #sum dist results per crf
    t_ext["l"] = [t_rate[-1], t_dist[-1]] #last element, highest crfs ex.51
    t_ext["r"] = [t_rate[0], t_dist[0]] #first element, lowest crfs ex.0
    t_ext["slope"] = compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])
    
    #when new solution is the same as the past one
    while not (curr_opt["r"] == prev_opt["r"]).all() or not (curr_opt["l"] == prev_opt["l"]).all():
        prev_opt = curr_opt.copy() #keep track of the previous optimal combination
        diffs = abs(t_tan - t_ext["slope"]) #difference between all and current slope
        s_mins = np.argmin(diffs, axis=1) #find the min difference
        for shot_index in range(0,global_.num_shots):
            s_pts["crf"][shot_index] = t_pts["crf"][s_mins[shot_index]]
            s_pts["rate"][shot_index] = t_pts["rate"][shot_index][s_mins[shot_index]]
            s_pts["dist"][shot_index] = t_pts["dist"][shot_index][s_mins[shot_index]]
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
    