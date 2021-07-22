# -*- coding: utf-8 -*-
"""Downloads DTM files for the selected area from INEGI data base (Mexico).

@author: ncoz

@copyright: ZRC SAZU (Novi trg 2, 1000 Ljubljana, Slovenia)

@history:
    Created on Thu Apr 21 10:43:42 2020
"""

import sys
import time
import zipfile
from os import makedirs
from os.path import join, basename, split, exists, dirname

import geopandas as gpd
import numpy as np
import rasterio
import requests
from bs4 import BeautifulSoup
from rasterio.crs import CRS
from rasterio.transform import from_origin


def get_tile_names(aoi):
    """Function finds file names and URLs for tiles."""
    # Location of fishnet file
    if basename(sys.argv[0]) == "storm_main_test.py":
        bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files\\MX"
    else:
        bup_dir = ".\\anc_bup_files\\MX"

    fishnet = gpd.read_file(join(bup_dir, "MX_lidar_fishnet.shp"))

    # Reproject AOI polygon to same CRS as fishnet (WGS84)
    grd_crs = CRS.from_string(fishnet.crs['init']).to_epsg()
    aoi_crs = aoi.crs.to_epsg()
    if grd_crs != aoi_crs:
        aoi_pr = aoi.to_crs(crs=grd_crs).envelope
    else:
        aoi_pr = aoi.envelope

    # Create a list of tile names covered by the polygon:
    clv_tiles = []
    for _, row in fishnet.iterrows():
        ints_tile = aoi_pr.intersects(row.geometry)
        if ints_tile[0]:
            clv_tiles.append(row.upc)

    return clv_tiles


def download_file(dwn_url, dwn_folder):
    """Download a file from URL."""
    # TODO try/except for html status code
    download_tile = requests.get(dwn_url)

    # Save the content as file
    _, dwn_fil = split(dwn_url)
    dwn_dir = join(dwn_folder, dwn_fil)
    open(dwn_dir, "wb").write(download_tile.content)
    # Message for successful download
    status_msg = f"{dwn_fil} succsesfully downloaded"

    return status_msg, dwn_fil


def extract_zip(path_to_zip_file):
    """
    Extracts ZIP files
    IN: path to Zip file
    """
    dwn_dir = dirname(path_to_zip_file)
    with zipfile.ZipFile(path_to_zip_file, 'r') as zzip:
        print("Extracting the files now...")
        for fil in zzip.namelist():
            if fil.endswith('.xyz') or fil.endswith('.html'):
                zip_info = zzip.getinfo(fil)
                zip_info.filename = basename(fil)
                try:
                    zzip.extract(zip_info, dwn_dir)
                    if fil.endswith('.xyz'):
                        fnm = join(dwn_dir, basename(fil))
                        print("XYZ extracted!")
                    else:
                        print("HTML extracted!")
                except ValueError:
                    print("Extraction of this file failed!")

    return fnm


def save_gtif(file_path):
    print("Converting XYZ to GTiff...")

    # Obtain CRS (UTM zone) from html file
    page = open(file_path[:-3] + "html", "r", encoding='latin_1')
    soup = BeautifulSoup(page, "lxml")

    # Find: <dt><em>UTM_Zone_Number:</em>  14</dt>
    res = soup.find_all("dt")
    for el in res:
        if el.find("em").text == "UTM_Zone_Number:":
            utm_zone = int(el.contents[1])

    # Select EPSG code (4484 for 11; 4485 for 12, etc...)
    epsg_mx = 4473 + utm_zone
    crs_mx = CRS.from_epsg(epsg_mx)

    # Read XYZ file
    with rasterio.open(file_path) as src:
        array = src.read()
        profile = src.profile
        west = src.bounds.left
        north = src.bounds.bottom
        resx, _ = src.res

    # Transform the array
    array = np.flip(array, axis=1)
    # Update metadata
    new_transform = from_origin(west, north, abs(resx), abs(resx))
    profile.update({"driver": "GTiff", "crs": crs_mx, "transform": new_transform})

    save_f = file_path[:-3] + "tif"
    with rasterio.open(save_f, "w", **profile) as dest:
        dest.write(array)

    print("Done!")
    return basename(save_f)


def download(gs_aoi, main_dir):

    # Get codes ("clave") for download
    tiles = get_tile_names(gs_aoi)

    # Make sure temporary folder for download exists:
    dwn_dir = join(main_dir, "DTM")
    if not exists(dwn_dir):
        makedirs(dwn_dir)

    # URL dor download (insert clave)
    mx_url = (
        "http://internet.contenidos.inegi.org.mx"
        "/contenidos/Productos/prod_serv/contenidos/espanol/bvinegi"
        "/productos/geografia/imagen_cartografica/1_10_000/lidar/"
        "/Terreno_ASCII/"
    )
    sufx = "_as.zip"

    tst = time.time()
    for i, upc in enumerate(tiles):
        print('{} of {}'.format(i + 1, len(tiles)))
        dwn_url = join(mx_url + str(upc) + sufx)
        dwn_stat, file_name = download_file(dwn_url, dwn_dir)
        # Extract XYZ and HTML with metadata (rwq. for UTM zone)
        xyz_pth = extract_zip(join(dwn_dir, file_name))
        save_gtif(xyz_pth)
        print('File {}.'.format(dwn_stat))
    out_msg = 'Finished downloading DTM files!'
    tst = time.time() - tst
    print(f"--- Time to download: {tst} sec. ---")

    # Output dictionary:
    out = {'out_msg': out_msg,
           'out_dir': dwn_dir}

    return out


if __name__ == "__main__":
    # Set temporary inputs
    from shapely.geometry import box
    # [minx, miny, maxx, maxy] (Acapulco)
    in_ext = [
        -99.87725514475203, 16.810318800012684,
        -99.83301834476471, 16.854555600000000
    ]
    in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    in_crs = CRS.from_epsg(4326)  # WGS84
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_dir = "..\\..\\mx_temp"

    # Run download
    r = download(in_gs, in_dir)

    print(r["out_msg"])
    print(f"Files saved in > {r['dwn_dir']}")
