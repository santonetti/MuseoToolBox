# -*- coding: utf-8 -*-
"""
Spatial Leave-One-SubGroup-Out (SLOSGO)
======================================================

This example shows how to make a Spatial Leave-One-Out using subgroup,
called here a Spatial Leave-One-SubGroup-Out.

In this example, it shows how to use just once a raster.

"""

##############################################################################
# Import librairies
# -------------------------------------------

from MuseoToolBox.crossValidationTools import SpatialLeaveOneSubGroupOut
from MuseoToolBox import datasets
##############################################################################
# Load HistoricalMap dataset
# -------------------------------------------

raster,vector = datasets.getHistoricalMap()
field = 'Class'
subGroup = 'uniquefid'

##############################################################################
# Create CV
# -------------------------------------------

SLOSGO = SpatialLeaveOneSubGroupOut(raster,vector,field,subGroup,
                                    distanceThresold=20,
                                    random_state=12,verbose=False)

###############################################################################
# .. note::
#    There is no need to specify a bandPrefix. 
#    If bandPrefix is not specified, scipt will only generate the centroid

for tr,vl in SLOSGO.split():
    print(tr.shape,vl.shape)

#############################################
# Draw image
    
import numpy as np
from matplotlib import pyplot as plt
fig, ax = plt.subplots()
plt.ylim(40,150)
plt.xlim(40,150)


plt.scatter(np.random.randint(100,150,50),np.random.randint(100,150,50),alpha=.8)
plt.scatter(80,80, s=80*100,alpha=.8)
plt.scatter(80,80,color='green',s=40)
for i in np.random.randint(72,88,20):
    plt.scatter(i,np.random.randint(72,88),color='green',s=40)
plt.text(92,82,'Validation pixels\n(same group)',size=12)
plt.text(100,120,'Training pixels',size=12, ha='right')
plt.text(46,52,'Buffer of spatial auto-correlated pixels')
plt.axis('off')

plt.show()
