import numpy as np
import lifeparsers


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


def create_callahan_table():
    """Generate the lookup table for the cells."""
    successors = {}
    # map predecessors to successor
    s_table = np.zeros((16, 16, 16, 16), dtype=np.uint8)
    # map 16 "colours" to 2x2 cell patterns

    def life(*args):
        n = sum(args[1:])
        n |= args[0]  # if we or with the cell value, we can just test == 3
        if n == 3:
            return 1
        else:
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
        nw = life(f, a, b, c, e, g, i, j, k)
        ne = life(g, b, c, d, f, h, j, k, l)
        sw = life(j, e, f, g, i, k, m, n, o)
        se = life(k, f, g, h, j, l, n, o, p)

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
    unpacked = unpack_callahan(packed)

    assert np.allclose(lif_int, unpacked)
    return packed


def load_life(fname):
    return lifeparsers.to_numpy(lifeparsers.autoguess_life_file(fname)[0])
