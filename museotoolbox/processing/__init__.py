#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# ___  ___                       _____           _______
# |  \/  |                      |_   _|         | | ___ \
# | .  . |_   _ ___  ___  ___     | | ___   ___ | | |_/ / _____  __
# | |\/| | | | / __|/ _ \/ _ \    | |/ _ \ / _ \| | ___ \/ _ \ \/ /
# | |  | | |_| \__ \  __/ (_) |   | | (_) | (_) | | |_/ / (_) >  <
# \_|  |_/\__,_|___/\___|\___/    \_/\___/ \___/|_\____/ \___/_/\_\
#
# @author:  Nicolas Karasiak
# @site:    www.karasiak.net
# @git:     www.github.com/nkarasiak/MuseoToolBox
# =============================================================================
"""
The :mod:`museotoolbox.processing` module gathers raster and vector tools.
"""
# general libraries
import os
import numpy as np
import tempfile
#from museotoolbox.processing import RasterMath


# spatial libraries
from osgeo import __version__ as osgeo_version
from osgeo import gdal, ogr


from ..internal_tools import ProgressBar, push_feedback

def image_mask_from_vector(
        in_vector, in_image, out_image, invert=False, gdt=gdal.GDT_Byte):
    """
    Create a image mask where polygons/points are the pixels to keep.

    Parameters
    ----------
    in_vector : str.
        Path of the vector file to rasterize.
    in_image : str.
        Path of the raster file where the vector file will be rasterize.
    out_image : str.
        Path of the file (.tif) to create.
    invert : bool, optional (default=False).
        invert=True make polygons/points with 0 values in out_image.
    gdt : int, optional (default=gdal.GDT_Byte).
        The gdal datatype of the rasterized vector.
    """
    rasterize(
        in_image,
        in_vector,
        None,
        out_image,
        invert=invert,
        gdt=gdt)


def get_gdt_from_minmax_values(max_value, min_value=0):
    """
    Return the Gdal DataType according the minimum or the maximum value.

    Parameters
    ----------
    max_value : int or float.
        The maximum value needed.
    min_value : int or float, optional (default=0).
        The minimum value needed.

    Returns
    -------
    gdalDT : int.
        gdal datatype.

    Examples
    ---------
    >>> get_gdt_from_minmax_values(260)
    2
    >>> get_gdt_from_minmax_values(16)
    1
    >>> get_gdt_from_minmax_values(16,-260)
    3
    """
    max_abs_value = np.amax(np.abs([max_value, min_value]))

    # if values are int
    if isinstance(max_abs_value, (int, np.integer)):
        if min_value >= 0:
            if max_value <= 255:
                gdalDT = gdal.GDT_Byte
            elif max_value > 255 and max_value <= 65535:
                gdalDT = gdal.GDT_UInt16
            elif max_value >= 65535:
                gdalDT = gdal.GDT_UInt32
        elif min_value < 0:
            if min_value > -65535:
                gdalDT = gdal.GDT_Int16
            else:
                gdalDT = gdal.GDT_Int32

    # if values are float
    if isinstance(max_abs_value, float):
        if max_abs_value > +3.4E+38:
            gdalDT = gdal.GDT_Float64
        else:
            gdalDT = gdal.GDT_Float32

    return gdalDT


def convert_dt(dt, to_otb_dt=False):
    """
    Return the datatype from gdal to numpy or from numpy to gdal.

    Parameters
    -----------
    dt : int or str
        gdal datatype from src_dataset.GetRasterBand(1).DataType.
        numpy datatype from np.array([]).dtype.name

    Returns
    --------
        dt : int or data type
            - For gdal, the data type (int).
            - For numpy, the date type (type).

    Examples
    ---------
    >>> _convert_dt(gdal.GDT_Int16)
    numpy.int16
    >>> _convert_dt(gdal.GDT_Float64)
    numpy.float64
    >>> _convert_dt(numpyDT=np.array([],dtype=np.int16).dtype.name)
    3
    >>> _convert_dt(numpyDT=np.array([],dtype=np.float64).dtype.name)
    7
    """
    from osgeo import gdal_array
    if isinstance(dt, int):
        is_gdal = True
    else:
        is_gdal = False

    if is_gdal is True:
        code = gdal_array.GDALTypeCodeToNumericTypeCode(dt)
    else:
        NP2GDAL_CONVERSION = {
            "uint8": 1,
            "int8": 3,
            "uint16": 2,
            "int16": 3,
            "uint32": 4,
            "int32": 5,
            "float32": 6,
            "float64": 7,
            "complex64": 10,
            "complex128": 11,
            "int64": 5,
            "uint64": 5
        }
        try:
            code = NP2GDAL_CONVERSION[dt]
            if dt.endswith('int64'):
                push_feedback(
                    'Warning : Numpy type {} is not recognized by gdal. Will use int32 instead'.format(dt))
        except BaseException:
            code = 7
            push_feedback(
                'Warning : Numpy type {} is not recognized by gdal. Will use float64 instead'.format(dt))
    if to_otb_dt:
        if is_gdal:
            code = _convert_gdal_to_otb_dt(dt)
        else:
            code = _convert_gdal_to_otb_dt(code)
    return code


def _convert_gdal_to_otb_dt(dt):
    """
    Convert Gdal DataType to OTB str format.

    Parameters
    ----------
    dt : int
        gdal datatype from src_dataset.GetRasterBand(1).DataType.

    Returns
    ----------
    otb_dt : str.
        The otb data type.

    Examples
    ---------
    >>> _convert_gdal_to_otb_dt(gdal.GDT_Float32)
    'float'
    >>> _convert_gdal_to_otb_dt(gdal.GDT_Byte)
    'uint8'
    >>> _convert_gdal_to_otb_dt(gdal.GDT_UInt32)
    'uint32'
    >>> _convert_gdal_to_otb_dt(gdal.GDT_CFloat64)
    'cdouble'
    """
    # uint8/uint16/int16/uint32/int32/float/double/cint16/cint32/cfloat/cdouble
    code = [
        'uint8',
        'uint8',
        'uint16',
        'int16',
        'uint32',
        'int32',
        'float',
        'double',
        'cint16',
        'cint32',
        'cfloat',
        'cdouble']

    if dt > len(code):
        otb_dt = ('cdouble')
    else:
        otb_dt = code[dt]

    return otb_dt


