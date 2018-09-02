# GLSL Game of Life shader test

Implements Paul Callahan's fast 2x2 block Life algorithm, entirely on the GPU. Implemented as GLSL shaders, using a lookup table stored in a small (256x256) single channel texture. This provides a relatively fast algorithm which will work for any outer-totalistic CA.

This approach rewrites the update algorithm from a process on 3x3 neighbourhoods of 2 state cells to an equivalent 16 state CA on 2x2 neighbourhoods, where each of these 16-state "supercells" represents a 2x2 block of the underlying binary CA. This clever trick reduces the number of accesses per update for a naive algorithm from 9N to 4N, with a simple 64K lookup table to look up the result of each neigbhourhood.

This is particularly easy to implement on GPUs, which have specific capability to sample 2x2 neighbourhoods for texture filtering purposes.

### Caveats
While the base algorithm is fast, it is unable to exploit any of the sparsity of the CA and every cell must be processed in each generation. Some type of tile based approach with relatively large subtiles (perhaps 128x128) might be a more efficient GPU based approach. 

## Implementation
The code is implemented in Python, using [ModernGL](https://github.com/cprogrammer1994/ModernGL) for OpenGL support, and [Pyglet](https://bitbucket.org/pyglet/pyglet/wiki/Home) to provide event and window management. A driver/GPU supporting OpenGL 4.3+ is required to provide storage buffers. Tested on an AMD R9 390.

### Structure

* The original pattern is packed into a 16 state format (2x2 binary cells -> one 16 state "block").

        +---+
        |a b|
        |c d|
        +---+

        # packed is a 4 bit integer code for one block
        packed = a + (b << 1) + (c << 2) + (d << 3)
        


* A lookup table mapping every 4x4 "superblock" to a 2x2 successor is created and stored as a texture. This encodes the Life rule
(or any other outer-totalistic rule). F' means the successor of cell F
in the next generation after applying the Life rule.


        4x4    ->     2x2 centre in next generation

       +-------+
       |a b c d|      +------+       
       |e F G h|   -> | F' G'|          
       |i J K l|      | J' K'|                   
       |m n o p|      +------+  
       +-------+  


This superblock is then split into 4 2x2 parts, with the NX' being the centre block in the next generation (note this introduces an offset, but this is easily compensated for)
 
             +---+         +---+
        NW = |a b|    NE = |c d|
             |e F|         |G h|
             +---+         +---+

             +---+         +---+
        SE = |i J|    SW = |K l|
             |m n|         |o p|
             +---+         +---+

             +----+
        NX'= |F'G'|
             |J'K'|
             +----+

The final table maps each 2x2 superblock of 2x2 blocks to a new 2x2 block NX, offset by one cell to the northwest.

        +-----+     +------+
        |NW NE|  -> |NX' * |
        |SW SE|     |*   * |
        +-----+     +------+

        lookup_table[NW, NE, SW, SE] = NW'        

This creates a 16x16x16x16 lookup table, each entry being a 4 bit code NW'. This is reshaped to a 256x256 array before upload to the GPU, as 4D
textures are not supported directly in OpenGL.

### OpenGL implementation

* In each frame:
    * A shader (`gol_shader`) computes the successors of each block in the next frame, writing to a texture-backed framebuffer.
    * A second shader (`unpack_shader`) unpacks from the block format back into the 2x2 binary cells for display in a second texture-backed framebuffer.
    * This is finally rendered onto a single textured quad (`tex_shader`) onto the screen.

                   +---------------+
                   | 16 state CA   |--->| unpack_shader |>-------+
                +->| NxN 1ch. tex. |                             |
                |  +---------------+             +-----------------+
                |    |                           |2 state CA       |
                |    +->| gol_shader |>-+        |2Nx2N 1 ch. tex. |
                |                       |        +-----------------+
                +-----------------------+          |
                   (next generation)               +--->| tex_shader |--> screen

            

#### Notes
* It might be more sensible to use compute shaders rather than colour framebuffers for this purpose.
* Atomic buffer operations are used to provide a cell population count
as the unpacking of cells progresses
* `texelFetch()` is used to look up exact entries in the lookup table.
* `texelGatherOffset()` is used to gather the four neighbours of a block in a single call.

The entire Life algorithm as run on the GPU is just:

        ivec4 q = ivec4(textureGatherOffset(lifeTex, texCoord, ivec2(-f,-f)).wxzy * 15);    
        nextGen = texelFetch(callahanLUT, ivec2((q.z * 16 + q.w), (q.x * 16 + q.y)), 0).x;    
where `f` is a frame offset (to compensate for pixel shift on each frame),
`lifeTex` is the sampler holding the current generation, `callahanLUT` is the sampler holding the lookup table, `nextGen` is the next generation as a 16-state block state.

### 2x2 Algorithm
This is Paul's original explanation of the algorithm:

> But there's a very nice kind of spatial packing that just happens to  
> work for 2x2 patches (has it been used elsewhere?): Observe, trivially,  
> that every 2x2 patch is determined by the 4x4 patch obtained by  
> adding a one-cell border around it. This patch is itself composed  
> of 4 2x2 patches. They aren't aligned with the center patch, but this  
> turns out not be much of a problem.   
>  
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
> 
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
>  
> a) List of single cells: 56.2 seconds user time. (Unix time command)  
> b) List of 2x2 patches: 12.8 seconds user time. (" " " )  
> c) Xlife (G command): 32.3 seconds (timed with a stopwatch)  
>  
> Display updates complicate the problem of benchmarking Xlife. But the  
> G command only keeps a running display of the number of generations  
> finished (every hundred) and the above seems to be the fastest Xlife can  
> generate the pattern in practice.  
> 
> Now that I have this code, I can probably run some experiments faster.  
> On the other hand, even something as simple as the population checks  
> to determine stability are complicated (slightly) by the new method.  
> Checking if subpatterns are destroyed, determining connected oscillators, etc.  
> are all much easier after first unpacking the 2x2 patches into a  
> list of single cells.  
> 
> --Paul  
> 8 November 1997  