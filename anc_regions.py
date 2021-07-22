# -*- coding: utf-8 -*-
"""
Created on Fri Jan 17 11:23:08 2020

@author: ncoz

Makes calls to anc_download and anc_tools modules tp prepare ancillary data for
respective regions/data sets.

Calls from anc_main.

Regions:
    Netherlands
    -----------
    dtm_NL() - AHN3 0.5 m; Amersfoort / RD New, EPSG:28992
    
    Denmark
    -------
    dtm_DK() - Denmark; DHM hoejdemodel 0.4m;
               ETRS89 / UTM zone 32N - Projected, EPSG:25832
               
"""

import P1_Geometric.P11_Data_Preparation.anc_tools as atls
import P1_Geometric.P11_Data_Preparation.dwn_NL as dwn_NL
import P1_Geometric.P11_Data_Preparation.dwn_DK as dwn_DK
import P1_Geometric.P11_Data_Preparation.dwn_SI as dwn_SI
import P1_Geometric.P11_Data_Preparation.dwn_SRTM as dwn_SRTM
import P1_Geometric.P11_Data_Preparation.dwn_DE as dwn_DE
import P1_Geometric.P11_Data_Preparation.dwn_MX as dwn_MX
from pyproj import CRS


def get_NL(data_type, tmp_dir, gs_aoi):
    """Obtains and prepares ancillary DTM data for Netherlands.

    It first makes a call to download routine, to download DTM files from Dutch
    database.
    Processing of the data:
    - interpolate "nodata" values
    - clip and merge

    Args:
        data_type (str): DTM or LAZ
        tmp_dir (str): directory for saving temporary files
        gs_aoi (GeoSeries): polygon of AOI

    Returns:
        out (dict): "out_msg" output message and "pth_dtm" path to DTM file
    """
    # Download DTMs:
    dwn_out = dwn_NL.download(data_type, gs_aoi, tmp_dir)
    print(dwn_out['out_msg'])
    dwn_dir = dwn_out['out_dir']

    if data_type == "DTM":
        # Interpolate DTMs:
        out = atls.fill_tif(dwn_dir)
        print(out['out_msg'])
        # Merge & clip DTMs:
        out = atls.merge_clip(out['out_dir'], gs_aoi)
        print(out['out_msg'])
    elif data_type == "LAZ":
        # Index LAZ files
        print("Indexing point cloud data...")
        atls.las_index(dwn_dir)
        # Create Intensity from LAZ
        print("Processing point cloud data...")
        out = atls.las_intensity(dwn_dir, gs_aoi, 28992)
        print(out['out_msg'])
        inty_dir = out['out_dir']
        # TIFS created from LAZ files have no CRS
        out_msg = atls.assign_crs(inty_dir, 28992)
        print(out_msg)
        # Merge & clip
        out = atls.merge_clip(inty_dir, gs_aoi)
        print(out['out_msg'])
    else:
        raise ValueError(f"Unknown data type selected: {data_type}")
    
    # Update output dictionary with new message:
    out['out_msg'] = f"Ancillary {data_type} data for Netherlands successfully prepared!"
    
    return out


def get_DK(data_type, tmp_dir, gs_aoi):
    """Obtains and prepares ancillary DTM data for Denmark.
    """
    # Download files:
    dwn_out = dwn_DK.download(gs_aoi, tmp_dir, data_type)
    print(dwn_out['out_msg'])
    dwn_dir = dwn_out['out_dir']

    if data_type == "DTM":
        # Merge & clip DTMs
        out = atls.merge_clip(dwn_dir, gs_aoi)
        print(out['out_msg'])
    elif data_type == "LAZ":
        # Index LAZ files
        print("Indexing point cloud data...")
        atls.las_index(dwn_dir)
        # Create Intensity from LAZ
        print("Processing point cloud data...")
        out = atls.las_intensity(dwn_dir, gs_aoi, 25832)
        print(out['out_msg'])
        inty_dir = out['out_dir']
        # Merge & clip
        out = atls.merge_clip(inty_dir, gs_aoi)
        print(out['out_msg'])
    else:
        raise ValueError("Unknown data_type selected!")

    # Update output dictionary with new message:
    out['out_msg'] = f"Ancillary {data_type} data for Denmark successfully prepared!"
    
    return out