def extract_ROI(in_image, in_vector, *fields, **kwargs):
    """
    Extract raster values from Regions Of Interest in a vector file.

    Initially written by Mathieu Fauvel, improved by Nicolas Karasiak.

    Parameters
    -----------
    in_image : str.
        the name or path of the raster file, could be any file that GDAL can open.
    in_vector : str.
        A filename or path corresponding to a vector file.
        It could be any file that GDAL/OGR can open.
    *fields : str.
        Each field to extract label/value from.
    
    **kwargs : list of kwargs.
        - get_pixel_position : bool, optional (default=False).
        
        If `get_pixel_position=True`, will return pixel position in the image for each point.
        
        - only_pixel_position : bool, optional (default=False).
        
        If `only_pixel_position=True`, with only return pixel position for each point.
                
        - prefer_memory : bool, optional (default=True).
        
        If `prefer_memory=False`, will write temporary raster on disk to extract ROI values.
                
        - verbose : bool or int, optional (default=True).
        
        The higher is the int verbose, the more it will returns informations.

    Returns
    --------
    X : np.ndarray, size of (n_samples,n_features).
        The sample matrix.
        A n*d matrix, where n is the number of referenced pixels and d is the number of features.
        Each line of the matrix is a pixel.
    y : np.ndarray, size of (n_samples,).
        The label of each pixel.

    See also
    ---------
    museotoolbox.processing.read_vector_values : read field values from vector file.

    Examples
    ---------
    >>> from museotoolbox.datasets import load_historical_data
    >>> from museotoolbox.processing import extract_ROI
    >>> raster,vector= load_historical_data()
    >>> X,Y = extract_ROI(raster,vector,'Class')
    >>> X
    array([[ 213.,  189.,  151.],
       [ 223.,  198.,  158.],
       [ 212.,  188.,  150.],
       ...,
       [ 144.,  140.,  105.],
       [  95.,   92.,   57.],
       [ 141.,  137.,  102.]])
    >>> X.shape
    (12647,3)
    >>> Y
    [3 3 3 ..., 1 1 1]
    >>> Y.shape
    (12647,)
    """
    # generate kwargs value
    if 'verbose' in kwargs.keys():
        verbose = kwargs['verbose']
    else:
        verbose = False
    if 'get_pixel_position' in kwargs:
        get_pixel_position = kwargs['get_pixel_position']
    else:
        get_pixel_position = False
    if 'only_pixel_position' in kwargs:
        only_pixel_position = kwargs['only_pixel_position']
    else:
        only_pixel_position = False
    if 'prefer_memory' in kwargs:
        prefer_memory = kwargs['prefer_memory']
    else:
        prefer_memory = True
    # Open Raster
    raster = gdal.Open(in_image, gdal.GA_ReadOnly)
    if raster is None:
        raise ValueError('Impossible to open ' + in_image)
        # exit()
    # Convert vector to raster

    nFields = len(fields)

    if nFields == 0 or fields[0] == False:
        fields = [False]
    else:
        source = ogr.Open(in_vector)
        layer = source.GetLayer()
        np_dtypes = []
        ldefn = layer.GetLayerDefn()
        for f in fields:
            idx = ldefn.GetFieldIndex(f)
            if idx == -1:

                listFields = []
                for n in range(ldefn.GetFieldCount()):
                    fdefn = ldefn.GetFieldDefn(n)
                    if fdefn.name is not listFields:
                        listFields.append('"' + fdefn.name + '"')
                raise ValueError('Sorry, field "{}" is not available.\nThese fields are available : {}.'.format(
                    f, ', '.join(listFields)))

            fdefn = ldefn.GetFieldDefn(idx)
            fdefn_type = fdefn.type
            if fdefn_type < 4 or fdefn_type == 12:
                if fdefn_type > 1 and fdefn_type != 12:
                    np_dtype = np.float64
                else:
                    np_dtype = np.int64
            else:
                raise ValueError(
                    'Wrong type for field "{}" : {}. \nPlease use int or float.'.format(
                        f, fdefn.GetFieldTypeName(
                            fdefn.type)))
            np_dtypes.append(np_dtype)

    rois = []
    temps = []
    for field in fields:
        if prefer_memory:
            raster_in_mem = True
            image_field = 'MEM'
            data_src = rasterize(in_image, in_vector, field,
                                 out_image=image_field, gdt=gdal.GDT_Float64)

        else:

            raster_in_mem = False
            image_field = tempfile.mktemp('_roi.tif')
            rasterize(in_image, in_vector, field,
                      out_image=image_field, gdt=gdal.GDT_Float64)
            data_src = gdal.Open(image_field, gdal.GA_ReadOnly)
            temps.append(image_field)

        if data_src is None:
            raise Exception(
                'A problem occured when rasterizing {} with field {}'.format(
                    in_vector, field))
        if (raster.RasterXSize != data_src.RasterXSize) or (
                raster.RasterYSize != data_src.RasterYSize):
            raise Exception('Raster and vector do not cover the same extent.')

        rois.append(data_src)

    # Get block size
    band = raster.GetRasterBand(1)
    block_sizes = band.GetBlockSize()
    x_block_size = block_sizes[0]
    y_block_size = block_sizes[1]
    gdalDT = band.DataType
    del band

    # Get the number of variables and the size of the images
    d = raster.RasterCount
    nc = raster.RasterXSize
    nl = raster.RasterYSize

    # ulx, xres, xskew, uly, yskew, yres = raster.GetGeoTransform()

    if get_pixel_position is True or only_pixel_position is True:
        coords = np.array([], dtype=np.int64).reshape(0, 2)

    xDataType = convert_dt(gdalDT)

    # Read block data
    X = np.array([], dtype=xDataType).reshape(0, d)
    F = np.array([], dtype=np.int64).reshape(
        0, nFields)  # now support multiple fields

    # for progress bar
    if verbose:
        total = 100
        pb = ProgressBar(total, message='Reading raster values... ')

    for i in range(0, nl, y_block_size):
        if i + y_block_size < nl:  # Check for size consistency in Y
            lines = y_block_size
        else:
            lines = nl - i
        for j in range(0, nc, x_block_size):  # Check for size consistency in X
            if j + x_block_size < nc:
                cols = x_block_size
            else:
                cols = nc - j

            # for ProgressBar
            if verbose:
                currentPosition = (i / nl) * 100
                pb.add_position(currentPosition)
            # Load the reference data

            ROI = rois[0].GetRasterBand(1).ReadAsArray(j, i, cols, lines)

            t = np.nonzero(ROI)

            if t[0].size > 0:
                if get_pixel_position or only_pixel_position:
                    coordsTp = np.empty((t[0].shape[0], 2))

                    coordsTp[:, 0] = t[1] + j
                    coordsTp[:, 1] = t[0] + i

                    coords = np.concatenate((coords, coordsTp))

                # Load the Variables
                if not only_pixel_position:
                    # extract values from each field
                    if nFields > 0:
                        Ftemp = np.empty(
                            (t[0].shape[0], nFields), dtype=np.int64)
                        for idx, roiTemp in enumerate(rois):
                            roiField = roiTemp.GetRasterBand(
                                1).ReadAsArray(j, i, cols, lines)
                            Ftemp[:, idx] = roiField[t]

                        F = np.concatenate((F, Ftemp))

                    # extract raster values (X)
                    Xtp = np.empty((t[0].shape[0], d), dtype=xDataType)
                    for k in range(d):
                        band = raster.GetRasterBand(
                            k + 1).ReadAsArray(j, i, cols, lines)
                        Xtp[:, k] = band[t]

                    X = np.concatenate((X, Xtp))

    if verbose:
        pb.add_position(100)
    # Clean/Close variables
    # del Xtp,band
    roi = None  # Close the roi file
    raster = None  # Close the raster file

    # remove temp raster
    if raster_in_mem:
        for roi in temps:
            os.remove(roi)

    # generate returns
    if only_pixel_position:
        toReturn = coords
    else:
        if nFields > 0:
            toReturn = [X] + [F[:, f] for f in range(nFields)]
        else:
            toReturn = X

        if get_pixel_position:
            if nFields == 0:
                toReturn = [toReturn] + [coords]
            else:
                toReturn = toReturn + [coords]

    return toReturn


def rasterize(in_image, in_vector, in_field=False, out_image='MEM',
              gdt=gdal.GDT_Int16, invert=False):
    """
    Rasterize vector to the size of data (raster)

    Parameters
    -----------
    in_image : str.
        A filename or path corresponding to a raster image.
    in_vector : str.
        A filename or path corresponding to a vector file.
    in_field : str, optional (default=False).
        Name of the filed to rasteirze.
        If False, will rasterize the polygons or points with >0 value, and set the other values to 0.
    out_image : str, optional (default = 'MEM').
        A filename or path corresponding to a geotiff (.tif) raster image to save.
        'MEM' will store raster in memory.
    gdt : int, optional (default=gdal.GDT_Int16)
        gdal datatype.
    invert : bool, optional (default=False).
        if invert is True, polygons will have 0 values in the out_image.

    Returns
    --------
     dst_ds : gdal object
         The open dataset with gdal (essential if out_image is set to 'MEM')
    """

    data_src = gdal.Open(in_image)
    shp = ogr.Open(in_vector)

    lyr = shp.GetLayer()

    if out_image.upper() == 'MEM':

        driver = gdal.GetDriverByName('MEM')
        out_image = ''
        options = []
    else:

        driver = gdal.GetDriverByName('GTiff')
        options = ['COMPRESS=PACKBITS', 'BIGTIFF=IF_SAFER']

    dst_ds = driver.Create(
        out_image,
        data_src.RasterXSize,
        data_src.RasterYSize,
        1,
        gdt,
        options=options)
    dst_ds.SetGeoTransform(data_src.GetGeoTransform())
    dst_ds.SetProjection(data_src.GetProjection())

    if in_field is False or in_field is None:
        if invert == True:
            try:
                options = gdal.RasterizeOptions(inverse=invert)
                gdal.Rasterize(dst_ds, in_vector, options=options)
            except BaseException:
                raise Exception(
                    'Version of gdal is too old : RasterizeOptions is not available.\nPlease update.')
        else:
            #            gdal.Rasterize(dst_ds, vectorSrc)
            gdal.RasterizeLayer(dst_ds, [1], lyr, options=options)

        dst_ds.GetRasterBand(1).SetNoDataValue(0)
    else:
        options = ['ATTRIBUTE=' + in_field]
        gdal.RasterizeLayer(dst_ds, [1], lyr, None, options=options)

    data_src, shp, lyr = None, None, None

    return dst_ds


