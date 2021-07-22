# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 10:14:07 2020

@author: ncoz
"""

import glob
from os import makedirs
from os.path import join, split, exists
from shutil import copyfile
from urllib.error import HTTPError

import geopandas as gpd
import numpy as np
import rasterio
import requests
from pyproj import CRS
from rasterio.transform import from_origin


# =============================================================================
# Functions
# =============================================================================
def get_tile_names(aoi, data_type):
    """
    Function finds file names and URLs for tiles covered by the AOI polygon.
    """
    # Read fishnet from URL:
    fishnet_url = ("http://gis.arso.gov.si/"
                   "related/lidar_porocila/lidar_fishnet_D96TM.zip")
    try:
        fishnet = gpd.read_file(fishnet_url)
    except HTTPError:
        # Use backed-up version if API unavailable, might not be up-to-date
        print("Problems accessing Fishnet from web...")
        print("Using local (backup) version instead.")
        fishnet = gpd.read_file(".\\P1_Geometric\\P11_Data_Preparation"
                                "\\anc_bup_files\\SI\\LIDAR_FISHNET_D96.shp")

    # Reproject AOI polygon local CRS if needed (EPSG 3794):
    net_crs = CRS.from_string(fishnet.crs['init']).to_epsg()
    aoi_crs = aoi.crs.to_epsg()
    if aoi_crs != net_crs:
        aoi_pr = aoi.to_crs(crs=net_crs).envelope
    else:
        aoi_pr = aoi.envelope

    # Create a list of tile names covered by the polygon:
    if data_type == "DTM":
        url_main = "http://gis.arso.gov.si/lidar/dmr1/"
        url_mid = "/D96TM/TM1_"
        url_ext = ".asc"
    elif data_type == "LAZ":
        url_main = "http://gis.arso.gov.si/lidar/gkot/laz/"
        url_mid = "/D96TM/TM_"
        url_ext = ".laz"
    else:
        raise ValueError(f"Unrecognized data type '{data_type}' dwn_SI.py.")
    tiles = []
    for _, row in fishnet.iterrows():
        ints_tile = aoi_pr.intersects(row.geometry)
        if ints_tile[0]:
            tiles.append(url_main
                         + row['BLOK']
                         + url_mid
                         + row['NAME']
                         + url_ext)
    return tiles


def download_file(dwn_url, dwn_folder):
    """Download a file from URL."""
    download_tile = requests.get(dwn_url)

    # Save the content as file
    _, dwn_fil = split(dwn_url)
    dwn_dir = join(dwn_folder, dwn_fil)
    open(dwn_dir, "wb").write(download_tile.content)
    # Message for successful download
    status_msg = f"{dwn_fil} succsesfully downloaded"

    return status_msg, dwn_fil


def copy_local(dwn_url, copy_dir):
    """Function copies selected files from local repository.

    It creates the path to local file by taking the file name from the
    URL and joining it with the local path.

    NOTE: The CRS of TIFs in repository is not defined, instead
    of just copying, update the GeoTIFF instead.

    Future-proofed: if CRS is missing then update, else just copy.
    """
    # Path to local repository of DTMs
    local_dir = "l:\\Slovenija\\DEM_D96"
    # Prepare paths
    _, name = split(dwn_url[:-4])
    fil_nam = name + ".tif"
    src_pth = join(local_dir, fil_nam)
    dst_pth = join(copy_dir, fil_nam)

    # Open TIF file
    tif = rasterio.open(src_pth)

    # Check CRS
    if tif.crs is None:
        meta = tif.profile.copy()
        meta.update({"crs": CRS.from_epsg(3794)})  # D96/TM
        array = tif.read()
        with rasterio.open(dst_pth, "w", **meta) as dest:
            dest.write(array)
        tif.close()
    else:
        tif.close()
        copyfile(src_pth, dst_pth)

    # Output
    status_msg = f"{fil_nam} succsesfully copied"

    return status_msg, fil_nam


def asc_to_gtif(i_dir):
    """
    This tool re-formats ASC files into GeoTIFF format.

    Parameters:
    -----------
    i_dir : str
        Directory with ASC files

    Returns:
    --------
    str
        Out message
    """

    # Set search for all files with suffix in specified folder
    q = join(i_dir, "*.asc")
    # List of all TIF files
    asc_fps = glob.glob(q)

    # Loop over all files
    for item in asc_fps:
        # Open ASC file
        data = np.loadtxt(item, delimiter=";")

        # Determine the size of the output array
        x_size = np.count_nonzero(data[:, 0] == data[0, 0])
        y_size = np.count_nonzero(data[:, 1] == data[0, 1])

        # Transform columns to grid
        arr = np.reshape(data[:, 2], (1, x_size, y_size), order="F")
        arr = np.flip(arr, axis=1)

        # Determine pixel resolution
        arr_x = np.reshape(data[:, 0], (x_size, y_size), order="F")
        pix_x = arr_x[0, 1] - arr_x[0, 0]
        arr_y = np.reshape(data[:, 1], (x_size, y_size), order="F")
        pix_y = arr_y[1, 0] - arr_y[0, 0]

        # Determine top-left coordinates
        left = data[:, 0].min()
        top = data[:, 1].max() + pix_y  # Adjust for pixel size

        # Set meta data for GeoTIF
        transform = from_origin(left, top, pix_x, pix_y)
        si_crs = {'init': 'EPSG:3794'}  # D96/TM

        _, name = split(item[:-4])
        save_file = join(i_dir, name + '.tif')

        # Save array as with metadata as GeoTIFF
        new_dataset = rasterio.open(save_file, "w", driver="GTiff",
                                    height=arr.shape[1], width=arr.shape[2],
                                    count=1, dtype=str(arr.dtype),
                                    crs=si_crs,
                                    transform=transform, compress="lzw")
        new_dataset.write(arr)
        new_dataset.close()

        # Remove ASC file
        # remove(item)

    # Output message:
    out_msg = 'Successfully converted ASC files to GeoTIFF!'

    return out_msg


# =============================================================================
# MAIN FUNCTION:
# =============================================================================
def download(data_type, gs_aoi, main_dir, local_rep=True):
    """
    Copy lidar data for Slovenia from a local repository.

    Set local_rep=False to download from ARSO website instead.
    """
    # Get URLs for tiles covered by a polygon:
    tiles = get_tile_names(gs_aoi, data_type)
    print(f'Found {len(tiles)} products')

    # Make sure temporary folder for download exists:
    dwn_dir = join(main_dir, data_type)
    if not exists(dwn_dir):
        makedirs(dwn_dir)

    if local_rep:
        # Copy DTM files from local repository:
        print('\nCopying DTM files:')
        for num, name in enumerate(tiles):
            print('{} of {}'.format(num+1, len(tiles)))
            dwn_stat, _ = copy_local(name, dwn_dir)
            print('File {}.'.format(dwn_stat))
        out_msg = 'Finished copying DTM files!'
    else:
        # Download DTM files:
        print(f"\nDownloading {data_type} files:")
        for num, name in enumerate(tiles):
            print('{} of {}'.format(num+1, len(tiles)))
            dwn_stat, _ = download_file(name, dwn_dir)
            print('File {}.'.format(dwn_stat))
        if data_type == "DTM":
            # Convert to Geotiff
            print("Converting to GeoTIFF...")
            result = asc_to_gtif(dwn_dir)
            print(result)
        out_msg = "Finished downloading DTM files!"

    # Output dictionary:
    out = {'out_msg': out_msg,
           'out_dir': dwn_dir}

    return out


if __name__ == "__main__":
    # Set temporary inputs (define area of interest as box polygon)
    from shapely.geometry import box
    in_ext = [456500, 97200, 457500, 99200]  # [minx, miny, maxx, maxy]
    in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    # Define CRS (coordinate reference system)
    in_crs = CRS.from_epsg(3794)  # EPSG:3794 for the D96/TM (nova slovenska projekcija)
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_type = "DEM"  # LAZ or DEM
    # Define save location (folder)
    in_dir = "..\\..\\si_temp"

    # Run download
    r = download(in_type, in_gs, in_dir, False)

    print(r["out_msg"])
    print(f"Files saved in > {r['out_dir']}")
