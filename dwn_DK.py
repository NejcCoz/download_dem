# -*- coding: utf-8 -*-
"""
Created on Thu Jan  9 10:32:41 2020

@author: ncoz
"""

import ftplib
import math
import sys
import zipfile
from os import makedirs, remove
from os.path import join, exists, split, basename

import geopandas as gpd
from pyproj import CRS


# ==============================================================================
# FUNCTIONS:
# ==============================================================================
def get_tile_names(aoi, dwn_dir, dt):
    # Make sure the temporary folder for download exists
    fishnet_dir = join(dwn_dir, "fishnet")
    if not exists(fishnet_dir):
        makedirs(fishnet_dir)

    # Read credentials for FTP server from file
    if basename(sys.argv[0]) == "storm_main_test.py":
        bup_dir = ".\\P1_Geometric\\P11_Data_Preparation\\anc_bup_files\\"
    else:
        bup_dir = ".\\anc_bup_files\\"
    file_credentials = gpd.read_file(join(bup_dir, "dk_credentials.txt"))
    try:
        f = open(file_credentials)
        (usrnam, psswrd) = f.readline().split(" ")
        if psswrd.endswith("\n"):
            psswrd = psswrd[:-1]
        f.close()
    except IOError:
        print("Error reading the password file!")
        sys.exit("Error reading the password file!")
    
    # Get FISHNET from FTP
    print("Downloading FISHNET from FTP")
    # FTP server address
    ftp_obj = ftplib.FTP("ftp.kortforsyningen.dk")
    # Connect to FTP server using credentials
    ftp_obj.login(user=usrnam, passwd=psswrd)
    if dt == "DTM":
        # Change working directory to DTM
        ftp_obj.cwd("dhm_danmarks_hoejdemodel/DTM/GRID")
        # Fishnet file name
        fn = "GRID_2014_DTM_SHP_UTM32-ETRS89.zip"
    elif dt == "LAZ":
        ftp_obj.cwd("dhm_danmarks_hoejdemodel/PUNKTSKY/GRID")
        fn = "GRID_2014_punktsky_SHP_UTM32-ETRS89.zip"
    else:
        raise ValueError(f"Unrecognized data type '{dt}' in get_tile_names.")

    # Create file from binary
    file = open(join(fishnet_dir, fn), "wb")
    ftp_obj.retrbinary("RETR " + fn, file.write)
    file.close()

    # Extract from ZIP and delete
    extract_zip(join(fishnet_dir, fn))
    remove(join(fishnet_dir, fn))

    # Quit FTP connection:
    ftp_obj.quit()

    if dt == "DTM":
        grd_nam = "2014_dtm.shp"
    elif dt == "LAZ":
        grd_nam = "2014_punktsky.shp"
    else:
        raise ValueError(f"Unrecognized data type '{dt}' in get_tile_names.")

    # Read fishnet with GeoPandas
    fishnet = gpd.read_file(join(fishnet_dir, grd_nam))
    
    # Create list with file names:
    print(f"Querying {dt} files on the FTP server...")
    tiles = []
    for _, row in fishnet.iterrows():
        ints_tile = aoi.intersects(row.geometry)
        if ints_tile[0]:
            tile_n = row['filename']
            # Names of LAZ files in fishnet do not match file names on FTP
            if dt == "LAZ":
                tile_n = tile_n.replace("punktsky", "punktsky".upper())
                tile_n = tile_n.replace("LAZ", "TIF")
            tiles.append(tile_n)
    return tiles
    
    
def extract_files(path_to_zip_file, gs_aoi, dt):
    """
    Extracts from ZIP only files covering the AOI
    IN: (1) path to Zip file
        (2) AOI polygon
        (3) data type (DTM or LAZ)
    """
    # Folder for extraction
    zip_dir, _ = split(path_to_zip_file)
    
    # Make sure the temporary folder for download exists:
    if not exists(zip_dir):
        makedirs(zip_dir)
        
    # Get values for the extents
    x_min = math.floor(gs_aoi.bounds['minx'][0]/1000)
    x_max = math.ceil(gs_aoi.bounds['maxx'][0]/1000)
    y_min = math.floor(gs_aoi.bounds['miny'][0]/1000)
    y_max = math.ceil(gs_aoi.bounds['maxy'][0]/1000)
    
    # Extract only selected files
    with zipfile.ZipFile(path_to_zip_file, 'r') as zzip:
        # List all TIF or LAZ files in the zip (ignore *.md5 files)
        if dt == "DTM":
            file_sfx = ".tif"
        elif dt == "LAZ":
            file_sfx = ".laz"
        else:
            raise ValueError(f"Unrecognized data type '{dt}' in extract_files.")
        tifs = [item for item in zzip.namelist() if item.endswith(file_sfx)]
        # Cycle through all files in the ZIP
        flnm: object
        for flnm in tifs:
            grid = flnm[:-4].split("_")
            # Test if file is covered by AOI
            test = (y_min <= int(grid[2]) < y_max
                    and x_min <= int(grid[3]) < x_max)
            # Extract files that fulfil the criteria
            if test:
                zzip.extract(flnm, path=zip_dir)
                
                