class RasterMath:
    """
    Read one or multiple rasters per block, and perform one or many functions to one or many geotiff raster outputs.
    If you want a sample of your data, just call :func:`~museotoolbox.processing.RasterMath.get_random_block`.

    The default option of rasterMath will return in 2d the dataset :
        - each line is a pixel with in columns its differents values in bands so masked data will not be given to this user.

    If you want to have the data in 3d (X,Y,Z), masked data will be given too (using numpy.ma).

    Parameters
    ----------
    in_image : str.
        Path of a gdal extension supported raster.
    in_image_mask : str or False, optional (default=False).
        If str, path of the raster mask. Value masked are 0, other are considered not masked.
        Use ``invert=True`` in :mod:`museotoolbox.processing.image_mask_from_vector` to mask only what is not in polygons.
    return_3d : bool, optional (default=False).
        Default will return a row per pixel (2 dimensions), and axis 2 (bands) are columns.
        If ``return_3d=True``, will return the block without reshape (not suitable to learn with `sklearn`).
    block_size : list or False, optional (default=[256,256]).
        Define the reading and writing block size. First element is the number of columns, second element the number of lines per block.
        If False, will use the block size as defined in in_image.
        To define later the block_size, use `custom_block_size`.
    message : str, optional (default='rasterMath...').
        If str, the message will be displayed before the progress bar.
    verbose : bool or int, optional (default=True).
        The higher is the int verbose, the more it will returns informations.
    _offsets : lst
        List of the offsets used in the different functions.
    _function_is_3d : bool
        False if the function is in 2d, True if the function is in 3d
        
    
    
    
    Examples
    ---------
    >>> import museotoolbox as mtb
    >>> raster,_= mtb.datasets.load_historical_data()
    >>> rM = mtb.processing.RasterMath(raster)
    Total number of blocks : 15
    >>> rM.add_function(np.mean,out_image='/tmp/test.tif',axis=1,dtype=np.int16)
    Using datatype from numpy table : int16.
    Detected 1 band for function mean.
    >>> rM.run()
    rasterMath... [########################################]100%
    Saved /tmp/test.tif using function mean
    """

    def __init__(self, in_image, in_image_mask=False, return_3d=False, block_size=[256, 256],
                 message='rasterMath...', verbose=True):

        self.verbose = verbose
        self.message = message
        self.driver = gdal.GetDriverByName('GTiff')

        # Load raster
        self.opened_images = []

        self.add_image(in_image)

        self.n_bands = self.opened_images[0].RasterCount
        self.n_columns = self.opened_images[0].RasterXSize
        self.n_lines = self.opened_images[0].RasterYSize

        # Get the geoinformation
        self.geo_transform = self.opened_images[0].GetGeoTransform()
        self.projection = self.opened_images[0].GetProjection()

        # Get block size
        band = self.opened_images[0].GetRasterBand(1)
        self.input_block_sizes = band.GetBlockSize()

        # input block size
        if block_size is False:
            self.x_block_size = self.input_block_sizes[0]
            self.y_block_size = self.input_block_sizes[1]
        else:
            self.x_block_size = block_size[0]
            self.y_block_size = block_size[1]
        self.block_sizes = [self.x_block_size, self.y_block_size]
        self.custom_block_size()  # set block size

        self.nodata = band.GetNoDataValue()
        self.dtype = band.DataType
        self.ndtype = convert_dt(band.DataType)
        self.return_3d = return_3d

        del band  # for memory purposes

        # Load in_image_mask if given
        self.mask = in_image_mask
        if self.mask:
            self.opened_mask = gdal.Open(in_image_mask)
            if self.opened_mask is None:
                raise ReferenceError(
                    'Impossible to open image ' + in_image_mask)

        # Initialize the output
        self.lastProgress = 0
        self.functions = []
        self.functionsKwargs = []
        self.outputs = []
        self.outputNoData = []
        self.options = []  # options is raster parameters
       
        # Initalize the run
        self._position = 0
        
        # Specific for spatial function (in 3D)
        self._offsets=[]
        self._function_is_3d=[]
        

    def add_image(
            self,
            in_image):
        """
        Add raster image.

        Parameters
        -----------
        in_image : str.
            Path of a gdal extension supported raster.
        """

        opened_raster = gdal.Open(in_image, gdal.GA_ReadOnly)
        if opened_raster is None:
            raise ReferenceError('Impossible to open image ' + in_image)

        sameSize = True

        if len(self.opened_images) > 0:
            if opened_raster.RasterXSize != self.opened_images[
                    0].RasterXSize or opened_raster.RasterYSize != self.opened_images[0].RasterYSize:
                sameSize = False
                push_feedback("raster {} doesn't have the same size (X and Y) as the initial raster.\n \
                      Museotoolbox can't add it as an input raster.".format(os.path.basename(in_image)))

        if sameSize:
            self.opened_images.append(opened_raster)

    def add_function(
            self,
            function,
            out_image,
            out_n_bands=False,
            out_np_dt=False,
            out_nodata=False,
            compress=True,
            **kwargs):
        """
        Add function to rasterMath.

        Parameters
        ----------
        function : function.
            Function to parse where the first argument is a numpy array similar to what :mod:`museotoolbox.processing.RasterMath.get_random_block()` returns.
        out_image : str.
            A path to a geotiff extension filename corresponding to a raster image to create.
        out_n_bands : int or False, optional (default=False).
            If False, will run the given function to find the number of bands to define in the out_image.
        out_np_dt : int or False, optional (default=False).
            If False, will run the given function to get the datatype.
        out_nodata : int, float or False, optional (default=False).
            If True or if False (if nodata is present in the init raster),
            will use the minimum value available for the given or found datatype.
        compress: bool or str, optional (default=True).
            If True, will use PACKBITS.
            If 'high', will use DEFLATE with ZLEVEL = 9 and PREDICTOR=2.
        **kwargs :
            kwargs are keyword arguments you need for the given function.

        See also
        ----------
        museotoolbox.processing.RasterMath.get_random_block : To test your function, parse the first argument with a random block
        museotoolbox.processing.convert_dt : To see conversion between numpy datatype to gdal datatype.
        museotoolbox.processing.get_dt_from_minmax_values : To get the gdal datatype according to a min/max value.
        """

        out_n_bands, out_np_dt= self._check_add_function(
             function,
             out_image,
             out_n_bands=out_n_bands,
             out_np_dt=out_np_dt,
             out_nodata=out_nodata,
             compress=compress,
             spatial=False,                  
             **kwargs)
        
        self._add_output(out_image, out_n_bands, out_np_dt)
        self.functions.append(function)      
        self.functionsKwargs.append(kwargs)
        
    def _check_add_function(
            self,
            function,
            out_image,
            out_n_bands=False,
            out_np_dt=False,
            out_nodata=False,
            compress=True,
            spatial=False,                  # spatial function : False or True
            **kwargs):
        """
        Check function before add_function or add_spatial_function to rasterMath
        
        Parameters :
        ----------
        function : function.
        out_image : str.
        out_n_bands : int or False, optional (default=False).
        out_np_dt : int or False, optional (default=False).
        out_nodata : int, float or False, optional (default=False).
        compress: bool or str, optional (default=True).
        spatial : bool. 
            If true, add_spatial_function
            If false, add_function
        **kwargs 
        """
        
        random_block = self.get_random_block(force_3d=spatial)
         
        random_block = random_block[:3,:3,...]
      
        if len(kwargs) > 0:
            randomBlock = function(random_block, **kwargs)
        else:
            kwargs = False
            randomBlock = function(random_block)
        
        if out_np_dt is False:
            dtypeName = randomBlock.dtype.name
            out_np_dt = convert_dt(dtypeName)
            push_feedback(
                'Using datatype from numpy table : {}.'.format(dtypeName))
        else:
            dtypeName = np.dtype(out_np_dt).name
            out_np_dt = convert_dt(dtypeName)

        # get number of bands
        randomBlock = self.reshape_ndim(randomBlock,force_3d=spatial)

        out_n_bands = randomBlock.shape[-1]
        need_s = ''
        if out_n_bands > 1:
            need_s = 's'

        if self.verbose:
            push_feedback(
                'Detected {} band{} for function {}.'.format(
                    out_n_bands, need_s, function.__name__))

        if self.options == []: # got from custom_raster_parameters
            self._init_raster_parameters(compress=compress)
        else:
            params = self.get_raster_parameters()
            arg_pos = next(
                (x for x in params if x.startswith('compress')), None)
            if arg_pos:
                # remove old compress arg
                params.pop(params.index(arg_pos))
            self.custom_raster_parameters(params)
            self._init_raster_parameters(compress=compress)

        if (out_nodata is True) or (self.nodata is not None) or (
                self.mask is not False):
            if np.issubdtype(dtypeName, np.floating):
                minValue = float(np.finfo(dtypeName).min)
            else:
                minValue = np.iinfo(dtypeName).min

            if not isinstance(out_nodata, bool):
                if out_nodata < minValue:
                    out_nodata = minValue
            else:
                out_nodata = minValue

            if self.verbose:
                push_feedback('No data is set to : ' + str(out_nodata))

        self.outputNoData.append(out_nodata)
        self._function_is_3d.append(spatial) #append 'True' for spatial function, else 'False'

        return(out_n_bands, out_np_dt)
        
    def add_spatial_function(
            self,
            function,
            out_image,
            out_n_bands=False,
            out_np_dt=False,
            out_nodata=False,
            compress=True,
            offset=0,
            **kwargs):
        
        """
        Add spatial function to rasterMath (we need spatial=True in _check_add_function)

        Parameters
        ----------
        function : function.
            Function to parse where the first argument is a numpy array similar to what :mod:`museotoolbox.processing.RasterMath.get_random_block()` returns.
        out_image : str.
            A path to a geotiff extension filename corresponding to a raster image to create.
        out_n_bands : int or False, optional (default=False).
            If False, will run the given function to find the number of bands to define in the out_image.
        out_np_dt : int or False, optional (default=False).
            If False, will run the given function to get the datatype.
        out_nodata : int, float or False, optional (default=False).
            If True or if False (if nodata is present in the init raster),
            will use the minimum value available for the given or found datatype.
        compress: bool or str, optional (default=True).
            If True, will use PACKBITS.
            If 'high', will use DEFLATE with ZLEVEL = 9 and PREDICTOR=2.
        **kwargs :
            kwargs are keyword arguments you need for the given function
        """
        out_n_bands, out_np_dt = self._check_add_function(
            function,
            out_image,
            out_n_bands=out_n_bands,
            out_np_dt=out_np_dt,
            out_nodata=out_nodata,
            compress=compress,
            spatial=True,                  
            **kwargs)
        
        self._add_output(out_image, out_n_bands, out_np_dt)
        self._offsets.append(offset)
        self.functions.append(function)      
        self.functionsKwargs.append(kwargs)
    

    def _init_raster_parameters(self, compress=True):

        self.options = []

        if compress:
            n_jobs = os.cpu_count() - 1
            if n_jobs < 1:
                n_jobs = 1

            self.options.append('BIGTIFF=IF_SAFER')

            if osgeo_version >= '2.1':
                self.options.append('NUM_THREADS={}'.format(n_jobs))

            if compress == 'high':
                self.options.append('COMPRESS=DEFLATE')
                self.options.append('PREDICTOR=2')
                self.options.append('ZLEVEL=9')
            else:
                self.options.append('COMPRESS=PACKBITS')
        else:
            self.options = ['BIGTIFF=IF_NEEDED']

    def get_raster_parameters(self):
        """
        Get raster parameters (compression, block size...)

        Returns
        --------
        options : list.
            List of parameters for creating the geotiff raster.

        References
        -----------
        As MuseoToolBox only saves in geotiff, parameters of gdal drivers for GeoTiff are here :
        https://gdal.org/drivers/raster/gtiff.html
        """
        if self.options == []:
            self._init_raster_parameters()
        return self.options

    def custom_raster_parameters(self, parameters_list):
        """
        Parameters to custom raster creation.

        Do not enter here blockXsize and blockYsize parameters as it is directly managed by :mod:`custom_block_size` function.

        Parameters
        -----------
        parameters_list : list.
            - example : ['BIGTIFF=IF_NEEDED','COMPRESS=DEFLATE']
            - example : ['COMPRESS=JPEG','JPEG_QUALITY=80']

        References
        -----------
        As MuseoToolBox only saves in geotiff, parameters of gdal drivers for GeoTiff are here :
        https://gdal.org/drivers/raster/gtiff.html

        See also
        ---------
        museotoolbox.processing.RasterMath.custom_block_size : To custom the reading and writing block size.
        """
        self.options = parameters_list

    def _managed_raster_parameters(self):
        # remove blockysize or blockxsize if already in options
        self.options = [val for val in self.options if not val.upper().startswith(
            'BLOCKYSIZE') and not val.upper().startswith('BLOCKXSIZE') and not val.upper().startswith('TILED')]
        self.options.extend(['BLOCKYSIZE={}'.format(
            self.y_block_size), 'BLOCKXSIZE={}'.format(self.x_block_size)])
        if self.y_block_size == self.x_block_size:
            if self.y_block_size in [64, 128, 256, 512, 1024, 2048, 4096]:
                self.options.extend(['TILED=YES'])

    def _add_output(self, out_image, out_n_bands, out_np_dt):
        if not os.path.exists(os.path.dirname(out_image)):
            os.makedirs(os.path.dirname(out_image))

        self._managed_raster_parameters()

        dst_ds = self.driver.Create(
            out_image,
            self.n_columns,
            self.n_lines,
            out_n_bands,
            out_np_dt,
            options=self.options
        )
        dst_ds.SetGeoTransform(self.geo_transform)
        dst_ds.SetProjection(self.projection)

        self.outputs.append(dst_ds)

    def _iter_block(self, get_block=False,                                 
                    y_block_size=False, x_block_size=False, offset=0):
        if not y_block_size:
            y_block_size = self.y_block_size
        if not x_block_size:
            x_block_size = self.x_block_size

        for row in range(0, self.n_lines, y_block_size):
            for col in range(0, self.n_columns, x_block_size):
                width = min(self.n_columns - col, x_block_size)
                height = min(self.n_lines - row, y_block_size)

                if get_block:
                    X = self._generate_block_array(
                        col, row, width, height, offset, mask=self.mask)
                    yield X, col, row, width, height
                else:
                    yield col, row, width, height

    def _generate_block_array(self, col, row, width, height, offset=0, mask=False, force_3d=False): 
        """
        Return block according to position and width/height of the raster.

        Parameters
        ----------
        col : int.
            the col.
        row : int
            the line.
        width : int.
            the width.
        height : int.
            the height.
        offset : int.
            the offset (optional)
        mask : bool.
            Use the mask (only if a mask if given in parameter of `RasterMath`.)
        force_3d : bool.
            If True, will force the array in 3d for a spatial function

        Returns
        -------
        arr : numpy array with masked values. (`np.ma.masked_array`)
        """
        arrs = []
        if mask:
            bandMask = self.opened_mask.GetRasterBand(1)
            arrMask = bandMask.ReadAsArray(
                col, row, width, height).astype(np.bool)
            if self.return_3d is False:
                arrMask = arrMask.reshape(width * height)
        else:
            arrMask = None

        for nRaster in range(len(self.opened_images)):
            
            offsetX_before=offsetX_after=offsetY_before=offsetY_after=offset
            
            if offset !=0 :
                #TODO : remove while loops for something better
                while col - offsetX_before < 0:
                    offsetX_before += -1
                while row - offsetY_before < 0:
                    offsetY_before += -1
                while col + width + offsetX_after >= self.n_columns +1: 
                    offsetX_after += -1
                while row + height + offsetY_after >= self.n_lines +1:
                    offsetY_after += -1
                # decreasing offsets when on the edge of the image to fit in with the boundaries
            
            arr = self.opened_images[nRaster].ReadAsArray(col-offsetX_before, row-offsetY_before,\
                                    width+offsetX_after+offsetX_before, height+offsetY_after+offsetY_before)

            if arr.ndim > 2:
                arr = np.moveaxis(arr, 0, -1)
            
            if not self.return_3d and not force_3d:      
                arr = arr.reshape(-1, arr.shape[-1])

            arr = self._filter_nodata(arr, arrMask)
            arrs.append(arr)

        if len(arrs) == 1:
            arrs = arrs[0]

        return arrs

    def _filter_nodata(self, arr, mask=None):
        """
        Filter no data according to a mask and to nodata value set in the raster.
        """
        arrShape = arr.shape
        arrToCheck = np.copy(arr)[..., 0]

        outArr = np.zeros((arrShape), dtype=self.ndtype)
        if self.nodata:
            outArr[:] = self.nodata

        if self.mask:
            t = np.logical_or((mask == False),
                              arrToCheck == self.nodata)
        else:
            t = np.where(arrToCheck == self.nodata)

        if self.return_3d:
            tmpMask = np.zeros(arrShape[:2], dtype=bool)
            tmpMask[t] = True
            tmpMask = np.repeat(tmpMask.reshape(*tmpMask.shape, 1), arr.shape[-1], axis=2)
            outArr = np.ma.masked_array(arr, tmpMask)
        else:
            tmpMask = np.zeros(arrShape, dtype=bool)
            tmpMask[t, :] = True
            outArr = np.ma.masked_array(arr, tmpMask)

        return outArr

    def get_block(self, block_number=0, offset=0, force_3d = False):
        """
        Get a block by its position, ordered as follow :
    
            +-----------+-----------+
            |  block 0  |  block 1  |
            +-----------+-----------+
            |  block 2  |  block 3  |
            +-----------+-----------+
    
        Parameters
            -----------
        block_number, int, optional (default=0).
        Position of the desired block.
        offset : int
            A parameter to get an extended block in the image (used in spatial functions)
        force_3d : bool
            Use force_3d = True for spatial function

    
        Returns
        --------
        Block : np.ndarray
        """
    
        if block_number > self.n_blocks:
            raise ValueError(
                'There are only {} blocks in your image.'.format(
                    self.n_blocks))
        else:
            row = [l for l in range(0, self.n_lines, self.y_block_size)]
            col = [c for c in range(0, self.n_columns, self.x_block_size)]
            
            row_number = int(block_number / self.n_x_blocks)
            col_number = int(block_number % self.n_x_blocks)
            
            width = min(self.n_columns - col[col_number], self.x_block_size)
            height = min(self.n_lines - row[row_number], self.y_block_size)
                        
            tmp = self._generate_block_array(
            col[col_number], row[row_number], width, height, offset, self.mask, force_3d)
            
            if force_3d is False :                        
                if self.return_3d is False : 
                    tmp = self._manage_2d_mask(tmp)
                    tmp = np.ma.copy(tmp)
        return tmp
        
    def get_random_block(self, random_state=None, offset=0, force_3d=False):  
        """
        Get a random block from the raster.

        Parameters
        ------------
        random_state : int, optional (default=None)
            If int, random_state is the seed used by the random number generator.
            If None, the random number generator is the RandomState instance used by numpy np.random.
        offset : int
            A parameter to get an extended block in the image (used in spatial functions)
        force_3d : bool.
            Use force_3d true for a spatial function
        """