def get_SI(data_type, tmp_dir, gs_aoi, local=False):
    """Returns array with DTM for Slovenia (SI).

    Parameters
    ----------
    data_type : str
        Data type "DTM" for DTM or "LAZ" for Point Cloud
    tmp_dir : str
        Path to dir for saving temporary files.
    gs_aoi : gpd.GeoSeries
        Polygon of the AOI.
    local : bool, default False
        Copy data from network drive if True or from web if false.

    Returns
    -------
    dict
        Contains 'out_msg'
    """
    # Download files
    out_dwn = dwn_SI.download(data_type, gs_aoi, tmp_dir, local)
    print(out_dwn['out_msg'])
    dwn_dir = out_dwn['out_dir']

    # Process downloaded files
    if data_type == "DTM":
        # Merge & clip DTMs
        out = atls.merge_clip(dwn_dir, gs_aoi)
        print(out['out_msg'])
    elif data_type == "LAZ":
        # Index LAZ files
        print("Indexing point cloud data...")
        atls.las_index(dwn_dir)
        # Create Intensity from LAZ
        print("Processing point cloud data...")
        out = atls.las_intensity(dwn_dir, gs_aoi, 3794)
        print(out['out_msg'])
        inty_dir = out['out_dir']
        # Assign CRS before merging
        out_msg = atls.assign_crs(inty_dir, 3794)
        print(out_msg)
        # Merge & clip
        out = atls.merge_clip(inty_dir, gs_aoi)
        print(out['out_msg'])
    else:
        raise ValueError("Unknown data_type selected!")
    
    # Update output dictionary with new message:
    out['out_msg'] = 'Ancillary DTM data for Slovenia successfully prepared!'
    
    return out


def get_DE(data_type, tmp_dir, gs_aoi, region):
    """Returns array with DTM for Germany.

    Parameters
    ----------
    data_type : str
        Data type "DTM" for DTM or "LAZ" for Point Cloud
    tmp_dir : str
        Path to dir for saving temporary files.
    gs_aoi : gpd.GeoSeries
        Polygon of the AOI.
    region : str
        Currently only works for NRW, but more regions
        to be added in future.

    Returns
    -------
    dict
        Contains 'out_msg'
    """

    # Download data
    out_dwn = dwn_DE.download(data_type, gs_aoi, tmp_dir, region)
    print(out_dwn['out_msg'])
    dwn_dir = out_dwn['out_dir']

    if data_type == "DTM":
        # Merge & clip DTMs
        out = atls.merge_clip(dwn_dir, gs_aoi)
        print(out['out_msg'])
    elif data_type == "LAZ":
        # Index LAZ files
        print("Indexing point cloud data...")
        atls.las_index(dwn_dir)
        # Create Intensity from LAZ
        print("Processing point cloud data...")
        out = atls.las_intensity(dwn_dir, gs_aoi, 25832)
        print(out['out_msg'])
        inty_dir = out['out_dir']
        # Merge & clip
        out = atls.merge_clip(inty_dir, gs_aoi)
        print(out['out_msg'])
    else:
        raise ValueError("Unknown data_type selected!")

    # Update output dictionary with new message:
    # ------------------------------------------
    out['out_msg'] = f"Ancillary {data_type} data for Germany {region} successfully prepared!"

    return out


def get_SRTM(tmp_dir, gs_aoi):
    # Download DTMs:
    out_dwn = dwn_SRTM.download(gs_aoi, tmp_dir)
    print(out_dwn['out_msg'])
    dtm_dir = out_dwn['out_dir']

    # Merge & clip DTMs:
    out = atls.merge_clip(dtm_dir, gs_aoi)
    print(out['out_msg'])

    # Update output dictionary with new message:
    # ------------------------------------------
    out['out_msg'] = 'Ancillary DTM data from SRTM successfully prepared!'

    return out


def get_MX(tmp_dir, gs_aoi):
    # Download DTMs:
    out_dwn = dwn_MX.download(gs_aoi, tmp_dir)
    print(out_dwn['out_msg'])
    dtm_dir = out_dwn['out_dir']

    # Merge & clip DTMs:
    out = atls.merge_clip(dtm_dir, gs_aoi)
    print(out['out_msg'])

    # Update output dictionary with new message:
    # ------------------------------------------
    out['out_msg'] = 'Ancillary DTM data from SRTM successfully prepared!'

    return out


