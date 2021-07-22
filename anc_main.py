# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 10:20:31 2019

@author: ncoz

Main routine for download and processing of ancillary data for OrthoVHR.
The routine is still being developed and currently only works for the area
covering the Netherlands.

INPUT: TBD (... for the development, the input is a polygon of AOI)
            * project_id = string (unique identifier)
            * aoi_coords = AOI coordinates in WKT format
            * aoi_crs = AOI coordinate reference system,
                eg. {'init':'epsg:3035'} for ETRS89

OUTPUT: TBD (some sort of log file and updated dictionary with metadata)
"""

import os
import sys
from shutil import rmtree

import geopandas as gpd
from pyproj import CRS
from rasterio import crs
from shapely.geometry import box

import P1_Geometric.P11_Data_Preparation.anc_regions as anc


def anc_main(project_id, aoi_extent, aoi_epsg):
    """Returns an array of selected ancillary data.

    Args:
        project_id (str):
        aoi_extent (list):
        aoi_epsg (int):

    Returns:

    """
    # =========================================================================
    # PREPARE INPUT (currently just read POLYGON to GPD data frame)
    # =========================================================================
        
    # Create polygon from aoi_extent = [min_x, min_y, max_x, max_y]
    polygon = box(aoi_extent[0], aoi_extent[1],
                  aoi_extent[2], aoi_extent[3])
    # Create GeoSeries
    aoi_crs = CRS.from_epsg(aoi_epsg)
    gs_aoi = gpd.GeoSeries(polygon, crs=aoi_crs)
        
    # Create folder for temporary files
    tmp_dir = os.path.join('.', project_id + '_anc_temp')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
        
    # =========================================================================
    # SELECT DATABASE
    # =========================================================================
    
    # Location of shape file with available Open DTM databases
    if os.path.basename(sys.argv[0]) == "storm_main_test.py":
        bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files\\dtm_open_data"
    else:
        bup_dir = ".\\anc_bup_files\\dtm_open_data"

    open_dtm = gpd.read_file(os.path.join(bup_dir, "dtm_open_data.shp"))

    # Reproject AOI to WGS84 (if AOI in different CRS):
    wgs_epsg = CRS.from_string(open_dtm.crs['init']).to_epsg()
    aoi_epsg = gs_aoi.crs.to_epsg()
    if wgs_epsg != aoi_epsg:
        wgs_aoi = gs_aoi.to_crs(crs=wgs_epsg)
    else:
        wgs_aoi = gs_aoi
    
    # Check if AOI is contained within any database 
    select = None
    for _, row in open_dtm.iterrows():
        ints = wgs_aoi.within(row.geometry)
        if ints[0]:
            select = row['abbrev']
        if select is None:
            # TODO: Test if SRTM is actually available
            select = 'SRTM'
    
    # =========================================================================
    # PREPARE ANCILLARY DATA (for the selected region)
    # =========================================================================
    if select == 'NL':
        out = anc.get_NL("DTM", tmp_dir, gs_aoi)
        print(out['out_msg'])
        out_int = anc.get_NL("LAZ", tmp_dir, gs_aoi)
    elif select == 'DK':
        out = anc.get_DK("DTM", tmp_dir, gs_aoi)
        print(out['out_msg'])
        out_int = anc.get_DK("LAZ", tmp_dir, gs_aoi)
    elif select == 'SI':
        out = anc.get_SI("DTM", tmp_dir, gs_aoi)
        print(out['out_msg'])
        out_int = anc.get_SI("LAZ", tmp_dir, gs_aoi)
    elif select == 'DE_NRW':
        out = anc.get_DE("DTM", tmp_dir, gs_aoi, "NRW")
        print(out['out_msg'])
        # TODO: LAZ + check if "ab 2017"
        out_int = None
    elif select == 'MX':
        out = anc.get_MX(tmp_dir, gs_aoi)
        out_int = None
    else:
        out = anc.get_SRTM(tmp_dir, gs_aoi)
        out_int = None

    # =========================================================================
    # PREPARE OUTPUT
    # =========================================================================

    # Remove message from output
    _ = out.pop('out_msg')

    # Rename the array key
    out['array_dtm'] = out.pop('array')

    # Unpack meta data for DTM
    meta_data = out.pop('dtm_meta')
    dtm_trans = meta_data.get('transform')
    
    # Add unpacked data to output dictionary
    out['x_min'] = dtm_trans[2]
    out['y_max'] = dtm_trans[5]
    out['x_size'] = dtm_trans[0]
    out['y_size'] = dtm_trans[4]
    out['width'] = meta_data.get('width')
    out['height'] = meta_data.get('height')
    out['crs'] = meta_data.get('crs').data
    out['crs_wkt'] = crs.CRS.from_dict(out['crs']).wkt

    # Update Intensity
    if out_int is not None:
        out['array_intensity'] = out_int.pop('array')
        # Unpack meta data for Intensity
        meta_data_int = out_int.pop('dtm_meta')
        dtm_trans_int = meta_data_int.get('transform')

        # Add unpacked data to output dictionary
        out['x_min_intensity'] = dtm_trans_int[2]
        out['y_max_intensity'] = dtm_trans_int[5]
        out['x_size_intensity'] = dtm_trans_int[0]
        out['y_size_intensity'] = dtm_trans_int[4]
        out['width_intensity'] = meta_data_int.get('width')
        out['height_intensity'] = meta_data_int.get('height')
    else:
        # If intensity is not available
        out['array_intensity'] = None

    # =========================================================================
    # CLEAN UP
    # =========================================================================

    # Used during development to save results as GeoTIFF
    # import rasterio
    # from os.path import join
    # profile = output["dtm_meta"]
    # with rasterio.open(join(tmp_dir, "anc_NL_dtm.tif"), "w", **profile) as dst:
    #     dst.write(output["array"])

    # Delete temporary folder
    rmtree(tmp_dir, ignore_errors=True)
        
    return out


if __name__ == "__main__":
    # # /////////////////////////////// #
    # # TEMPORARY INPUT FOR NETHERLANDS #
    # in_id = 'test_main_NL02'
    # # [minx, miny, maxx, maxy]
    # # in_ext = [4019220, 3172674, 4023580, 3178624]
    # in_ext = [4019220, 3172674, 4019420, 3172874]
    # in_crs = 3035  # EPSG for ETRS89
    #
    # my_out = anc_main(in_id, in_ext, in_crs)
    # # print(my_out["out_msg"])
    # # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # # //////////////////////////// #
    # # TEMPORARY INPUT FOR SLOVENIA #
    # in_id = 'test_main_SI01'
    # in_ext = [456500, 97200, 457500, 99200]  # [minx, miny, maxx, maxy]
    # in_crs = 3794  # EPSG code for D96/TM
    # in_dtyp = "DTM"
    #
    # my_out = anc_main(in_id, in_ext, in_crs, in_dtyp)
    # print(my_out["out_msg"])
    # # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # ////////////////////////// #
    # TEMPORARY INPUT FOR MEXICO #
    in_id = 'test_main_MX02'
    # [minx, miny, maxx, maxy]
    in_ext = [
        -99.87725514475203, 16.810318800012684,
        -99.83301834476471, 16.854555600000000
    ]
    in_crs = 4326  # WGS84

    my_out = anc_main(in_id, in_ext, in_crs)
    print(my_out["out_msg"])
    # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # # /////////////////////////// #
    # # TEMPORARY INPUT FOR DENMARK #
    # in_id = 'test_main_DK01'
    # # [minx, miny, maxx, maxy]
    # in_ext = [4320480, 3762072, 4321480, 3763072]
    # in_crs = 3035  # EPSG for ETRS89
    # in_dtyp = "DTM"
    #
    # my_out = anc_main(in_id, in_ext, in_crs, in_dtyp)
    # print(my_out["out_msg"])
    # # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # # ///////////////////////////////// #
    # # TEMPORARY INPUT FOR GERMANY  (NRW)#
    # in_id = 'test_main_DE01'
    # # [minx, miny, maxx, maxy]
    # in_ext = [6.75968155220865, 50.9130021454120, 6.7886, 50.9353]
    # in_crs = 4326  # EPSG for ETRS89
    # in_dtyp = "DTM"
    #
    # my_out = anc_main(in_id, in_ext, in_crs, in_dtyp)
    # print(my_out["out_msg"])
    # # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # # //////////////////////// #
    # # TEMPORARY INPUT FOR SRTM #
    # in_id = 'test_main_SRTM02'
    # # [minx, miny, maxx, maxy]
    # in_ext = [-0.7856227356756005, 51.6602891223456098,
    #           -0.2141897969920468, 52.1704971033130747]
    # in_crs = 4326  # EPSG for ETRS89
    # in_dtyp = "DTM"
    #
    # my_out = anc_main(in_id, in_ext, in_crs, in_dtyp)
    # print(my_out["out_msg"])
    # # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    # # CRS LIST
    # in_crs = 4326  # EPSG for WGS84
    # in_crs = 3035  # EPSG for ETRS89
    # in_crs = 28992  # EPSG for Amersfoort / RD New