#        mask = np.array([True])

        np.random.seed(random_state)
        rdm = np.random.permutation(np.arange(self.n_blocks))
        idx = 0
        
        size = 0
        while size == 0:
            tmp = self.get_block(block_number=rdm[idx], offset=offset, force_3d=force_3d)   
            if len(self.opened_images) > 1:
                mask = tmp[0].mask
                size = tmp[0].size
            else:
                mask = tmp.mask
                size = tmp.size
            
            if np.all(mask == True):
                size = 0
            idx += 1
        return tmp

    def reshape_ndim(self, x,force_3d=False):
        """
        Reshape array with at least one band.

        Parameters
        ----------
        x : numpy.ndarray, shape [n_pixels, n_features] or shape [n_pixels].

        Returns
        -------
        x : numpy.ndarray, shape [n_pixels, n_features].

        """
        if x.ndim == 0:
            x = x.reshape(-1, 1)
        if self.return_3d or force_3d:
            if x.ndim == 2:
                x = x.reshape(*x.shape, 1)
        else:
            if x.ndim == 1:
                x = x.reshape(-1, 1)
        return x

    def read_band_per_band(self):
        """
        Yields each whole band as np masked array (so with masked data)
        """
        for nRaster in range(len(self.opened_images)):
            nb = self.opened_images[nRaster].RasterCount
            for n in range(1, nb + 1):
                band = self.opened_images[nRaster].GetRasterBand(n)
                band = band.ReadAsArray()
                if self.mask:
                    mask = np.asarray(
                        self.opened_mask.GetRasterBand(1).ReadAsArray(), dtype=bool)
                    band = np.ma.MaskedArray(band, mask=~mask)
                else:
                    band = np.ma.MaskedArray(
                        band, mask=np.where(
                            band == self.nodata, True, False))
                yield band

    def read_block_per_block(self, x_block_size=False, y_block_size=False):
        """
        Yield each block.
        """
        for X, col, line, cols, lines in self._iter_block(
                get_block=True, y_block_size=y_block_size, x_block_size=x_block_size):
            if isinstance(X, list):
                mask = X[0].mask
            else:
                mask = X.mask
            if not np.all(mask == 1):
                yield X

    def _return_unmasked_X(self, X):
        if isinstance(X.mask, np.bool_):
            if X.mask == False:
                X = X.data
            else:
                pass
                # no return
        else:
            mask = np.in1d(X.mask[:, 0], True)
            X = X[~mask, :].data
        return X

    def _manage_2d_mask(self, X):
        if len(self.opened_images) > 1:
            X = [self._return_unmasked_X(x) for x in X]
        else:
            X = self._return_unmasked_X(X)

        return X

    def custom_block_size(self, x_block_size=False, y_block_size=False):
        """
        Define custom block size for reading and writing the raster.

        Parameters
        ----------
        y_block_size : float or int, default False.
            IF int, number of rows per block.
            If -1, means all the rows.
            If float, value must be between 0 and 1, such as 1/3.
        x_block_size : float or int, default False.
            If int, number of columns per block.
            If -1, means all the columns.
            If float, value must be between 0 and 1, such as 1/3.
        """

        if y_block_size:
            if y_block_size == -1:
                self.y_block_size = self.n_lines
            elif isinstance(y_block_size, float):
                self.y_block_size = int(np.ceil(self.n_lines * y_block_size))
            else:
                self.y_block_size = y_block_size
        else:
            self.y_block_size = self.block_sizes[1]
        if x_block_size:
            if x_block_size == -1:
                self.x_block_size = self.n_columns
            elif isinstance(x_block_size, float):
                self.x_block_size = int(np.ceil(self.n_columns * x_block_size))
            else:
                self.x_block_size = x_block_size
        else:
            self.x_block_size = self.block_sizes[0]

        self.n_blocks = np.ceil(self.n_lines / self.y_block_size).astype(int) * np.ceil(self.n_columns /
                                                                                        self.x_block_size).astype(int)
        self.block_sizes = [self.x_block_size, self.y_block_size]

        self.n_y_blocks = len(
            [i for i in range(0, self.n_lines, self.y_block_size)])
        self.n_x_blocks = len(
            [i for i in range(0, self.n_columns, self.x_block_size)])

        if self.verbose:
            push_feedback('Total number of blocks : %s' % self.n_blocks)

    def _iter_for_spatial_function(self, col, line, width, height, offset):
        """
        Yields a spatial_block which browses the whole block
        
        Parameters
        ----------
        col : int
            first column of the block
        line : int
            first line of the block
        width : int
            the width of the spatial block
        height : int
            the height of the spatial block
        offset : int
            the offset
        """
        for id_col, column in enumerate(range(col, col+width)):
            for id_row, row in enumerate(range(line, line+height)):
                spatial_block = self._generate_block_array(column, row, 1, 1, offset, self.mask, True)
                yield id_col, id_row, spatial_block
         
            
    def _return_block (self, idx, X_, X__, col, line, cols, lines, fun) :
        """
        Returns the result of the functions applied to an entire block
        
        Parameters
        ----------
        idx : int
            index of the function (fun)            
        X_ : np.array
            copy of the array of the block X, X_ is used to get mask            
        X__ : np.array
            copy of the array X_ 
        col : int
            first column of the block
        line : int
            first line of the block
        width : int
            the width of the spatial block
        height : int
            the height of the spatial block
        fun : str
            the function
            
        Returns
        --------
        resFun : np.ndarray
            Results of the functions
        """
        
        if self._function_is_3d[idx] is True:
                     
             if not X_.ndim > 2:
                 X_reshape = np.reshape(X_,(lines, cols, X_.shape[-1]))
             resFun = np.zeros((X_reshape.shape[0],X_reshape.shape[1],self.outputs[idx].RasterCount))
             
          
             for x_center, y_center, spatial_block in self._iter_for_spatial_function(col, line, cols, lines, self._offsets[idx]):
                 resFun[y_center, x_center, ...] = fun(spatial_block,**self.functionsKwargs[idx])
        else :         
             if self.functionsKwargs[idx] is not False:
                 resFun = fun(X__, **
                              self.functionsKwargs[idx])
             else:
                 resFun = fun(X__)
 
        resFun = self.reshape_ndim(resFun, force_3d=self._function_is_3d[idx])
        
        return resFun   
                
    def run(self):
        """
        Process writing with outside function.

        Returns
        -------
        None
        """

        # TODO : Parallel
        self.pb = ProgressBar(self.n_blocks, message=self.message)

        for X, col, line, cols, lines in self._iter_block(
                get_block=True):

            if isinstance(X, list):
                X_ = [np.ma.copy(arr) for arr in X]
                X = X_[0]  # X_[0] is used to get mask
            else:
                X_ = np.ma.copy(X) #return a copy of the array

            if self.verbose:
                self.pb.add_position(self._position)

            for idx, fun in enumerate(self.functions):
                maxBands = self.outputs[idx].RasterCount

                if not np.all(X.mask == 1):
                    # if all the block is not masked
                    if not self.return_3d:
                        if isinstance(X_, list):
                            X__ = [arr[~X.mask[:, 0], ...].data for arr in X_]
                        else:
                            X__ = X[~X.mask[:, 0], ...].data
                    else:
                        X__ = np.ma.copy(X_)

                    resFun = self._return_block(idx, X_, X__, col, line, cols, lines, fun)                 

                    nBands = resFun.shape[-1]
                    if nBands > maxBands:
                        raise ValueError(
                            "Your function output {} bands, but has been defined to have a maximum of {} bands.".format(
                                resFun.shape[-1], maxBands))

                    if not np.all(X.mask == 0):
                        # if all the block is not unmasked add the nodata value

                        resFun = self.reshape_ndim(resFun, force_3d=self._function_is_3d[idx])
                        mask = self.reshape_ndim(X.mask[..., 0], force_3d=self._function_is_3d[idx])
                        tmp = np.repeat(
                            mask,
                            maxBands,
                            axis=mask.ndim - 1) # répète le masque sur le nombre de bandes
                    
                        if self.return_3d or self._function_is_3d[idx]:       
                             
                             if not tmp.ndim > 2:
                                 tmp = np.reshape(tmp,(lines, cols, self.outputs[idx].RasterCount))

                             resFun = np.where(
                                tmp,
                                self.outputNoData[idx],
                                resFun)
                        else:
                            tmp = tmp.astype(resFun.dtype)
                            tmp[mask.flatten(), ...] = self.outputNoData[idx]
                            tmp[~mask.flatten(), ...] = resFun
                            resFun = tmp

                else:
                    # if all the block is masked
                    if self.outputNoData[idx] is not False:
                        # create an array with only the nodata value
                        # self.return3d+1 is just the right number of axis
                        resFun = np.full(
                            (*X.shape[:self.return_3d + 1], maxBands), self.outputNoData[idx])

                    else:
                        raise ValueError(
                            'Some blocks are masked and no nodata value was given.\
                            \n Please give a nodata value when adding the function.')
                if np.__version__ >= '1.17' and self.outputNoData[idx] is not False:
                    resFun = np.nan_to_num(resFun, nan=self.outputNoData[idx])

                for ind in range(maxBands):
                    # write result band per band
                    indGdal = ind + 1
                    curBand = self.outputs[idx].GetRasterBand(indGdal)

                    resToWrite = resFun[..., ind]

                    if self.return_3d is False:
                        # need to reshape as block
                        resToWrite = resToWrite.reshape(lines, cols)

                    curBand.WriteArray(resToWrite, col, line)
                    curBand.FlushCache() 

            self._position += 1

        self.pb.add_position(self.n_blocks)

        for idx, fun in enumerate(self.functions):
            # set nodata if given
            if self.outputNoData[idx] is not False:
                band = self.outputs[idx].GetRasterBand(1)
                band.SetNoDataValue(self.outputNoData[idx])
                band.FlushCache()

            if self.verbose:
                push_feedback(
                    'Saved {} using function {}'.format(
                        self.outputs[idx].GetDescription(), str(
                            fun.__name__)))
            self.outputs[idx] = None


