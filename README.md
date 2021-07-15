# SatProc
The satproc package is used to download and pre-process satellite data from the ESA Copernicus programme.

IMPORTANT: The api for downloading orbit files has been moved, so the pre-processing of the individual Sentinel-1 tiles is broken. To fix it, the orbit files needs to be downloaded (maybe manually), and then referenced in the app/data/graphs/preprocessGraph.xml somehow (ie. in the processing graph for the ESA SNAP software). 

# Downloading and processing large dataset
Use network drive folder for storing the output. Navigate to the satproc folder and run the docker command 

One using temp folder in downloads:
docker run --rm -p 8080:8080 -v "$PWD":/workspace/mnt -v /home/jhj/Downloads/satproc/output_dir:/workspace/output_dir -v /home/jhj/Downloads/satproc/output_dir_coreg:/workspace/output_dir_coreg --shm-size 512m -e AUTHENTICATE_VIA_JUPYTER="env" -e INCLUDE_TUTORIALS=false -v /etc/localtime:/etc/localtime:ro jacobjeppesen/research-env-customized:0.2.0

docker run --rm -p 8080:8080 -v "$PWD":/workspace/mnt -v /network_drive_folder_path:/workspace/output_dir -v /network_drive_coreg_folder_path:/workspace/output_dir_coreg --shm-size 512m -e AUTHENTICATE_VIA_JUPYTER="env" -e INCLUDE_TUTORIALS=false -v /etc/localtime:/etc/localtime:ro jacobjeppesen/research-env-customized:0.2.0

Run the notebook in /mnt/app/download_and_process_dataset.ipynb

# Perform the co-registration
Run the notebook in /mnt/app/coregister_dataset.ipynb

The reference image for the co-registration was obtained by adding the ortofoto layer from Kortforsyningen in QGIS, and then saving the image as GeoTIFF.

Run the same docker command as above: 
docker run --rm -p 8080:8080 -v "$PWD":/workspace/mnt -v /network_drive_folder_path:/workspace/output_dir -v /network_drive_coreg_folder_path:/workspace/output_dir_coreg --shm-size 512m -e AUTHENTICATE_VIA_JUPYTER="env" -e INCLUDE_TUTORIALS=false -v /etc/localtime:/etc/localtime:ro jacobjeppesen/research-env-customized:0.2.0

Save geotiff (not vrt) in qgis by right clicking on ortofoto > export > save as
  - Set extent from the layer you want to coregister (e.g. a sentinel-2 tile)​
  - Set nodata=0