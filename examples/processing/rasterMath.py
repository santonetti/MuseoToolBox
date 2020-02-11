# -*- coding: utf-8 -*-
"""
Basics to use rasterMath
===============================================================

Compute substract and addition between two raster bands.

"""

##############################################################################
# Import librairies
# -------------------------------------------

from museotoolbox.processing import RasterMath
from museotoolbox import datasets
import numpy as np
##############################################################################
# Load HistoricalMap dataset
# -------------------------------------------

raster,vector = datasets.load_historical_data()

##############################################################################
# Initialize rasterMath with raster
# ------------------------------------

rM = RasterMath(raster)
rM._iter_block
print(rM.get_random_block())

##########################
# Let's suppose you want compute the difference between blue and green band.
# I suggest you to define type in numpy array to save space while creating the raster!

X = rM.get_random_block()

 
sub = lambda X : np.array((X[:,0]-X[:,1])).astype(np.int16) 


rM.add_function(sub,out_image='/tmp/sub_lambda.tif')
###########################################################
# Use a python function to use arguments
# ----------------------------------------

def sub(X,band1=0,band2=1):
    outX = np.array((X[:,band1]-X[:,band2])).astype(np.int16)
    return outX

#################################################################
# We can add keyword argument in the addFunction.
# This function is going to substract band2 from band 1 
import time
t=time.time()
rM = RasterMath(raster)
rM.add_function(sub,out_image='/tmp/sub.tif',band1=1,band2=0,compress='high')

#####################
# Run the script

rM.run()
print(time.time()-t)
#######################
# Plot result

from osgeo import gdal
from matplotlib import pyplot as plt 
src = gdal.Open('/tmp/sub.tif')
plt.imshow(src.ReadAsArray())

###########################################################
# Use a python function for spatial function
# -------------------------------------------

def mean_band1(X):
    outX = np.mean(X[...,0])
    return outX

###############################################################################
# You may want to filter an image with a spatial filter (mean filter for instance).

rM = RasterMath(raster)
rM.add_spatial_function(mean_band1, out_image='/tmp/mean_band1.tif', offset=1)
rM.run()

#######################
# Plot result

from osgeo import gdal
from matplotlib import pyplot as plt 
src = gdal.Open('/tmp/mean_band1.tif')
plt.imshow(src.ReadAsArray())
