import numpy as np
def riaa_db(f):
    """Ideal RIAA playback response in dB, normalised to 0 dB at 1 kHz."""
    t1, t2, t3 = 3180e-6, 318e-6, 75e-6
    def h(f):
        s = 2j*np.pi*np.asarray(f, float)
        return (1+s*t2)/((1+s*t1)*(1+s*t3))
    return 20*np.log10(abs(h(f))/abs(h(1000.0)))
