import itertools #to combine options
import numpy as np #easy vector operations
import math #for operation with infinite
import copy #to create list shadow copies
import code.global_ as gb_

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
    s_pts = {"rate": np.zeros((gb_.num_shots, len(gb_.npts))), \
                 "dist": np.zeros((gb_.num_shots, len(gb_.npts)))}
    t_pts = {"rate": np.zeros(len(gb_.npts)), \
                 "dist": np.zeros(len(gb_.npts))}
    crf_index = len(gb_.npts) - 1
    curr_crf = gb_.npts[-1]
    if tn == "dist":
        tv = gb_.dist_max_val - tv

    for shot_index in range(gb_.num_shots): #for each shot
        for n_crf, val_crf in enumerate(gb_.npts):
            if ti == 0 and gb_.config["DEBUG"]["ENC"]:
                path = gb_.encode(shot_index, val_crf) #encoding
                gb_.assess(shot_index, path) #quality assessment
                gb_.set_results(shot_index, int(val_crf), path)
            r = gb_.data["shots"][shot_index]["assessment"]["rate"][val_crf]
            d = gb_.data["shots"][shot_index]["assessment"]["dist"][val_crf]
            s_pts["rate"][shot_index][n_crf] = r * gb_.data["shots"][shot_index]["duration"] / gb_.duration
            s_pts["dist"][shot_index][n_crf] = d * gb_.data["shots"][shot_index]["duration"] / gb_.duration
    
    #iterate the points starting from the end until the target is no more satisfied
    while np.einsum('ij->j',s_pts[tn])[crf_index] < tv and crf_index != 0:
        curr_crf = gb_.npts[crf_index]
        crf_index -= 1
    
    if crf_index == len(gb_.npts) - 1: #if target is below min CRF metric value
        print("no encodings satisfy the target - encoding at min CRF")
    elif np.einsum('ij->j',s_pts[tn])[0] < tv: #if target is above max CRF
        print("no encodings satisfy the target - encoding at max CRF")
        curr_crf = gb_.npts[crf_index]
    elif tn == "dist":
        curr_crf = gb_.npts[crf_index]
    
    return np.zeros(gb_.num_shots) + curr_crf