def sample_extraction(
        in_image,
        in_vector,
        out_vector,
        unique_fid=None,
        band_prefix=None,
        verbose=1):
    """
    Extract centroid from shapefile according to the raster, and extract band value if band_prefix is given.

    This script is available via terminal by entering : `mtb_SampleExtraction`.

    Parameters
    ----------
    in_image : str.
        A filename or path of a raster file.
        It could be any file that GDAL can open.
    in_vector : str.
        A filename or path corresponding to a vector file.
        It could be any file that GDAL/OGR can open.
    out_vector : str.
        Extension will be used to select driver. Please use one of them : ['gpkg','sqlite','shp','netcdf','gpx'].
    unique_fid : str, optional (default=None).
        If None, will add a field called 'uniquefid' in the output vector.
    band_prefix : str, optional (default=None).
        If band_prefix (e.g. 'band'), will extract values from raster.
    """

    def _pixel_location_from_centroid(coords, geo_transform):
        """
        Convert XY coords into the centroid of a pixel

        Parameters
        --------
        coords : arr or list.
            X is coords[0], Y is coords[1].
        geo_transform : list.
            List got from gdal.Open(inRaster).GetGeoTransform() .
        """
        newX = geo_transform[1] * (coords[0] + 0.5) + \
            geo_transform[0]

        newY = geo_transform[5] * (coords[1] + 0.5) + geo_transform[3]
        return [newX, newY]

    if unique_fid is None:
        unique_fid = 'uniquefid'
        if verbose:
            push_feedback("Adding 'uniquefid' field to the original vector.")
        _add_vector_unique_fid(
            in_vector, unique_fid, verbose=verbose)

    if verbose:
        push_feedback("Extract values from raster...")
    X, Y, coords = extract_ROI(
        in_image, in_vector, unique_fid, get_pixel_position=True, verbose=verbose)

    geo_transform = gdal.Open(in_image).GetGeoTransform()

    centroid = [_pixel_location_from_centroid(
        coord, geo_transform) for coord in coords]
    # init outLayer
    if np.issubdtype(X.dtype, np.integer):
        try:
            dtype = ogr.OFTInteger64
        except BaseException:
            dtype = ogr.OFTInteger
    else:
        dtype = ogr.OFTReal
    outLayer = _create_point_layer(
        in_vector, out_vector, unique_fid, dtype=dtype, verbose=verbose)
    if verbose:
        outLayer._add_total_points(len(centroid))

    if verbose:
        push_feedback("Adding each centroid to {}...".format(out_vector))
    for idx, xy in enumerate(centroid):
        try:
            curY = Y[idx][0]
        except BaseException:
            curY = Y[idx]
        if curY != 0:
            if band_prefix is None:
                outLayer._add_point_to_layer(xy, curY)
            else:
                outLayer._add_point_to_layer(xy, curY, X[idx], band_prefix)

    outLayer.close_layer()


