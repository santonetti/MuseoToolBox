# -*- coding: utf-8 -*-
"""
Read fields from vector
======================================================

This example shows how to read fields values from
a vector file.
"""

##############################################################################
# Import librairies
# -------------------

import museotoolbox as mtb

##############################################################################
# Load HistoricalMap dataset
# ----------------------------

raster,vector = mtb.datasets.load_historical_data(low_res=True)

###############################################################################
# .. note::
#    If you have no memories on what the fields name are, simply put the vector path

try : 
    mtb.processing.read_vector_values(vector)
except Exception as e:
    print(e)

#############################################
# Read values from field 'Class'
# --------------------------------

Y,Name = mtb.processing.read_vector_values(vector,'Class','Type')
print(Y,Name)
print(Y.shape)

#############################################
# Read values from field beginning with 'C'
# -------------------------------------------
# As multiple fields can begin with C, function returns a column per field

C = mtb.processing.read_vector_values(vector,band_prefix='C')
print(C)
print(C.shape)


#############################################

from matplotlib import pyplot as plt
import numpy as np
plt.title('Number of polygons per label')
plt.bar(np.arange(np.unique(Y).size)+1,np.unique(Y,return_counts=True)[1])
