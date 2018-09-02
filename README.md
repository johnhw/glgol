# glgol
GLSL GoL shader test

Implements Paul Callahan's fast 2x2 block Life algorithm, entirely on the GPU. Implemented as GLSL shaders, using a lookup table stored in a small (256x256) single channel texture. This provides a relatively fast algorithm which will work for any outer-totalistic CA.

It would probably be more sensible to use compute shaders rather than colour buffers for this purpose.

### Structure

* The original pattern is packed into a 16 state format (2x2 binary cells -> one 16 state "block").

    ab
    cd

    packed = a + (b << 1) + (c << 2) + (d << 3)


* A lookup table mapping every 4x4 "superblock" to a 2x2 successor is created and stored as a texture. This encodes the Life rule
(or any other outer-totalistic rule)

    4x4    -> 2x2 centre

    abcd
    eFGh   -> F'G'   
    iJKl      J'K'
    mnop  

Then split into 4 2x2 parts, with the next NW' being the centre block in the next generation (note this introduces an offset, but this is easily compensated for)

    NW = ab   NE =  cd
         eF         Gh

    SE = iJ   SW =  Kl
         mn         op

    NW' = F'G'
          J'K'

The final table maps each 2x2 superblock of 2x2 blocks to a new 2x2 block NX

    NW NE  -> NX _
    SW SE     _  _

* In each frame:
    * A shader (`gol_shader`) computes the successors of each block in the next frame
    * A second shader (`unpack_shader`) then unpacks from the block format back into the 2x2 binary cells for display



### 2x2 Algorithm
This is Paul's original explanation of the algorithm:

> But there's a very nice kind of spatial packing that just happens to
> work for 2x2 patches (has it been used elsewhere?): Observe, trivially,
> that every 2x2 patch is determined by the 4x4 patch obtained by
> adding a one-cell border around it. This patch is itself composed
> of 4 2x2 patches. They aren't aligned with the center patch, but this
> turns out not be much of a problem.
> Consider a 16-state CA based on an asymmetric 4-cell neighborhood
> consisting of a cell and its eastern, southern, and south-eastern neighbors.
> Now we can embed 2x2 patches from any 2-state (Moore neighborhood or
> subset) CA into single cells on this CA. Suppose we derive the rule
> for determining the middle 2x2 patch from a 4x4 patch in the 2-state CA and
> express it as the rule of the 16-state CA. Then if we were to convert
> to the new CA, apply the rule, and convert back, we would have computed
> the original 2-state rule, except that every new state would be shifted
> north-west from where it should be. We can always compute the correction
> needed after applying a certain number of steps, so in fact, we can
> work primarily within the 16-state CA until we need to use the
> individual cells (alternatively, we could derive 2 16-state CAs that
> cancel either other's shifts when applied one after the other; I
> chose not to implement this in order to avoid code duplication).
> So, once you accept that the 16-state 4-cell neighborhood CA can embed
> your 2-state CA, the next question is how to compute its rule efficiently.
> Well, this too be done with row-majored-ordered lists of
> cell positions and states. In fact, it is a little easier than the
> straight Life code, because 2x2 neighborhoods can be scanned by maintaining
> just 2 pointers into the list. A 2x2 neighborhood of 16-state cells fits
> into 16 bits. Thus, the transition rule fits into a look-up table of
> 2^16 entries. Luckily, this introduces very low overhead on any modern
> computer. The table is generally a redundant representation of 4 overlapping
> 3x3 neighborhoods. The procedure that fills in the entries need not be
> optimized, and works with any 2-state Moore-neighborhood rule.
> I obtained the following times running rabbits for 17331 generations on
> a SPARC 5 (all compiled at the same optimization level with gcc):
> a) List of single cells: 56.2 seconds user time. (Unix time command)
> b) List of 2x2 patches: 12.8 seconds user time. (" " " )
> c) Xlife (G command): 32.3 seconds (timed with a stopwatch)
> Display updates complicate the problem of benchmarking Xlife. But the
> G command only keeps a running display of the number of generations
> finished (every hundred) and the above seems to be the fastest Xlife can
> generate the pattern in practice.
> Now that I have this code, I can probably run some experiments faster.
> On the other hand, even something as simple as the population checks
> to determine stability are complicated (slightly) by the new method.
> Checking if subpatterns are destroyed, determining connected oscillators, etc.
> are all much easier after first unpacking the 2x2 patches into a
> list of single cells.
> --Paul
> 8 November 1997