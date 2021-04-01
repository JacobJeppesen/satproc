from multiprocessing import Pool
from pathlib import Path
import shutil
import os

import numpy as np
import pandas as pd
from absl import flags, logging
from tqdm import tqdm

from src.sentinelprocessors.s1processor import S1Processor
from src.sentinelprocessors.s2processor import S2Processor
from src.sentinelprocessors.s3processor import S3Processor
from src.sentinelprocessors.s5processor import S5Processor

FLAGS = flags.FLAGS


class ProcessPipeliner(object):
    def __init__(self, products_df, directory=Path('/data/')):
        self.directory = directory
        self.pbar = None
        self.products_df = self.__concat_product_paths(products_df)
        self.satellite = FLAGS.satellite
        self.s1_num_proc = FLAGS.s1_num_proc
        self.s2_num_proc = FLAGS.s2_num_proc

    def process_products(self):
        if self.satellite == 's1' or self.satellite == 'all':
            logging.info("### Processing Sentinel-1 products ###")
            s1_products_df = self.products_df[self.products_df['platformname'] == 'Sentinel-1']
            s1processor = S1Processor(s1_products_df, self.directory)
            # Create folders now to avoid multiple processes trying to create the same folder later (leads to errors)
            s1processor.create_parent_folders()

            # Create a vrt for each product date
            s1_titles = s1_products_df['title'].values
            # Get the product data and absolute orbit to get a unique identifier for each Sentinel-1 pass
            product_dates_abs_orbits = [(title[17:25] + title[48:55]) for title in s1_titles]
            product_dates_abs_orbits = np.unique(product_dates_abs_orbits)
            
            # TODO: To improve processing speed, run the parallel processing (ie. pool.map()) over the 
            #       product_date_abs_orbit instead of the individual tiles inside the for-loop (just remove
            #       the pool.map() of the individual tiles and use a for-loop to iterate through the tiles). 
            #       This would results in the co-registration and the vrt_to_geotiff running in parallel, 
            #       which should significantly decrease the processing time. Note that the the maximum number
            #       of processes should be kept the same, as multiple number of tiles will be processed in parallel,
            #       though not from the necessarily from the same date. In general, always try to perform the 
            #       parallelization on the outer-most for-loop. The downside is that if the scene to processed
            #       is from a single date with multiple tiles, there will be no parallization (except for the 
            #       built-in in some of the used processing functions). But that should be fine. Generally, when
            #       there is a big need for parallization, it is because data from multiple dates are being 
            #       processed. For single-date datasets, the user can wait a bit longer.

            # TODO: Get the check for processed products finalized
            # pseudo-code to check all previously processed products
            data_directory = Path('data')
            output_directory = data_directory / 'output_data' / 's1' / 'combined'
            if output_directory.exists():
                filenames = list(output_directory.glob('*.tif'))
                processed_date_abs_orbit = [filename[4:17] for filename in filenames]
                # Then use the processed_date_abs_orbit to check if the product has been processed in the next loop
            
            failed_product_date_abs_orbit = []
            for product_date_abs_orbit in tqdm(product_dates_abs_orbits):
                # NOTE: The code below is used for the Elsevier paper. Do not trust it too much. The s1_products_df_date
                #       should be properly implemented, and so should the co-registering of Sentinel-1 data.
                print("\n")
                # try:
                if True:
                    # Process the individual tiles
                    date = product_date_abs_orbit[:8]
                    abs_orbit = product_date_abs_orbit[9:]
                    s1_products_df_date = s1_products_df[s1_products_df['title'].str.contains(date)]
                    s1_products_df_date = s1_products_df_date[s1_products_df_date['title'].str.contains(abs_orbit)]
                    s1processor.products_df = s1_products_df_date.copy()

                    # Multiprocessing method from here: https://stackoverflow.com/a/5442981/12045808 (if you want tqdm then look
                    # here https://github.com/tqdm/tqdm/issues/484#issuecomment-353383768)
                    index_arg = range(len(s1_products_df_date))
                    with Pool(processes=self.s1_num_proc) as pool:
                        pool.map(s1processor.process, index_arg)

                    # Create the vrt with the combined tiles
                    vrt_path = s1processor.create_vrt_and_cog(product_date_abs_orbit, create_thumbnail=True)

                    # Co-register
                    if FLAGS.s1_coregister:
                        logging.info("Co-registering")
                        coreg_path = (vrt_path.parent / f'{vrt_path.stem}_coreg').with_suffix('.tif')
                        s1processor.temp_coregister_function_for_elsevier_intepretability_paper(vrt_path, coreg_path)

                    # Move to final output path
                    if FLAGS.move_to_output_directory and FLAGS.output_directory is not None:
                        tif_path = vrt_path.with_suffix('.tif')
                        png_path = vrt_path.with_suffix('.png')
