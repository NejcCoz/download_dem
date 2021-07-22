# -*- coding: utf-8 -*-
"""
Created on Fri May 08 14:41:09 2020

@author: ncoz

Downloads DTM files for Germany.
- NRW

"""

import glob
import gzip
import shutil
import sys
from os import remove, makedirs
from os.path import join, split, exists, basename

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.crs import CRS
from rasterio.transform import from_origin


# =============================================================================
# Functions
# =============================================================================
def get_tile_names(aoi, data_type):
    """Function finds file names and URLs for tiles.

    Fishnet for finding tiles is read from file!
    """
    # Read NRW grid polygons from file:
    if basename(sys.argv[0]) == "storm_main_test.py":
        bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files\\DE"
    else:
        bup_dir = ".\\anc_bup_files\\DE"

    fishnet = gpd.read_file(join(bup_dir, "fishnet_DE.shp"))

    # Reproject AOI polygon to fishnet CRS (ETRS89/UTM32N, EPSG:25832)
    grd_crs = CRS.from_string(fishnet.crs['init']).to_epsg()
    aoi_crs = aoi.crs.to_epsg()
    if grd_crs != aoi_crs:
        aoi_pr = aoi.to_crs(crs=grd_crs).envelope
    else:
        aoi_pr = aoi.envelope

    # Create a list of tile names covered by the polygon:
    # ---------------------------------------------------
    url_path = "https://www.opengeodata.nrw.de/produkte/geobasis/hm/"
    if data_type == "DTM":
        url_main = join(url_path, "dgm1_xyz/dgm1_xyz/")
        file_type = "file_name"
    elif data_type == "LAZ":
        url_main = join(url_path, "3dm_l_las/3dm_l_las/")
        file_type = "laz_name"
    else:
        raise ValueError(f"Unrecognized data type '{data_type}' dwn_DE.py.")
    tiles = []
    for _, row in fishnet.iterrows():
        ints_tile = aoi_pr.intersects(row.geometry)
        # TODO: Only do this for LAZ download (skip for DTM)
        if ints_tile[0]:
            tiles.append(url_main + row[file_type])
            ax = round(row.left / 1000)
            ay = round(row.bottom / 1000)
            tiles.append(url_main + f"3dm_32_{ax + 1}_{ay}_1_nw.laz")
            tiles.append(url_main + f"3dm_32_{ax}_{ay + 1}_1_nw.laz")
            tiles.append(url_main + f"3dm_32_{ax + 1}_{ay + 1}_1_nw.laz")

    return tiles


def download_file(dwn_url, dwn_folder):
    """Downloads a file from URL."""
    download_tile = requests.get(dwn_url)

    # Filename (for saving and status message)
    _, dwn_fil = split(dwn_url)

    if download_tile.status_code == 200:
        # Save the content as file
        dwn_dir = join(dwn_folder, dwn_fil)
        open(dwn_dir, 'wb').write(download_tile.content)

        # Message for successful download
        status_msg = f"{dwn_fil} succsesfully downloaded"
    else:
        status_msg = f"{dwn_fil} does not exist. Skipped."
        # Set to None to prevent further processing of nonexistent file
        dwn_fil = None

    return status_msg, dwn_fil


