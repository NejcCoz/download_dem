# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 10:06:27 2020

@author: ncoz
"""

from owslib.wms import WebMapService

import geopandas as gpd
from shapely.geometry import box
from pyproj import CRS


wms = WebMapService('https://srsp-ows.jncc.gov.uk/'
                    'ows?service=wms&version=1.3.0&request=GetCapabilities')

layers = list(wms.contents)

wms[layers[-1]].boundingBox
wms[layers[-1]].styles

# AOI
in_ext = [3418692, 3716536, 3446474, 3742660]  # [minx, miny, maxx, maxy]
in_poly = box(in_ext[0], in_ext[1], in_ext[2], in_ext[3])
in_crs = CRS.from_epsg(3035)  # D96/TM
# ---
in_gs = gpd.GeoSeries(in_poly, crs=in_crs)
in_gs_uk = in_gs.to_crs(27700).envelope
in_gs_uk.to_file(".\\UK_aoi_extents")
bbox = in_gs_uk.bounds

# Make a request for imagery:
lay5 = layers[-1]
xy_box = round(bbox.iloc[0])
# xy_size = [(xy_box[2]-xy_box[0])/10, (xy_box[3]-xy_box[1])/10]
img = wms.getmap(layers=[lay5],
                 styles=['scotland:lidar-presence'],
                 srs='EPSG:27700',
                 bbox=(xy_box.minx, xy_box.miny, xy_box.maxx, xy_box.maxy),
                 size=(3150, 3000),
                 format='image/geotiff',
                 transparent=True
                 )

out = open('jpl_mosaic_visb.tif', 'wb')
out.write(img.read())
out.close()
