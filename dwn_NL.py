# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 09:51:09 2019

@author: ncoz

Subroutine of anc_main for downloading Lidar data for Netherlands.

from dwn_NL import download

out = download(data_type, gdf_AOI, main_dir)

Required input:
    (1) data_type = 'LAZ' for Point Cloud or 'DTM' for DTM GeoTIFF
    (2) gs_aoi   = polygon representing AOI in GeoSeries format (Geopandas)
    (3) main_dir  = location of directory for temporary files
"""

import sys
import zipfile
from os import remove, makedirs
from os.path import join, split, exists, basename
from urllib.error import URLError

import geopandas as gpd
import requests
from pyproj import CRS


# =============================================================================
# Functions
# =============================================================================
def get_tile_names(aoi):
    """Function finds file names and URLs for tiles covered by the AOI polygon.
    Currently only AHN3 API is used, however, if required API for AHN2 can also
    be included (atm commented-out).

    INPUT:
        (1) aoi: AOI polygon sa GeoDataFrame
    OUTPUT:
        (1) tile_names: names of tiles
        (2) LAZ_url: URLs for LAZ files
        (3) DTM_url: URLs for DTM files
    """
    # Read AHN grid polygons from API:
    ahn3_api = ("https://opendata.arcgis.com/datasets"
                "/9039d4ec38ed444587c46f8689f0435e_0.geojson")
    # AHN2_api = ("https://opendata.arcgis.com/datasets"
    #             "/6c898cd924c441d5aea33b3bc6cc117a_0.geojson'")
    try:
        ahn3_gj = gpd.read_file(ahn3_api)
    except URLError:
        # Use backed-up version if API unavailable, might not be up-to-date
        print("Problems accessing AHN3 fishnet API. Using backup version.")

        if basename(sys.argv[0]) == "storm_main_test.py":
            bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files\\"
        else:
            bup_dir = ".\\anc_bup_files\\"
        ahn3_gj = gpd.read_file(join(bup_dir, "ahn3.geojson"))
    
    # Reproject AOI polygon to WGS84 (if AOI in different CRS):
    ahn_crs = CRS.from_string(ahn3_gj.crs['init']).to_epsg()
    aoi_crs = aoi.crs.to_epsg()
    if ahn_crs != aoi_crs:
        aoi_pr = aoi.to_crs(crs=ahn_crs).envelope
    else:
        aoi_pr = aoi.envelope

    # Create a list of tile names covered by the polygon:
    # ---------------------------------------------------
    tiles = {'tile_names': [],
             'laz_url': [],
             'dtm_url': [],
             'ahn2_i': [],
             'ahn2_r': []}
    for _, row in ahn3_gj.iterrows():
        ints_tile = aoi_pr.intersects(row.geometry)
        if ints_tile[0]:
            tiles['tile_names'].append(row['Kaartblad'])
            tiles['laz_url'].append(row['AHN3_LAZ'])
            tiles['dtm_url'].append(row['AHN3_05m_DTM'])
            tiles['ahn2_i'].append(row['ahn2_05m_i'])
            tiles['ahn2_r'].append(row['ahn2_05m_r'])
    return tiles


def download_file(dwn_url, dwn_folder):
    """Downloads a file from URL.
    INPUT:
        dwn_url - URL address of the file
        dwn_folder - folder for downloads
    OUTPUT:
        status_msg - message of successful download
        dwnFIL - file name
    """
    # Prepare path
    _, dwn_fil = split(dwn_url)
    dwn_dir = join(dwn_folder, dwn_fil)

    # download_tile = requests.get(dwn_url)
    open(dwn_dir, 'wb').write(requests.get(dwn_url).content)

    # Message for successful download
    status_msg = dwn_fil + ' succsesfully downloaded'

    return status_msg, dwn_fil


def extract_zip(path_to_zip_file):
    """Extracts ZIP files

    IN: path to Zip file
    """
    dwn_dir, _ = split(path_to_zip_file)
    with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
        print('Extracting the files now...')
        try:
            zip_ref.extractall(path=dwn_dir)
        except ValueError:
            print('Extraction of this file failed!')
        print('Done!')


# =============================================================================
# MAIN FUNCTION:
# =============================================================================
def download(data_type, gs_aoi, main_dir):
    """Downloads lidar data for Netherlands

    IN:
        (1) data_type - string 'DTM' or 'LAZ'
        (2) gs_aoi - GeoPandas DataFrame, AOI extents as polygon
        (3) main_dir - string, location of temporary folder (download location)
    OUT:
        (1) out_msg - string
        (2) out_dir - path to directory with downloaded files
    """
    # Get URLs for tiles covered by a polygon:
    # ----------------------------------------
    tiles = get_tile_names(gs_aoi)
    print('Found {} products'.format(len(tiles['tile_names'])))

    # Make sure temporary folder for download exists:
    # -----------------------------------------------
    dwn_dir = join(main_dir, data_type)
    if not exists(dwn_dir):
        makedirs(dwn_dir)

    # Proceed to download:
    # --------------------
    if data_type == 'DTM':
        # DOWNLOAD DTM FILES & UNZIP:
        # ---------------------------
        print('\nDownloading DTM files:')
        for num, name in enumerate(tiles['dtm_url']):
            print('{} of {}'.format(num+1, len(tiles['dtm_url'])))
            dwn_stat, file_name = download_file(name, dwn_dir)
            print('File {}.'.format(dwn_stat))
            extract_zip(join(dwn_dir, file_name))
            # Delete ZIP file after extraction
            remove(join(dwn_dir, file_name))
        
        # Finished downloading:
        # ---------------------
        out_msg = 'Finished downloading DTM files!'
    
    elif data_type == 'LAZ':
        # DOWNLOAD LAZ FILES:
        # -------------------
        print('\nDownloading LAZ files:')
        for num, name in enumerate(tiles['laz_url']):
            print('{} of {}'.format(num+1, len(tiles['laz_url'])))
            dwn_stat, _ = download_file(name, dwn_dir)
            print('File {}.'.format(dwn_stat))
            
        # Finished downloading:
        # ---------------------
        out_msg = 'Finished downloading LAZ files!'
        
    else:
        dwn_dir = None
        out_msg = 'Unexpected data_type'
        
    # Output dictionary:
    # ------------------
    out = {'out_msg': out_msg,
           'out_dir': dwn_dir}
    
    return out


if __name__ == "__main__":
    # Set temporary inputs
    from shapely.geometry import box
    in_ext = [4019220, 3172674, 4023580, 3178624]  # [minx, miny, maxx, maxy]
    in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    in_crs = CRS.from_epsg(3035)  # ETRS89
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_type = "DTM"  # "DTM" or "LAZ"
    in_dir = ".\\test79"

    # Run download
    r = download(in_type, in_gs, in_dir)

    print(r["out_msg"])
    print(f"Files saved in > {r['dwn_dir']}")