def extract_zip(path_to_zip_file):
    """
    Extracts ZIP files
    IN: path to Zip file
    """
    dwn_dir, _ = split(path_to_zip_file)
    with zipfile.ZipFile(path_to_zip_file, 'r') as zip_ref:
        print("Extracting the files now...")
        try:
            zip_ref.extractall(path=dwn_dir)
        except ValueError:
            print("Extraction of this file failed!")
        print("Done!")
        
        
# =============================================================================
# MAIN FUNCTION:
# =============================================================================
def download(gs_aoi, main_dir, data_type):
    """
    Download lidar data for Denmark
    IN:
        (1) gs_aoi - GeoPandas DataFrame, AOI extents as polygon
        (3) main_dir - string, location of temporary folder (download location)
    OUT:
        (1) out_msg - string
        (2) out_dir - path to directory with downloaded files
    """
    # All DK data is in ETRS89/UTM32N, so reproject if needed (EPSG:25832)
    dk_crs = 25832
    if dk_crs != gs_aoi.crs.to_epsg():
        aoi_pr = gs_aoi.to_crs(crs=dk_crs).envelope
    else:
        aoi_pr = gs_aoi.envelope
        
    # Get file names of the tiles covered by AOI
    tiles = get_tile_names(aoi_pr, main_dir, data_type)
    print(f"Found {len(tiles)} products")
    
    # Make sure the temporary folder for download exists
    dwn_dir = join(main_dir, data_type.lower())
    if not exists(dwn_dir):
        makedirs(dwn_dir)
    
    # Read credentials for FTP server from file
    file_credentials = ".\\anc_bup_files\\dk_credentials.txt"
    try:
        f = open(file_credentials)
        (usrnam, psswrd) = f.readline().split(" ")
        if psswrd.endswith("\n"):
            psswrd = psswrd[:-1]
        f.close()
    except IOError:
        print("Error reading the password file!")
        sys.exit("Error reading the password file!")

    if data_type == "DTM":
        fld = data_type
    elif data_type == "LAZ":
        fld = "PUNKTSKY"
    else:
        raise ValueError(f"Unrecognized data type '{data_type}' in download function.")

    # Retrieve files from FTP server
    ftp = ftplib.FTP("ftp.kortforsyningen.dk")  # Connect to host
    ftp.login(user=usrnam, passwd=psswrd)  # Connect to FTP w/ credentials
    ftp.cwd("dhm_danmarks_hoejdemodel/" + fld)  # Change working directory to DTM

    # Download ZIP files
    for i, fn in enumerate(tiles):
        print(f"Downloading {i + 1} of {len(tiles)}")

        # Create file and retrieve binary from FTP
        file = open(join(dwn_dir, fn), "wb")
        ftp.retrbinary("RETR " + fn, file.write)
        file.close()

        # Extract relevant TIF files
        print(f"Extracting {i + 1} of {len(tiles)}")
        extract_files(join(dwn_dir, fn), aoi_pr, data_type)
        remove(join(dwn_dir, fn))
    
    # Clean-up
    ftp.quit()

    # Message when finished
    out_msg = f"Finished downloading {data_type} files!"
    
    # Output dictionary:
    out = {'out_msg': out_msg,
           'out_dir': dwn_dir}
    
    return out


if __name__ == "__main__":
    from shapely.geometry import box
    # in_poly = box(4296708, 3762072, 4320480, 3786228)  # AOI
    in_poly = box(4320480, 3762072, 4321480, 3763072)  # Small for testing
    in_crs = CRS.from_epsg(3035)  # ETRS89-extended / LAEA Europe
    # ---
    in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
    in_type = "LAZ"
    in_dir = "..\\..\\dk_temp"

    # Run download
    r = download(in_gs, in_dir, in_type)

    print(r["out_msg"])
    print(f"Files saved in > {r['out_dir']}")