class _create_point_layer:
    def __init__(self, in_vector, out_vector, unique_id_field,
                 dtype=ogr.OFTInteger, verbose=1):
        """
        Create a vector layer as point type.

        Parameters
        ------------
        in_vector : str.
            A filename or path corresponding to a vector file.
            It could be any file that GDAL/OGR can open.
        out_vector : str.
            Outvector. Extension will be used to select driver. Please use one of them : ['gpkg','sqlite','shp','netcdf','gpx'].
        unique_fid : str, optional (default=None).
            If None, will add a field called 'uniquefid' in the output vector.
        dtype : int, optional (default=ogr.OFTInteger)
            the ogr datatype.
        verbose : bool or int, optional (default=True).
            The higher is the int verbose, the more it will returns informations.

        Methods
        ----------
        _add_total_points(nSamples): int.
            Will generate progress bar.
        _add_point_to_layer(coords): list,arr.
            coords[0] is X, coords[1] is Y.
        closeLayer():
            Close the layer.
        """
        self.verbose = verbose
        self._dtype = dtype
        # load inVector
        self.inData = ogr.Open(in_vector, 0)
        self.inLyr = self.inData.GetLayerByIndex(0)
        srs = self.inLyr.GetSpatialRef()

        # create outVector
        self.driver_name = get_ogr_driver_from_filename(out_vector)
        driver = ogr.GetDriverByName(self.driver_name)
        self.outData = driver.CreateDataSource(out_vector)

        # finish  outVector creation
        self.outLyr = self.outData.CreateLayer('centroid', srs, ogr.wkbPoint)
        self.outLyrDefinition = self.outLyr.GetLayerDefn()

        # initialize variables
        self.idx = 0
        self.lastPosition = 0
        self.nSamples = None
        if self.driver_name == 'SQLITE' or self.driver_name == 'GPKG':
            self.outLyr.StartTransaction()

        self.unique_id_field = unique_id_field

        # Will generate unique_ID_and_FID when copying vector
        self.unique_ID_and_FID = False
        self.addBand = False

    def _add_band_value(self, bandPrefix, nBands):
        """
        Parameters
        -------
        bandPrefix : str.
            Prefix for each band (E.g. 'band')
        nBands : int.
            Number of band to save.
        """
        self.nBandsFields = []
        for b in range(nBands):
            field = bandPrefix + str(b)
            self.nBandsFields.append(field)
            self.outLyr.CreateField(ogr.FieldDefn(field, self._dtype))
        self.addBand = True

    def _add_total_points(self, nSamples):
        """
        Adding the total number of points will show a progress bar.

        Parameters
        --------
        nSamples : int.
            The number of points to be added (in order to have a progress bar. Will not affect the processing if bad value is put here.)
        """
        self.nSamples = nSamples
        self.pb = ProgressBar(nSamples, 'Adding points... ')

    def _add_point_to_layer(
            self,
            coords,
            uniqueIDValue,
            band_value=None,
            band_prefix=None):
        """
        Parameters
        -------
        coords : list, or arr.
            X is coords[0], Y is coords[1]
        uniqueIDValue : int.
            Unique ID Value to retrieve the value from fields
        band_value : None, or arr.
            If array, should have the same size as the number of bands defined in addBandsValue function.
        """
        if self.verbose:
            if self.nSamples:
                currentPosition = int(self.idx + 1)
                if currentPosition != self.lastPosition:
                    self.pb.add_position(self.idx + 1)
                    self.lastPosition = currentPosition

        if self.unique_ID_and_FID is False:
            self._update_arr_according_to_vector()

        # add Band to list of fields if needed
        if band_value is not None and self.addBand is False:
            self._add_band_value(band_prefix, band_value.shape[0])

        point = ogr.Geometry(ogr.wkbPoint)
        point.SetPoint(0, coords[0], coords[1])
        featureIndex = self.idx
        feature = ogr.Feature(self.outLyrDefinition)
        feature.SetGeometry(point)
        feature.SetFID(featureIndex)

        # Retrieve inVector FID
        FID = self.uniqueFIDs[np.where(np.asarray(
            self.uniqueIDs, dtype=np.int) == int(uniqueIDValue))[0][0]]

        featUpdates = self.inLyr.GetFeature(int(FID))
        for f in self.fields:
            if f != 'ogc_fid':
                feature.SetField(f, featUpdates.GetField(f))
                if self.addBand is True:
                    for idx, f in enumerate(self.nBandsFields):
                        feature.SetField(f, int(band_value[idx]))

        self.outLyr.CreateFeature(feature)
        self.idx += 1

    def _update_arr_according_to_vector(self):
        """
        Update outVector layer by adding field from inVector.
        Store ID and FIDs to find the same value.
        """
        self.uniqueIDs = []
        self.uniqueFIDs = []
        currentFeature = self.inLyr.GetNextFeature()
        self.fields = [
            currentFeature.GetFieldDefnRef(i).GetName() for i in range(
                currentFeature.GetFieldCount())]
        # Add input Layer Fields to the output Layer
        layerDefinition = self.inLyr.GetLayerDefn()

        for i in range(len(self.fields)):
            fieldDefn = layerDefinition.GetFieldDefn(i)
            self.outLyr.CreateField(fieldDefn)

        self.inLyr.ResetReading()
        for feat in self.inLyr:
            uID = feat.GetField(self.unique_id_field)
            uFID = feat.GetFID()
            self.uniqueIDs.append(uID)
            self.uniqueFIDs.append(uFID)
        self.unique_ID_and_FID = True

    def close_layer(self):
        """
        Once work is done, close all layers.
        """
        if self.driver_name == 'SQLITE' or self.driver_name == 'GPKG':
            self.outLyr.CommitTransaction()
        self.inData.Destroy()
        self.outData.Destroy()


