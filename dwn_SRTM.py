# -*- coding: utf-8 -*-
"""Downloads DTM files for the selected area from SRTM data base.

@author: ncoz

@copyright: ZRC SAZU (Novi trg 2, 1000 Ljubljana, Slovenia)

@history:
    Created on Thu Feb 13 08:53:30 2020
"""

import sys
from os import makedirs
from os.path import join, exists, basename

import geopandas as gpd
import requests
from bs4 import BeautifulSoup
from pyproj import CRS


def get_tile_names(aoi):
    """Returns a list of file names for downloading the SRTM data.

    Function finds file names for tiles covered by the AOI polygon.
    The tiles are named after the lower-left coordinate of the tile in the WGS84
    CRS (EPSG:4326).

    For example:
        N46E014 for N 46 E 14 (Slovenia)
        N43W099 for N 43 W 99 (somewhere in USA)
    
    File names are obtained from a GeoJSON file:
        ./anc_bup_files/srtm30m_bounding_boxes.json
    """
    # Location of fishnet file
    if basename(sys.argv[0]) == "storm_main_test.py":
        bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files"
    else:
        bup_dir = ".\\anc_bup_files"

    fishnet = gpd.read_file(join(bup_dir, "srtm30m_bounding_boxes.json"))

    # Reproject AOI polygon to local CRS (if different):
    net_crs = CRS.from_string(fishnet.crs['init']).to_epsg()
    aoi_crs = aoi.crs.to_epsg()
    if net_crs != aoi_crs:
        aoi_pr = aoi.to_crs(crs=net_crs).envelope
    else:
        aoi_pr = aoi.envelope
    
    # Create a list of tile names covered by the polygon:
    tiles = []
    for _, row in fishnet.iterrows():
        ints_tile = aoi_pr.intersects(row.geometry)
        if ints_tile[0]:
            tiles.append(row['tile_name'])
    return tiles


def download_files(tiles_list, dwn_folder):
    """Download file from URL.
    
    """
    # SET URLS
    # --------
    # Start Page
    url = "https://ers.cr.usgs.gov"
    # Login page
    url_login = "https://ers.cr.usgs.gov/login/"
    # Build download URL
    url_pref = "https://earthexplorer.usgs.gov/download/8360/"
    url_suff = "/GEOTIFF/EE"

    # Open up a session
    with requests.Session() as s:
        # Open the login page
        rq = s.get(url)
        soup = BeautifulSoup(rq.text, 'lxml')

        # Get the csrf-token from meta tag
        csrf_token = soup.select('input[name="csrf"]')[0].get('value')
        # Removed 17/6/2020:
        # ncforminfo = soup.select('input[name="__ncforminfo"]')[0].get('value')

        # Read credentials for FTP server from file:
        if basename(sys.argv[0]) == "storm_main_test.py":
            bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files"
        else:
            bup_dir = ".\\anc_bup_files"
        file_credentials = join(bup_dir, "srtm_credentials.txt")
        try:
            with open(file_credentials) as f:
                (username, passw) = f.readline().split(" ")
                if passw.endswith("\n"):
                    passw = passw[:-1]
        except IOError:
            print('Error reading the password file!')
            sys.exit('Error reading the password file!')

        # Prepare payload for POST
        payload = {'username': username,
                   'password': passw,
                   'csrf': csrf_token}
        # Removed 17/6/2020: '__ncforminfo': ncforminfo

        s.post(url_login, data=payload, headers={})

        for i, tile_name in enumerate(tiles_list):
            print(f"{i + 1} of {len(tiles_list)}")

            # Build download URL
            url_tile = f"SRTM1{tile_name}V3"
            url_dwnld = url_pref + url_tile + url_suff

            page = s.get(url_dwnld)

            # SAVE FILE
            file_name = url_tile + ".tif"
            dwn_dir = join(dwn_folder, file_name)
            with open(dwn_dir, "wb") as f:
                f.write(page.content)

            # Message for successful download
            print(f"File {url_tile} successfully downloaded.")


def download(gs_aoi, main_dir):
    """Download of SRTM data from online repository.
    
    LOCAL CRS: EPSG:4326 - WGS 84 - Geographic
    """
    # Obtain tile names
    tiles_list = get_tile_names(gs_aoi)

    # Make sure temporary folder for download exists:
    dwn_dir = join(main_dir, 'srtm')
    if not exists(dwn_dir):
        makedirs(dwn_dir)

    print('\nDownloading SRTM files:')
    download_files(tiles_list, dwn_dir)
    out_msg = "Finished downloading SRTM files!"

    # Output dictionary:
    out_dict = {'out_msg': out_msg,
                'out_dir': dwn_dir}

    return out_dict


if __name__ == "__main__":
    # Temporary input for DEBUG:
    from shapely.geometry import box
    in_ext = [456500, 97200, 500500, 140200]  # [minx, miny, maxx, maxy]
    in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    in_crs = CRS.from_epsg(3794)  # D96/TM
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_dir = "..\\..\\srtm_temp"

    # Run download
    r = download(in_gs, in_dir)

    print(r["out_msg"])
    print(f"Files saved in > {r['out_dir']}")
