
# Basic reading support for AFNI in Python

This is a quick-and-dirty module to read AFNI BRIK/HEAD files in Python. I did very little testing, so please use with caution and if you find bugs, send me your suggested changes in exchange for my eternal gratitude!



Usage (assumes that you have `TT_N27+tlrc` AFNI BRIK/HEAD files sitting in the directory where you run this from):

```{python}
import afni
header,brik = afni.read('TT_N27+tlrc') # reads TT_N27+tlrc.{HEAD|BRIK}
```

That's it!

I also include an Jupyter notebook that shows how you can read AFNI data files and then work with it in Python. For that to work, you have to For example BRIK/HEAD files, go [here](https://afni.nimh.nih.gov/pub/dist/src/) and download!

Under Linux/Mac OS you can download these with `wget` (assuming that you have `wget` installed):

```
wget https://afni.nimh.nih.gov/pub/dist/src/TT_N27+tlrc.HEAD
wget https://afni.nimh.nih.gov/pub/dist/src/TT_N27+tlrc.BRIK.gz
gunzip TT_N27+tlrc.BRIK.gz
```




## TODO

* Let Python read compressed (gzipped) `.BRIK` files.
* Test the that we scale values correctly (based on `BRICK_FLOAT_FACS` in the header).
* Integrate this into [nibabel](http://nipy.org/nibabel/).