#                         coreg_new_path = (Path(FLAGS.output_path) / vrt.name).with_suffix('.tif')
                        new_output_dir = Path(FLAGS.output_directory)
                        tif_new_path = new_output_dir / tif_path.name
                        png_new_path = new_output_dir / png_path.name
                        if not tif_new_path.parent.exists():  # Create directory if it does not exist
                            os.makedirs(tif_new_path.parent)
                        logging.info(f"Moving {str(png_path)} to output directory {str(png_new_path)}")
                        shutil.move(png_path, png_new_path)
                        logging.info(f"Finished moving {str(png_path)} to output directory {str(png_new_path)}")
                        logging.info(f"Moving {str(tif_path)} to output directory {str(tif_new_path)}")
                        shutil.move(tif_path, tif_new_path)
                        logging.info(f"Finished moving {str(tif_path)} to output directory {str(tif_new_path)}")
                    else:
                        pass
                        
                    if FLAGS.s1_del_intermediate:
                        # Delete all the individual tile data. Used for Elsevier paper due to lack of storage capacity. 
                        logging.info("Deleting output_data/s1/GRD folder")
                        grd_data_path = Path('data/output/output_data/s1/GRD')
                        shutil.rmtree(grd_data_path)
                # except:
                #     logging.info(f"Following date and absolute orbit failed: {product_date_abs_orbit}")
                #     failed_product_date_abs_orbit.append(product_date_abs_orbit)
                print("\n")
                print("\n")
                
            for failed_product in failed_product_date_abs_orbit:
                logging.info(f"Following product failed processing: {failed_product}")                

        if self.satellite == 's2' or self.satellite == 'all':
            logging.info("### Processing Sentinel-2 products ###")
            s2_products_df = self.products_df[self.products_df['platformname'] == 'Sentinel-2']
            s2processor = S2Processor(s2_products_df, self.directory)

            # Process the individual tiles
            # Note: Multiprocessing method from here: https://stackoverflow.com/a/5442981/12045808 (if you want tqdm
            # then look here https://github.com/tqdm/tqdm/issues/484#issuecomment-353383768)
            index_arg = range(len(s2_products_df))
            with Pool(processes=self.s2_num_proc) as pool:
                pool.map(s2processor.process_tiles, index_arg)
            # parmap.map(s2processor.process_tiles, index_arg, pm_pbar=True, pm_processes=2)

            # Combine the tiles by creating vrt files and coregister each vrt file and save as geotiff.
            s2processor.create_vrt_files_and_coregister()

        if self.satellite == 's3' or self.satellite == 'all':
            logging.info("### Processing Sentinel-3 products ###")
            s3_products_df = self.products_df[self.products_df['platformname'] == 'Sentinel-3']
            s3processor = S3Processor(s3_products_df, self.directory)
            index_arg = range(len(s3_products_df))
            with Pool(processes=6) as pool:
                pool.map(s3processor.process, index_arg)

        if self.satellite == 's5p' or self.satellite == 'all':
            logging.info("### Processing Sentinel-5p products ###")
            s5_products_df = self.products_df[self.products_df['platformname'] == 'Sentinel-5 Precursor']
            s5processor = S5Processor(s5_products_df, self.directory)
            index_arg = range(len(s5_products_df))
            with Pool(processes=6) as pool:
                pool.map(s5processor.process, index_arg)

    def __concat_product_paths(self, products_df):
        """
        Concatenates the folder paths required for processing.

        :param products_df: Dataframe with all products (as returned from SentinelSat)
        :return: An updated dataframe with product paths concatenated to the products
        """
        products_df[['tile_path', 'product_path', 'product_type']] = \
            products_df.apply(self.__get_product_path, directory=self.directory, axis=1)

        return products_df

    @staticmethod
    def __get_product_path(row, directory):
        if row.platformname == 'Sentinel-1':
            # Directory structure from here: https://roda.sentinel-hub.com/sentinel-s1-l1c/GRD/readme.html
            # Note: The polarisation part of the directory structure has been skipped here
            product = row['title']
            product_type = row['producttype']
            begin_time = row['beginposition']
            year, month, day = str(begin_time)[0:4], str(begin_time)[5:7], str(begin_time)[8:10]
            mode = row['sensoroperationalmode']
            product_path = (directory / 'output_data' / 's1' / product_type / year / month /
                            day / mode / product).with_suffix('.SAFE')
            tile_path = ""

        elif row.platformname == 'Sentinel-2':
            # Get product directory path
            product = row['title']
            utm_code = product[39:41]  # e.g. 10
            latitude_band = product[41:42]  # e.g. S
            square = product[42:44]  # e.g. DG
            tile_path = directory / 'output_data' / 's2' / 'tiles' / utm_code / latitude_band / square
            product_path = (tile_path / product).with_suffix('.SAFE')

            # Damn you ESA for making an extra subfolder under granule!
            # Note: The following only works for some products - so you have to unzip the products before processing
            # abs_orbit_num = str(row.orbitnumber).zfill(6)  # zfill adds zeroes in front so we always have 6 digits
            # damn = product[7:11] + 'T' + utm_code + latitude_band + square + '_A' + abs_orbit_num + '_' + product[
            #                                                                                               11:26]
            # res_10m_path = granule_path / damn / 'IMG_DATA' / 'R10m/'
            # res_20m_path = granule_path / damn / 'IMG_DATA' / 'R20m/'
            # res_60m_path = granule_path / damn / 'IMG_DATA' / 'R60m/'
            product_type = ""
        elif row.platformname == 'Sentinel-3':
            product = row['title']
            instrument = row['instrumentshortname']
            product_type = row['producttype'][:-3]  # The [:-3] removes three underscores at the end
            product_path = (directory / 'output_data' / 's3' / instrument / product_type / product).with_suffix('.SEN3')
            tile_path = ""
        elif row.platformname == 'Sentinel-5 Precursor':
            producttype = row['producttypedescription']
            producttype_name_mapping = {'Ozone': 'O3',
                                        'Sulphur Dioxide': 'SO2',
                                        'Nitrogen Dioxide': 'NO2',
                                        'Methane': 'CH4',
                                        'Formaldehyde': 'HCHO',
                                        'Carbon Monoxide': 'CO',
                                        'Aerosol Index': 'AER_AI',
                                        'Aerosol Layer Height': 'AER_LH',
                                        'Cloud': 'CLOUD'}
            product_path = directory / 'output_data' / 's5p'
            product_type = producttype_name_mapping[producttype]
            tile_path = ""
        else:
            tile_path, product_path, product_type = "", "", ""

        return pd.Series([tile_path, product_path, product_type])

