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
    return -(yl-yr)/(xl-xr)

def check_side(s):
    """
    Check if, when drawing a line intersectin a point with a given slope, none of the points are in the left side of the line.
    The direction of the line is lower-right to upper-left.

    Input:
    - s : int
        Shot index
    Output:
    - out : np.array(num_scenes)
        Updated list of intervals with closest slope to the total
    """
    m = -t_ext["slope"]
    count = 1
    while count > 0:
        l0 = [(m*t_pts["rate"][s][s_mins[s]] - t_pts["dist"][s][s_mins[s]])/m,0]
        l1 = [0,t_pts["dist"][s][s_mins[s]] - m*t_pts["rate"][s][s_mins[s]]]
        count = 0
        for i in range(0, len(t_pts["dist"][s])):
            py = t_pts["dist"][s][i]
            px = t_pts["rate"][s][i]
            crss = (l1[0] - l0[0])*(py - l0[1]) - (px - l0[0])*(l1[1] - l0[1])
            if crss > 0.1:
                s_mins[s] = i
                count += 1
    return s_mins[s]

def run(ti, tn, tv):
    print("TODO")