def extract_zip(path_to_zip_file):
    """Extracts gZIP files

    IN: path to Zip file
    """
    with gzip.open(path_to_zip_file, 'rb') as f_in:
        print('Extracting...')
        with open(path_to_zip_file[:-3], 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        print('Done!')


def xyz_to_gtif(i_dir):
    """Re-formats XYZ files into GeoTIFF format.

    It is set up to work for DTM data from Germany (NRW). The data is stored in
    *.xyz files. Different values are separated by space, with the last column
    separated by 3 space characters. The first coordinate has to be modified,
    ie subtract 32000000, to get the correct value for EPSG:25832 CRS.


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
    q = join(i_dir, "*.xyz")
    # List of all TIF files
    fps = glob.glob(q)

    # Loop over all files
    for i, item in enumerate(fps):
        print(f"{i+1} of {len(fps)}")

        data = np.loadtxt(item)

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
        left = data[:, 0].min() - 32000000  # Adjust for EPSG:25832
        top = data[:, 1].max() + pix_y  # Adjust for pixel size

        # Set meta data for GeoTIF
        transform = from_origin(left, top, pix_x, pix_y)
        de_crs = {'init': 'EPSG:25832'}  # ETRS89 / UTM 32N

        _, name = split(item[:-4])
        save_file = join(i_dir, name + '.tif')

        # Save array as with metadata as GeoTIFF
        new_dataset = rasterio.open(save_file, "w", driver="GTiff",
                                    height=arr.shape[1], width=arr.shape[2],
                                    count=1, dtype=str(arr.dtype),
                                    crs=de_crs,
                                    transform=transform, compress="lzw")
        new_dataset.write(arr)
        new_dataset.close()

        # Remove XYZ file
        # remove(item)

    # Output message:
    out_msg = f"Successfully converted {len(fps)} XYZ files to GeoTIFF!"

    return out_msg


# =============================================================================
# REGIONS:
# =============================================================================
def dwn_NRW(data_type, gs_aoi, main_dir):
    """Downloads lidar data for Germany (NRW)

    From the NRW open data website:
    https://www.opengeodata.nrw.de/produkte/geobasis/hm/dgm1_xyz/dgm1_xyz/
    """

    # Get URLs for tiles covered by a polygon:
    # ----------------------------------------
    tiles = get_tile_names(gs_aoi, data_type)
    print(f'Found {len(tiles)} products')

    # Make sure temporary folder for download exists:
    # -----------------------------------------------
    dwn_dir = join(main_dir, data_type)
    if not exists(dwn_dir):
        makedirs(dwn_dir)

    # DOWNLOAD DTM FILES & UNZIP:
    # ---------------------------
    if data_type == "DTM":
        print('\nDownloading DTM files:')
        for num, name in enumerate(tiles):
            print(f"{num + 1} of {len(tiles)}")
            dwn_stat, file_name = download_file(name, dwn_dir)
            print(f"File {dwn_stat}.")
            if file_name:
                extract_zip(join(dwn_dir, file_name))
                # Delete ZIP file after extraction
                remove(join(dwn_dir, file_name))
        print("Converting all files to GeoTIFF...")
        result = xyz_to_gtif(dwn_dir)
        print(result)
        out_msg = 'Finished downloading DTM files!'
    else:
        print('\nDownloading LAZ files:')
        for num, name in enumerate(tiles):
            print(f"{num + 1} of {len(tiles)}")
            dwn_stat, file_name = download_file(name, dwn_dir)
            print(f"File {dwn_stat}.")
        out_msg = 'Finished downloading LAZ files!'
    # Output dictionary:
    # ------------------
    out = {'out_msg': out_msg,
           'out_dir': dwn_dir}

    return out


# =============================================================================
# MAIN FUNCTION:
# =============================================================================
def download(data_type, gs_aoi, main_dir, region):
    """Selects from which region to download the data from"""
    if region == "NRW":
        out = dwn_NRW(data_type, gs_aoi, main_dir)
    else:
        # TODO: raise exception
        print(f"No such region in download DE: {region}")
        out = None

    return out


if __name__ == "__main__":
    # Set temporary inputs
    from shapely.geometry import box

    # [minx, miny, maxx, maxy]  - Cologne
    in_ext = [
        6.75968155220865,
        50.9130021454120,
        6.7886,  # 6.94480973273774,
        50.9353  # 51.0927711827503
    ]

    in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
    in_crs = CRS.from_epsg(4326)  # WGS84
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_type = "DTM"
    in_dir = "..\\..\\de_temp"

    # Run download
    r = download(in_type, in_gs, in_dir, "NRW")

    print(r["out_msg"])
    print(f"Files saved in > {r['out_dir']}")

    # in_dir = "..\\..\\..\\..\\test79"
    # a = xyz_to_gtif(in_dir)
    # print(a)
