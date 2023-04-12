import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from scipy.integrate import cumtrapz
import code.global_ as gb_

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

def pts_disp(x,y,i,p):
    """
    Distribute points along the curve

    Input:
    - x : np.array(num_points)
        Computed rate values for current shot
    - y : np.array(num_points)
        Computed dist values for current shot
    - i : int
        Current point
    - p : list(3)
        Parameters of the function
    Output:
    - ty : np.array()
        Y value of the function
    """
    #number of points in between two init points
    ti = gb_.npts[i+1] - gb_.npts[i] + 1
    #ti linearly spaced numbers within the interval
    tx = np.linspace(x[i],x[i+1],num=ti,endpoint=True)
    #linear interpolation of points
    ty = eq_fit(tx,*p)
    #cumulative trapezoid (n order) integrated value of ty(tx)
    cdf = cumtrapz(ty, tx, initial=0)
    #normalize [0,1]
    cdf *= (1/cdf[-1])
    #approximated function from tx points according to its distribution function
    intfunc = interp1d(cdf, tx, fill_value="extrapolate")
    #new x points
    o = intfunc(np.linspace(0, 1, ti, endpoint=True))
    return o[:-1]

def run(ti, tn, tv):
    """
    Lagrangian implementation with curve fitting

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
                "r": np.zeros(gb_.num_shots, dtype=int)} #new optimal interval bounds
    prev_opt = {"l": np.ones(gb_.num_shots, dtype=int),
                "r": np.ones(gb_.num_shots, dtype=int)} #previous optimal interval bounds
    t_ext = {"l": [], "r": [], "slope": 0.0} #general slope
    init_pts = {"rate": np.zeros((gb_.num_shots, gb_.config["ENC"]["NUM_PTS"])),
            "dist": np.zeros((gb_.num_shots, gb_.config["ENC"]["NUM_PTS"]))} #info encoded shots
    t_pts = {"crf": np.arange(gb_.config["ENC"]["CRF_RANGE"][1],gb_.config["ENC"]["CRF_RANGE"][0]-1,-1,dtype=int),
            "rate": np.zeros((gb_.num_shots, gb_.config["ENC"]["CRF_RANGE"][1]-gb_.config["ENC"]["CRF_RANGE"][0]+1)),
            "dist": np.zeros((gb_.num_shots, gb_.config["ENC"]["CRF_RANGE"][1]-gb_.config["ENC"]["CRF_RANGE"][0]+1))}
    s_slopes = np.zeros((gb_.num_shots, gb_.config["ENC"]["CRF_RANGE"][1]-gb_.config["ENC"]["CRF_RANGE"][0])) #single tan slopes
    s_pts = {"crf": np.zeros(gb_.num_shots, dtype=int),
            "rate": np.zeros(gb_.num_shots),
            "dist": np.zeros(gb_.num_shots)} #info current optimal combination
    
    for shot_index in range(gb_.num_shots): #for each shot
        for n_crf, val_crf in enumerate(gb_.npts): #for each init crf
            if ti == 0 and gb_.config["DEBUG"]["ENC"]:
                path = gb_.encode(shot_index, val_crf) #encoding
                gb_.assess(shot_index, path) #quality assessment
                gb_.set_results(shot_index, int(val_crf), path)
            #store results in t_pts dictionary, weighted by duration
            init_pts["rate"][shot_index][n_crf] = gb_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            init_pts["dist"][shot_index][n_crf] = gb_.dist_max_val - gb_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
        par, cov = curve_fit(eq_fit, init_pts["rate"][shot_index], init_pts["dist"][shot_index],
                             bounds=((0,-np.inf,0),np.inf)) #fitting
        x = np.flip(init_pts["rate"][shot_index])
        xnew = t_pts["rate"][shot_index] = np.append(np.concatenate([pts_disp(x,init_pts["dist"][shot_index],i,par)
                                    for i in range(gb_.config["ENC"]["NUM_PTS"]-1)]),x[-1]) \
                                    * gb_.data["shots"][shot_index]["duration"] / gb_.duration #estimate x
        y = init_pts["dist"][shot_index]
        crf = gb_.npts
        t_pts["dist"][shot_index] = np.append(np.concatenate([np.interp(eq_fit(xnew[crf[i]-crf[0]:crf[i+1]-crf[0]+1],*par),
                                    (eq_fit(xnew[crf[i]-crf[0]:crf[i+1]-crf[0]+1],*par).min(),
                                     eq_fit(xnew[crf[i]-crf[0]:crf[i+1]-crf[0]+1],*par).max()),
                                     (y[len(crf)-i-2],y[len(crf)-i-1]))[:-1] for i in range(len(crf)-1)]),y[0]) \
                                    * gb_.data["shots"][shot_index]["duration"] / gb_.duration #compute y
        for n_crf in range(1,gb_.config["ENC"]["CRF_RANGE"][1]-gb_.config["ENC"]["CRF_RANGE"][0]+1):
            s_slopes[shot_index][n_crf-1] = gb_.compute_slope(t_pts["rate"][shot_index][n_crf],
                                                          t_pts["dist"][shot_index][n_crf],
                                                          t_pts["rate"][shot_index][n_crf-1],
                                                          t_pts["dist"][shot_index][n_crf-1])
    r_min = np.einsum('ij->j',t_pts["rate"])[0]
    r_max = np.einsum('ij->j',t_pts["rate"])[-1]
    d_min = np.einsum('ij->j',t_pts["dist"])[-1]
    d_max = np.einsum('ij->j',t_pts["dist"])[0]
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
    while not (curr_opt["r"] == prev_opt["r"]).all() or not (curr_opt["l"] == prev_opt["l"]).all():
        prev_opt = curr_opt.copy() #keep track of the previous optimal combination
        diffs = abs(s_slopes - t_ext["slope"]) #difference between all and current slope
        s_mins = np.argmin(diffs, axis=1) #find the min difference
        for shot_index in range(0,gb_.num_shots):
            if np.einsum('i->',s_slopes[shot_index]) != 0: #handle 0 slope shots ex. short black screen
                s_curr = gb_.check_side(shot_index, t_pts, s_mins[shot_index], -t_ext["slope"])
            else:
                s_curr = -1
            s_pts["crf"][shot_index] = t_pts["crf"][s_curr]
            s_pts["rate"][shot_index] = t_pts["rate"][shot_index][s_curr]
            s_pts["dist"][shot_index] = t_pts["dist"][shot_index][s_curr]
        
        if np.einsum('i->',s_pts[tn]) > tv: #if current opt go beyond the target
            if tn == "dist":
                t_ext["l"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])] #new general point
                curr_opt["l"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["r"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])]
                curr_opt["r"] = s_pts["crf"].copy()
        else:
            if tn == "dist":
                t_ext["r"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])] #new general point
                curr_opt["r"] = s_pts["crf"].copy()
            elif tn == "rate":
                t_ext["l"] = [np.einsum('i->',s_pts["rate"]), np.einsum('i->',s_pts["dist"])]
                curr_opt["l"] = s_pts["crf"].copy()
        t_ext["slope"] = gb_.compute_slope(t_ext["l"][0],t_ext["l"][1],t_ext["r"][0],t_ext["r"][1])
                
    if tn == "dist":
        return curr_opt["r"]
    elif tn == "rate":
        return curr_opt["l"]