if __name__ == "__main__":
    # # Temporary input for debugging (MX):
    # # -----------------------------------
    # from shapely.geometry import box
    # import geopandas as gpd
    # import rasterio
    # from os.path import join
    # # [minx, miny, maxx, maxy] (small)
    # # in_ext = [-99.8772551447520271, 16.8103188000126842,
    # #           -99.8688342786638117, 16.8123826399700889]
    # # [minx, miny, maxx, maxy] (Acapulco)
    # in_ext = [
    #     -99.87725514475203, 16.810318800012684,
    #     -99.83301834476471, 16.854555600000000
    # ]
    # in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    # in_crs = CRS.from_epsg(4326)  # WGS84
    # # ---
    # in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    # in_dir = "..\\..\\tmp_mx004"
    #
    # # Run download
    # my_out = get_MX(in_dir, in_gs)
    #
    # print(my_out)
    # profile = my_out["dtm_meta"]
    # with rasterio.open(join(in_dir, "mx_test.tif"), "w", **profile) as dst:
    #     dst.write(my_out["array"])
    # # -------------------------------------

    # # Temporary input for debugging (SRTM):
    # # -------------------------------------
    # from shapely.geometry import box
    # import geopandas as gpd
    # import rasterio
    # from os.path import join
    # in_ext = [456500, 97200, 500500, 140200]  # [minx, miny, maxx, maxy]
    # in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    # in_crs = CRS.from_epsg(3794)  # D96/TM
    # # ---
    # in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    # in_dir = "..\\..\\tmp_srtm001"
    # # Run function
    # my_out = get_SRTM(in_dir, in_gs)
    # print(my_out)
    # profile = my_out["dtm_meta"]
    # with rasterio.open(join(in_dir, "slo_test.tif"), "w", **profile) as dst:
    #     dst.write(my_out["array"])
    # # -------------------------------------

    # # Temporary input for debugging (SI):
    # # -----------------------------------
    # from shapely.geometry import box
    # import geopandas as gpd
    # import rasterio
    # from os.path import join
    # in_ext = [507441, 29329, 520304, 35868]  # [minx, miny, maxx, maxy]
    # in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    # in_crs = CRS.from_epsg(3794)
    # # ---
    # in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    # in_dir = "..\\..\\_TEST2_KO_SI_Kolpa"
    # # Access local repository:
    # in_local = False
    # in_type = "LAZ"
    # # Run function
    # my_out = get_SI(in_type, in_dir, in_gs, in_local)
    # print(my_out)
    # profile = my_out["dtm_meta"]
    # profile.update(compress='lzw')
    # with rasterio.open(join(in_dir, "KO_SI_Kolpa_laz.tif"),
    #                    "w", **profile, BIGTIFF='YES') as dst:
    #     dst.write(my_out["array"])
    # # -----------------------------------

    # # Temporary input for debugging (DK):
    # # -----------------------------------
    # import geopandas as gpd
    # from shapely.geometry import box
    # import rasterio
    # from os.path import join
    # # Small area for testing
    # in_poly = box(4296708, 3762072, 4298708, 3763072)
    # in_crs = CRS.from_epsg(3035)  # ETRS89-extended / LAEA Europe
    # # ---
    # in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    # in_dir = '..\\..\\tmp_dk002'
    # in_type = "LAZ"
    #
    # # Run function
    # my_out = get_DK(in_type, in_dir, in_gs)
    # print(my_out)
    # profile = my_out["dtm_meta"]
    # with rasterio.open(join(in_dir, "anc_DK_intensity.tif"), "w", **profile) as dst:
    #     dst.write(my_out["array"])
    # # -----------------------------

    # Temporary input for debugging (NL):
    # -----------------------------------
    from shapely.geometry import box
    import geopandas as gpd
    import rasterio
    from os.path import join
    # [minx, miny, maxx, maxy]
    in_poly = box(3984394, 3238658, 4007590, 3276012)
    in_crs = CRS.from_epsg(3035)  # ETRS89
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_dir = "..\\..\\03_AM_NL_Amsterdam"
    in_type = "DTM"

    # Run function
    my_out = get_NL(in_type, in_dir, in_gs)
    print(my_out)
    profile = my_out["dtm_meta"]
    profile.update(compress='lzw')
    with rasterio.open(join(in_dir, "AM_NL_dtm.tif"),
                       "w", **profile, BIGTIFF='YES') as dst:
        dst.write(my_out["array"])
    # -----------------------------------

    # # Temporary input for debugging (DE):
    # # -----------------------------------
    # from shapely.geometry import box
    # import geopandas as gpd
    # import rasterio
    # from os.path import join
    # # [minx, miny, maxx, maxy]  - Cologne
    # # in_ext = [
    # #     6.75968155220865,
    # #     50.9130021454120,
    # #     6.7886,  # 6.94480973273774,
    # #     50.9353  # 51.0927711827503
    # # ]
    # in_ext = [340512, 5640162, 358082, 5664528]
    # in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    # in_crs = CRS.from_epsg(25832)  # WGS84
    # # ---
    # in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    # in_dir = "..\\..\\06_BO_DE"
    # # Access local repository:
    # in_region = "NRW"
    # in_type = "DTM"
    # # Run function
    # my_out = get_DE(in_type, in_dir, in_gs, in_region)
    # print(my_out)
    # profile = my_out["dtm_meta"]
    # profile.update(compress='lzw')
    # with rasterio.open(join(in_dir, "BO_DE_dtm.tif"),
    #                    "w", **profile, BIGTIFF='YES') as dst:
    #     dst.write(my_out["array"])
    # # -----------------------------------
