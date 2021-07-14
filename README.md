# SatProc
The satproc package is used to download and pre-process satellite data from the ESA Copernicus programme.

# The reference image for co-registration
The reference image for the co-registration was obtained by adding the ortofoto layer from Kortforsyningen in QGIS, and then saving the image as GeoTIFF.

Save geotiff (not vrt) in qgis by right clicking on ortofoto > export > save as
  - Set extent from the layer you want to coregister (e.g. a sentinel-2 tile)​
  - Set nodata=0