def get_distance_matrix(in_image, in_vector, field=False, verbose=False):
    """
    Return for each pixel, the distance one-to-one to the other pixels listed in the vector.

    Parameters
    ----------
    in_image : str.
        Path of the raster file where the vector file will be rasterize.
    in_vector : str.
        Path of the vector file to rasterize.
    field : str or False, optional (default=False).
        Name of the vector field to extract the value (must be float or integer).

    Returns
    --------
    distance_matrix : array of shape (nSamples,nSamples)
    label : array of shape (nSamples)
    """
    if field is not False:
        only_pixel_position = False
    else:
        only_pixel_position = True

    coords = extract_ROI(
        in_image, in_vector, field, get_pixel_position=True, only_pixel_position=only_pixel_position, verbose=verbose)
    from scipy.spatial import distance
    if field:
        label = coords[1]
        coords = coords[2]

    distance_matrix = np.asarray(distance.cdist(
        coords, coords, 'euclidean'), dtype=np.uint64)

    if field:
        return distance_matrix, label
    else:
        return distance_matrix


def get_ogr_driver_from_filename(fileName):
    """
    Return driver name used in OGR accoriding to the extension of the vector.

    Parameters
    ----------
    fileName : str.
        Path of the vector with extension.

    Returns
    -------
    driverName : str
        'SQLITE', 'GPKG', 'ESRI Shapefile'...

    Examples
    --------
    >>> mtb.processing.get_ogr_driver_from_filename('goVegan.gpkg')
    'GPKG'
    >>> mtb.processing.get_ogr_driver_from_filename('stopEatingAnimals.shp')
    'ESRI Shapefile'
    """
    extensions = ['sqlite', 'shp', 'netcdf', 'gpx', 'gpkg']
    driversName = ['SQLITE', 'ESRI Shapefile', 'netCDF', 'GPX', 'GPKG']

    fileName, ext = os.path.splitext(fileName)

    if ext[1:] not in extensions:
        msg = 'Your extension {} is not recognized as a valid extension for saving shape.\n'.format(
            ext)
        msg = msg + 'Supported extensions are ' + str(driversName) + '\n'
        msg = msg + 'We recommend you to use \'sqlite\' extension.'
        raise Warning(msg)
    else:
        driverIdx = [x for x, i in enumerate(extensions) if i == ext[1:]][0]
        driverName = driversName[driverIdx]
        return driverName


