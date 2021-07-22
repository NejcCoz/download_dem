# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 08:55:58 2019

@author: ncoz

@version: 0.1

Group of functions that are used for manipulation of downloaded ancillary data.

Raster:
    * array_tif = extract array and meta from GeoTIFF (rasterio)
    * merge_clip = Merge and clip GeoTIFFs (rasterio), output array + meta
    * fill_tif = Interpolate to fill "nodata" in GeoTIFFs (GDAL)
    * nodata_check = check for nodata values in a raster (GDAL)

Point Cloud (LasTools):
    * las_index = Index LAZ files
    * las_dtm = Create DTMs from LAZ files
    * las_intensity = Create Intensity
"""

import glob
import multiprocessing
import os
import subprocess

import rasterio
from osgeo import gdal
from rasterio.crs import CRS
from rasterio.merge import merge


# =============================================================================
# Read array and metadata from TIFF (USING RASTERIO)
# =============================================================================
def array_tif(pth):
    """Returns an array and metadata from a single TIF file.

    IN:
        (1) pth (str) - string, path to TIFF file
    OUT:
        (1) out_msg - string
        (2) array - numpy array
        (3) dtm_meta - rasterio metadata dictionary
    """
    raster = rasterio.open(pth)
    array = raster.read()
    metadata = raster.meta
    raster.close()
    
    # Output dictionary
    dtm_out = {'out_msg': 'File successfully merged!',
               'array': array,
               'dtm_meta': metadata}
    
    return dtm_out


# =============================================================================
# Create Mosaic (USING RASTERIO)
# =============================================================================
def merge_clip(i_dir, gs_aoi):
    """
    Merges multiple files into a single TIF and clips the merged file to bounds
    using the Rasterio module.
    IN:
        (1) i_dir - string, input directory
        (2) gs_aoi - GeoSeries, polygon of extents of the AOI
    OUT:
        (1) out_msg - string
        (2) array- merged and clipped DTM in numpy array format
        (3) dtm_meta - metadata Rasterio dictionary
    """
    # Find all TIF files in specified folder
    q = os.path.join(i_dir, '*.tif')
    dem_fps = glob.glob(q)
    src_all = []
    # Open TIF files and store them as DataSets in the created list
    print("Opening TIF files for merge & clip operation.")
    for fp in dem_fps:
        src = rasterio.open(fp)
        src_all.append(src)

    # Reproject GS into the same coordinate reference system as the raster
    if src_all[0].crs is None:
        bounds = None
    else:
        raster_crs = src_all[0].crs.to_epsg()
        aoi_crs = gs_aoi.crs.to_epsg()
        if aoi_crs != raster_crs:
            aoi_pr = gs_aoi.to_crs(crs=raster_crs)
        else:
            aoi_pr = gs_aoi

        # Extract bounds for nice rectangular clip
        bounds = aoi_pr.bounds
        bounds = tuple(bounds.iloc[0])

    # Merge all files using rasterio.merge:
    # -------------------------------------
    print("Merging tiles and clipping to extents.")
    mosaic, out_trans = merge(src_all, bounds=bounds)
    # Update metadata from source files
    out_meta = src_all[0].meta.copy()
    out_meta.update({"driver": "GTiff",
                     "height": mosaic.shape[1],
                     "width": mosaic.shape[2],
                     "transform": out_trans})
    # Close source files after reading all the required data
    for ds in src_all:
        ds.close()

# INSTEAD OF SAVING TO FILE JUST RETURN THE ARRAY WITH METADATA
    dtm_out = {'out_msg': 'File successfully merged and clipped!',
               'array': mosaic,
               'dtm_meta': out_meta}

    return dtm_out


# ==============================================================================
# Fill/interpolate missing data (USING GDAL)
# ==============================================================================
def fill_tif(i_dir):
    """
    Fill NoData using GDAl - IDW method for interpolation.
    ("Inverse distance weighted")
    IN:
        (1) i_dir - string, input directory
    OUT:
        (1) out_msg - string
        (2) out_dir - string, output directory
        (3) out_nam - string, file name
    """
    # Find all TIFs in specified folder
    q = os.path.join(i_dir, '*.tif')
    dem_fps = glob.glob(q)

    # Create output directory
    o_dir = i_dir + '_fill'
    if not os.path.exists(o_dir):
        os.mkdir(o_dir)

    for ds in dem_fps:
        # Source dataset
        ds_src = gdal.Open(ds)
        # Get NoData value
        bnd_src = ds_src.GetRasterBand(1)
        nodata = bnd_src.GetNoDataValue()
        bnd_src = None
        
        # Prepare output DTM:
        # -------------------
        # Create output filename
        o_nam = os.path.basename(ds)[:-4] + '_fill.tif'
        # Output path
        fp_fill = os.path.join(o_dir, o_nam)
        # Create output dataset (copy source)
        driver = gdal.GetDriverByName("GTiff")
        # Output data set is a copy of source dataset
        ds_out = driver.CreateCopy(fp_fill, ds_src, strict=0)
        
        # Parameters for GDAL FillNodata:
        # -------------------------------
        bnd_out = ds_out.GetRasterBand(1)
        mask_band = None
        max_search_dist = 500
        smoothing_iterations = 1
        options = ['COMPRESS=LZW']
        
        # Run GDAL FillNodata:
        array_out = bnd_out.ReadAsArray()  # For checking if there is NoData
        test = 0
        if nodata in array_out:
            # Only print this message on first loop
            test += 1
            if test == 1:
                print("Raster contains NoData values. Start interpolation.")
            # RUN GDAL FOR INTERPOLATION
            gdal.FillNodata(bnd_out, mask_band,
                            max_search_dist, smoothing_iterations, options,
                            callback=None)
            # Check if there are still nodata values in raster:
            array_out = bnd_out.ReadAsArray()
            if nodata in array_out:
                print("Raster still contains NoData values -> set remaining to zero.")
                array_out = bnd_out.ReadAsArray()
                array_out[array_out == nodata] = 0
                ds_out.GetRasterBand(1).WriteArray(array_out)
            else:
                print("All nodata has been filled!")
        
        # Close GDAL Data Sets (required for saving the file)
        ds_src = None
        ds_out = None
        bnd_out = None
        driver = None
    
    # Output dictionary:
    # ------------------
    out = {'out_msg': 'File/s successfully filled!',
           'out_dir': o_dir}
    
    return out


# ==============================================================================
# Check if raster has "NoData"
# ==============================================================================
def nodata_check(tif_pth):
    """
    Returns TRUE if there are any NoData present in the raster and FALSE if
    raster is full.
        Using GDAL reads NODATA VALUE from raster and checks if this value
    exist in the ARRAY of the same raster.
    IN:
        (1) tif_pth - string, path to file that needs to be checked
    OUT:
        (1) check - boolean, True if file contains NoData
    """
    ds_src = gdal.Open(tif_pth)
    bnd_src = ds_src.GetRasterBand(1)
    array = bnd_src.ReadAsArray()
    nodata = bnd_src.GetNoDataValue()
    if nodata in array:
        check = True
    else:
        check = False

    # Close data sets
    bnd_src = None
    ds_src = None

    return check


# ==============================================================================
# LAStools (DTM)
# ==============================================================================
def las_dtm(i_dir, gs_aoi, epsg):
    """
    Create Intensity raster from Point Clouds using LAStools.

    NOTE: gs_aoi has to be reprojected into the local CRS (of Point Cloud data)

    IN:
        (1) i_dir - string, directory containing LAZ files
        (2) gs_aoi - geopandas GeoSeries, polygon of AOI
        (3) epsg - EPSG code of the local CRS (of Point Cloud)
        (4) las_ext (optional) - extension of Point Cloud file, "laz" by default

    OUT:
        (1) out_msg - string
        (2) out_dir - string, directory with DTMs
    """
    # Path to files
    laz_pth = os.path.join(i_dir, "*.laz")
    
    # Reproject polygon to local CRS
    if gs_aoi.crs.to_epsg() != epsg:
        aoi_pr = gs_aoi.to_crs(crs=epsg)
    else:
        aoi_pr = gs_aoi

    # Get bounds of polygon(minx, miny, maxx, maxy)
    bnds = aoi_pr.bounds.loc[0].values.tolist()
    # Bounds have to be strings when passed to cmd line
    bnds = [str(i) for i in bnds]
    
    # Set output directory:
    o_dir = i_dir + "_toDTM"
    if not os.path.exists(o_dir):
        os.mkdir(o_dir)
        
    # Number of available cores:
    cores = str(multiprocessing.cpu_count()-1)
    
    # Arguments list (it has to be a list of STRINGS!!!):
    arg_list = ['blast2dem',
                '-i', laz_pth,
                '-kill', '1000',
                '-buffered', '20',
                '-step', '5',
                '-otif',
                '-odir', o_dir,
                '-odix', '"_dem_5m"',
                '-keep_class', '2', '8',
                '-keep_xy', bnds[0], bnds[1], bnds[2], bnds[3],
                '-cores', cores
                ]
        
    # Run LAStools from cmd:
    subprocess.run(arg_list)
    
    # Output dictionary:
    out = {
        'out_msg': "Successfuly created DTM from LAZ!",
        'out_dir': o_dir
    }
    
    return out


# =============================================================================
# LAStools (Intensity)
# =============================================================================
def las_intensity(i_dir, gs_aoi, epsg):
    """
    Create Intensity raster from Point Clouds using LAStools.

    NOTE: gs_aoi has to be reprojected into the local CRS (of Point Cloud data)

    IN:
        (1) i_dir - string, directory containing LAZ files
        (2) gs_aoi - geopandas GeoSeries, polygon of AOI
        (3) epsg - EPSG code of the local CRS (of Point Cloud)
        (4) las_ext (optional) - extension of Point Cloud file, "laz" by default

    OUT:
        (1) out_msg - string
        (2) out_dir - string, directory with Intensity rasters
    """
    # Path to files
    laz_pth = os.path.join(i_dir, "*.laz")
    
    # Reproject polygon to local CRS
    if gs_aoi.crs.to_epsg() != epsg:
        aoi_pr = gs_aoi.to_crs(crs=epsg)
    else:
        aoi_pr = gs_aoi

    # Get bounds of polygon(minx, miny, maxx, maxy)
    bnds = aoi_pr.bounds.loc[0].values.tolist()
    # Bounds have to be strings when passed to cmd line
    bnds = [str(i) for i in bnds]
    
    # Set output directory:
    o_dir = i_dir + "_toIntensity"
    if not os.path.exists(o_dir):
        os.mkdir(o_dir)
        
    # Number of available cores:
    cores = str(multiprocessing.cpu_count()-1)
    
    # Arguments list (it has to be a list of STRINGS!!!):
    arg_list = ['blast2dem',
                '-i', laz_pth,
                '-kill', '1000',
                '-buffered', '20',
                '-step', '0.5',
                '-otif',
                '-odir', o_dir,
                '-odix', '"_intensity"',
                '-intensity',
                '-keep_class', '2', '8',
                '-keep_xy', bnds[0], bnds[1], bnds[2], bnds[3],
                '-cores', cores]
        
    # Run LAStools from cmd:
    subprocess.run(arg_list)
    
    # Output dictionary:
    out = {'out_msg': "Successfuly created Intensity from LAZ!",
           'out_dir': o_dir}
    
    return out


# ==============================================================================
# LAStools (indexing of Point Cloud)
# ==============================================================================
def las_index(i_dir):
    """
    Create PointCloud index for faster processing.
    IN:
        (1) string - directory with LAZ files
    """
    # Set arguments
    pth_laz = os.path.join(i_dir, "*.laz")
    cores = str(multiprocessing.cpu_count()-1)
    # Arguments list
    arg_list = ['lasindex',
                '-i', pth_laz,
                '-cores', cores]
    
    # subprocess.run(arg_list, shell=True)
    subprocess.run(arg_list)


# ==============================================================================
# Assign crs to GTIFFs
# ==============================================================================
def assign_crs(tif_dir, epsg):
    # Find all TIF files in specified folder
    q = os.path.join(tif_dir, '*.tif')
    dem_fps = glob.glob(q)

    for src_pth in dem_fps:
        with rasterio.open(src_pth, "r+") as tif:
            crs_check = tif.crs
            if crs_check is None:
                tif.crs = CRS.from_epsg(epsg)

    status_msg = f"Successfully assigned EPSG:{epsg} to files in {tif_dir}."

    return status_msg


if __name__ == "__main__":
    # TEST array_tif()
    i_path = ".\\test01_anc_temp\\dtm\\test.tif"
    result = array_tif(i_path)
    # ##########################################################################
    # TEMPORARY INPUT:
    # import geopandas as gpd
    # from shapely import wkt

    # Temporary input:
    # ----------------
    # i_dir = '.\\test01_anc_temp\\dtm'   # Downloaded TIFs
    # i_dir = '.\\test01_anc_temp\\dtm_clip'
    # i_dir = '.\\test01_anc_temp\\dtm_clip_fill'
    # i_dir = '.\\test01_anc_temp\\dtm_merge'    # mosaic of the original TIFs
    # i_dir = '.\\test01_anc_temp\\laz'    # Downloaded LAZ files

    # # Denmark
    # i_dir = '.\\dk_temp\\dtm_extracted'

    # # Netherlands
    # i_dir = ''

    # Temporary AOI polygon:
    # ----------------------

    # # Netherlands:
    # aoi_wkt = 'POLYGON ((4019220 3172674, 4019220 3178624, 4023580 3178624, 4023580 3172674, 4019220 3172674))'
    # aoi_crs = {'init':'epsg:3035'} # ETRS89

    # # Denmark:
    # aoi_wkt = 'POLYGON ((4320480 3762072, 4320480 3786228, 4296708 3786228, 4296708 3762072, 4320480 3762072))'
    # aoi_crs = {'init':'epsg:3035'}

    # # Make polygon
    # polygon = wkt.loads(aoi_wkt)
    # gs_aoi = gpd.GeoSeries(polygon, crs=aoi_crs)
