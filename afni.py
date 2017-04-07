
"""


Basic support for reading the AFNI BRIK/HEAD file format.
This is quite quick-and-dirty, so please use with caution.


Floris van Vugt, April 2017

"""


import re
import numpy as np
import os




def read_header(fname):
    """ 
    Reads AFNI header file. That is, reads the HEAD from a BRIK/HEAD file pair.
    
    Arguments
    fname : the filename to be read (if it doesn't end in .HEAD this will be appended)
    
    Returns
    dict of key-values representing the header contents
    """ 
    
    if fname.endswith('.'):
        fname+="HEAD"
    if not fname.endswith('.HEAD'):
        fname+=".HEAD"
    
    # Read the file contents
    headf = open(fname,'r').read()
    
    # Now parse the contents
    remainder = headf[:]

    # No, this is not an insult, it's a pattern that matches the beginning of a chunk,
    # i.e. type=something, name=something_else, count=a_number
    chunkhead = re.compile(r'type\s*=\s*(integer|float|string)-attribute\s*name\s*=\s*(\w+)\s*count\s*=\s*(\d+)')

    header = {}
    types = {}

    m = re.search(chunkhead,remainder)

    type_regexp = {
        "integer":"[+-]?[0-9]",
        "float":"[-+]?(\d+([.,]\d*)?|[.,]\d+)([eE][-+]?\d+)?" # source: http://stackoverflow.com/questions/4703390/how-to-extract-a-floating-number-from-a-string
    }

    # While there is another chunk to be found...
    while m:

        # Parse the type/name/count fields
        endpos = m.end()
        (tp,name,count) = m.groups()
        count = int(count)
        header[name]=count
        types[name]=tp
        #print(m.start(),tp,name,count)

        # The rest of the file...
        remainder = remainder[endpos:]

        # Now read the actual contents
        if tp=='integer' or tp=="float":
            # Set up a regexp that will capture the next "count" ints
            contents = re.match(r'(\s*(%s)+){%i}'%(type_regexp[tp],count),remainder)
            cast = int if tp=="integer" else float
            if contents:
                values = [ cast(i) for i in contents.group().split() ]
                header[name]=values if count>1 else values[0]
            else:
                raise ValueError("Failed to parse contents for %s"%name)
                
            remainder = remainder[contents.end():]

        elif tp=="string":
            contents = re.match(r'\s*\'(.{%i})~'%(count-1),remainder,re.DOTALL)
            if contents:
                header[name]=contents.group(1)
            else:
                raise ValueError("Failed to parse contents for %s"%name)
                
            remainder = remainder[contents.end():]
            
        else:
            raise ValueError("Unknown data type %s for %s"%(tp,name))

            
        # Set up for the next iteration of the loop
        m = re.search(chunkhead,remainder)
        
    return header #,types







def read_brik(fname,header):
    """ Reads BRIK file. Presupposes that we have parsed the .HEAD file and 
    supplied at least the relevant portion of it.
    
    Arguments
    fname : the filename to be read (.BRIK will be added if necessary)
    header : the header information, a set of key-values
    
    Returns
    array containing the data
    """
    
    if fname.endswith('.'):
        fname+="BRIK"
    if not fname.endswith('.BRIK'):
        fname+=".BRIK"
        
    # Determine the size of the data to be read (this comes from the header)
    nx,ny,nz=header["DATASET_DIMENSIONS"][0],header["DATASET_DIMENSIONS"][1],header["DATASET_DIMENSIONS"][2]
    
    ntp = header["DATASET_RANK"][1]
    n = nx*ny*nz*ntp #(Info.DATASET_DIMENSIONS(1) .* Info.DATASET_DIMENSIONS(2) .* Info.DATASET_DIMENSIONS(3) .* Info.DATASET_RANK(2)
    
    
    # Determine the datum type stored at each brick
    bt = header.get("BRICK_TYPES",None)


    # Check whether the brick data type is a list, in which case the different bricks could have
    # different data types, which we are too lazy here to support.
    if (type(bt) is list) or (type(bt) is tuple):
        if len(bt)>1:
            # If this is a list of data types but they are really all the same data type, then it's still okay.
            if len(list(set(bt)))==1:
                bt = bt[0]
            else:
                raise ValueError("Error: currently not supporting reading bricks with different data types.")
        else:
            bt = bt[0]

    if bt==0:
        dt = "B"              # not tested;    0 = byte    (unsigned char; 1 byte)
    elif bt==1: 
        dt = "h"              # tested;        1 = short   (2 bytes, signed)
    elif bt==2:
        dt = "i"              # not tested;    2 = int
    elif bt==3:
        dt = "f"              # not tested;    3 = float   (4 bytes, assumed to be IEEE format)
    elif bt==4:
        dt = "d"              # not tested;    4 = double  
    elif bt==5:
        dt = "D"              # not tested     5 = complex (8 bytes: real+imaginary parts)
    else:
        raise ValueError("Unknown data type (BRICK_TYPES=%i)"%bt)

    
    bo = header.get("BYTEORDER_STRING",None)
    if bo == "LSB_FIRST": #   "<" means little-endian (LSB first)
        bo_str = "<"
    elif bo == "MSB_FIRST": #   ">" means big-endian (MSB first)
        bo_str = ">"
    else:
        bo_str = "="

    dt = np.dtype(bo_str+dt)

    # Check that the file is indeed of the correct size
    fsize = os.path.getsize(fname)
    if fsize!=dt.itemsize*n: 
        raise ValueError("Error reading BRIK file, file size is %i but I expected to read %i voxels."%(fsize,n))

    
    V = np.fromfile(fname, dtype=np.dtype(dt),count=n)
    
    #V = fread(fidBRIK, n) , [Opt.OutPrecision,typestr]);
    # For reshaping, the AFNI doc says:
    # The voxel with 3-index (i,j,k) in a sub-brick
    #                   is located at position (i+j*nx+k*nx*ny), for
    #                   i=0..nx-1, j=0..ny-1, k=0..nz-1.  Each axis must
    #                   have at least 2 points!
    # I think this corresponds to what Numpy calls Fortran-style ordering.
    V = np.reshape( V, (nx,ny,nz,ntp), order="F" )

    
    # Potentially we need to apply factors to the data (but be careful of overflows!)
    ff = header.get("BRICK_FLOAT_FACS",[])
    if (type(ff) is list) or (type(ff) is tuple):

        for (i,fact) in enumerate(ff):
            if i>=ntp:
                raise ValueError("Error: header defines BRICK_FLOAT_FACS for nonexistant time point.")
            if fact>0: # According to the AFNI specification, fact is non-negative
                V[:,:,:,i] = fact*V[:,:,:,i]
        
    else: # If FLOAT_FACS is not a list, then simply apply it to all volumes
        if ff>0:
            V = ff*V

    
    return V







def read(fname):
    """ Read AFNI data file (BRIK/HEAD).
    
    Arguments
    fname : the filename to be read
    
    Returns
    (header,brik) 
    header : a dict containing the header information
    brik : a multidimensional array containing the voxel data
    """
    
    header = read_header(fname)
    brik   = read_brik(fname,header)
    
    return (header,brik)
