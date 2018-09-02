import numpy as np
import lifeparsers
import re


def mkeven_integer(arr):
    # force even size
    return np.pad(
        arr, ((arr.shape[0] % 2, 0), (arr.shape[1] % 2, 0)), "constant"
    ).astype(np.uint8)


def pack_callahan(arr):
    # pack into 4 bit 2x2 cell format
    return (
        arr[::2, ::2]
        + (arr[1::2, ::2] << 1)
        + (arr[::2, 1::2] << 2)
        + (arr[1::2, 1::2] << 3)
    )


def unpack_callahan(cal_arr):
    # unpack from 4 bit 2x2 cell format into standard array
    unpacked = np.zeros((cal_arr.shape[0] * 2, cal_arr.shape[1] * 2), dtype=np.uint8)
    unpacked[::2, ::2] = cal_arr & 1
    unpacked[1::2, ::2] = (cal_arr >> 1) & 1
    unpacked[::2, 1::2] = (cal_arr >> 2) & 1
    unpacked[1::2, 1::2] = (cal_arr >> 3) & 1
    return unpacked


# parse a b3s23 style rule
def parse_rule(rule):
    birth_survive = re.findall(r'[bB]([0-9]+)\s*\/?\s*[sS]([0-9]+)', rule)[0]
    def digits(seq):
        return [int(d) for d in seq]        
    return  digits(birth_survive[0]), digits(birth_survive[1])    


# table maps 16 state cell, encoded as:
# ab
# cd
# packed = a + (b<<1) + (c<<2) + (d<<3)
# to RGBA

def callahan_colour_table():
    from colorsys import yiq_to_rgb
    colour_table = np.ones((16,4), dtype=np.uint8)
    for iv in range(16):
        a = iv & 1
        b = (iv>>1) & 1
        c = (iv>>2) & 1
        d = (iv>>3) & 1
        y = (a+b+c+d) / 4.0
        i = ((a-b) + (c-d)) / 3.0
        q = ((a-c) + (b-d)) / 3.0        
        colour_table[iv, :3] = [int(x*255) for x in yiq_to_rgb(y, i, q)]
    return colour_table

        

def create_callahan_table(rule='b3s23'):
    """Generate the lookup table for the cells."""    
    # map predecessors to successor
    s_table = np.zeros((16, 16, 16, 16), dtype=np.uint8)
    # map 16 "colours" to 2x2 cell patterns

    birth, survive = parse_rule(rule)
    
    # apply the rule to the 3x3 block of cells
    def apply_rule(*args):
        n = sum(args[1:])
        ctr = args[0]
        if ctr and n in survive:
            return 1
        if not ctr and n in birth:
            return 1
        return 0

    # abcd
    # eFGh
    # iJKl
    # mnop

    # pack format
    # ab
    # cd
    # packed = a + (b<<1) + (c<<2) + (d<<3)

    # generate all 16 bit strings
    for iv in range(65536):
        bv = [(iv >> z) & 1 for z in range(16)]
        a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p = bv

        # compute next state of the inner 2x2
        nw = apply_rule(f, a, b, c, e, g, i, j, k)
        ne = apply_rule(g, b, c, d, f, h, j, k, l)
        sw = apply_rule(j, e, f, g, i, k, m, n, o)
        se = apply_rule(k, f, g, h, j, l, n, o, p)

        # compute the index of this 4x4
        nw_code = a | (b << 1) | (e << 2) | (f << 3)
        ne_code = c | (d << 1) | (g << 2) | (h << 3)
        sw_code = i | (j << 1) | (m << 2) | (n << 3)
        se_code = k | (l << 1) | (o << 2) | (p << 3)

        # compute the state for the 2x2
        next_code = nw | (ne << 1) | (sw << 2) | (se << 3)

        # get the 4x4 index, and write into the table

        s_table[nw_code, ne_code, sw_code, se_code] = next_code

    return s_table


def pack_life(lif):
    # pack into 4 bit format
    lif_int = mkeven_integer(lif)
    packed = pack_callahan(lif_int)
    return packed


def load_life(fname):
    return lifeparsers.to_numpy(lifeparsers.autoguess_life_file(fname)[0])
