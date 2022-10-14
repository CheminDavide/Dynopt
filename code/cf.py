def as_fit(x, a, b, c):
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