def read_vector_values(vector, *args, **kwargs):
    """
    Read values from vector. Will list all fields beginning with the roiprefix 'band-' for example.

    Parameters
    ----------
    vector : str
        Vector path ('myFolder/class.shp',str).
    *args : str
        Field name containing the field to extract values from (i.e. 'class', str).
    **kwargs : arg
        - band_prefix = 'band-' which is the common suffix listing the spectral values (i.e. band_prefix = 'band-').
        - get_features = True, will return features in one list AND spatial Reference.

    Returns
    -------
    List values, same length as number of parameters.
    If band_prefix as parameters, will return one array with n dimension.

    See also
    ---------
    museotoolbox.processing.extract_ROI: extract raster values from vector file.

    Examples
    ---------
    >>> from museotoolbox.datasets import load_historical_data
    >>> _,vector=load_historical_data()
    >>> Y = read_vector_values(vector,'Class')
    array([1, 1, 1, 1, 2, 2, 2, 1, 1, 2, 4, 5, 4, 5, 3, 3, 3], dtype=int32)
    >>> Y,fid = read_vector_values(vector,'Class','uniquefid')
    (array([1, 1, 1, 1, 2, 2, 2, 1, 1, 2, 4, 5, 4, 5, 3, 3, 3], dtype=int32),
     array([ 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17], dtype=int32))
    """

    try:
        file = ogr.Open(vector)
        lyr = file.GetLayer()
    except BaseException:
        raise Exception("Can't open {} file".format(vector))

    # get all fields and save only roiFields
    ldefn = lyr.GetLayerDefn()
    listFields = []

    # add kwargs
    extractBands = False
    get_features = False
    if kwargs:
        # check if need to extract bands from vector
        if 'band_prefix' in kwargs.keys():
            extractBands = True
            band_prefix = kwargs['band_prefix']
        # check if need to extract features from vector
        if 'get_features' in kwargs.keys():
            get_features = kwargs['get_features']

    if extractBands:
        bandsFields = []

    # if get_features, save Spatial Reference and Features
    if get_features:
        srs = lyr.GetSpatialRef()
        features = []

    # List available fields
    for n in range(ldefn.GetFieldCount()):
        fdefn = ldefn.GetFieldDefn(n)
        if fdefn.name is not listFields:
            listFields.append(fdefn.name)
        if extractBands:
            if fdefn.name.startswith(band_prefix):
                bandsFields.append(fdefn.name)

    if len(kwargs) == 0 and len(args) == 0:
        raise ValueError('These fields are available : {}'.format(listFields))
    else:

        if extractBands and len(bandsFields) == 0:
            raise ValueError(
                'Band prefix field "{}" do not exists. These fields are available : {}'.format(
                    band_prefix, listFields))

        # Initialize empty arrays
        if len(args) > 0:  # for single fields
            ROIlevels = [np.zeros(lyr.GetFeatureCount()) for i in args]

        if extractBands:  # for band_prefix
            ROIvalues = np.zeros(
                [lyr.GetFeatureCount(), len(bandsFields)], dtype=np.int32)

        # Listing each feature and store to array
        for i, feature in enumerate(lyr):
            if extractBands:
                for j, band in enumerate(bandsFields):
                    feat = feature.GetField(band)
                    if i == 0:
                        ROIvalues.astype(type(feat))

                    ROIvalues[i, j] = feat
            if len(args) > 0:
                try:
                    for a in range(len(args)):
                        feat = feature.GetField(args[a])
                        if i == 0:
                            ROIlevels[a] = ROIlevels[a].astype(type(feat))
                        ROIlevels[a][i] = feature.GetField(args[a])
                except BaseException:
                    raise ValueError(
                        "Field \"{}\" do not exists. These fields are available : {}".format(
                            args[a], listFields))
            if get_features:
                features.append(feature)

        # Initialize return
        fieldsToReturn = []

        # if bandPrefix
        if extractBands:
            fieldsToReturn.append(ROIvalues)

        # if single fields
        if len(args) > 0:
            for i in range(len(args)):
                fieldsToReturn.append(ROIlevels[i])

        # if features
        if get_features:
            fieldsToReturn.append(features)
            fieldsToReturn.append(srs)
        # if 1d, to turn single array
        if len(fieldsToReturn) == 1:
            fieldsToReturn = fieldsToReturn[0]

        return fieldsToReturn


def _add_vector_unique_fid(in_vector, unique_field='uniquefid', verbose=True):
    """
    Add a field in the vector with an unique value
    for each of the feature.

    Parameters
    -----------
    inVector : str
        Path of the vector file.
    uniqueField : str
        Name of the field to create
    verbose : bool or int, default True.
    Returns
    --------
    None

    Examples
    ---------
    >>> _add_vector_unique_fid('myDB.gpkg',uniqueField='polygonid')
    Adding polygonid [########################################]100%
    """
    if verbose:
        pB = ProgressBar(100, message='Adding ' + unique_field)

    driver_name = get_ogr_driver_from_filename(in_vector)
    inDriver = ogr.GetDriverByName(driver_name)
    inSrc = inDriver.Open(in_vector, 1)  # 1 for writable
    inLyr = inSrc.GetLayer()       # get the layer for this datasource
    inLyrDefn = inLyr.GetLayerDefn()

    if driver_name == 'SQLITE' or driver_name == 'GPKG':
        inLyr.StartTransaction()

    listFields = []
    for n in range(inLyrDefn.GetFieldCount()):
        fdefn = inLyrDefn.GetFieldDefn(n)
        if fdefn.name is not listFields:
            listFields.append(fdefn.name)
    if unique_field in listFields:
        if verbose > 0:
            print(
                'Field \'{}\' is already in {}'.format(
                    unique_field, in_vector))
        inSrc.Destroy()
    else:
        newField = ogr.FieldDefn(unique_field, ogr.OFTInteger)
        newField.SetWidth(20)
        inLyr.CreateField(newField)

        FIDs = [feat.GetFID() for feat in inLyr]

        ThisID = 1

        for idx, FID in enumerate(FIDs):
            if verbose:
                pB.add_position(idx / len(FIDs) + 1 * 100)
            feat = inLyr.GetFeature(FID)
            #ThisID = int(feat.GetFGetFeature(feat))
            # Write the FID to the ID field
            feat.SetField(unique_field, int(ThisID))
            inLyr.SetFeature(feat)              # update the feature
            # inLyr.CreateFeature(feat)
            ThisID += 1

        if driver_name == 'SQLITE' or driver_name == 'GPKG':
            inLyr.CommitTransaction()
        inSrc.Destroy()


def _reshape_ndim(X):
    """
    Reshape ndim of X to have at least 2 dimensions

    Parameters
    -----------
    X : np.ndarray
        array.

    Returns
    --------
    X : np.ndarray
        Returns array with a least 2 dimensions.

    Examples
    ---------
    >>> X = np.arange(5,50)
    >>> X.shape
    (45,)
    >>> _reshape_ndim(X).shape
    (45, 1)
    """
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    return X





