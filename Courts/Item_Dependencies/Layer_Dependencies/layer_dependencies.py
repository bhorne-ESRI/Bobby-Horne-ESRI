# Name: layer_dependencies.py
# Purpose: Takes in an item ID or URL for a layer used in your organization and provides a CSV output
#          with all of the layer's dependencies, such as webmaps and webapps.
# Author: Taylor Teske
# Last Modified: 5/29/2020
# Python Version:   3.6
# ArcGIS Python API Version: 1.7.1
# ---------------------------------------------

import json
import os
import datetime
import logging
import time
import pandas as pd
from arcgis.gis import GIS
from urllib.parse import urlparse


def get_logger(log_name, log_dir, run_name):

    the_logger = logging.getLogger(run_name)
    the_logger.setLevel(logging.DEBUG)

    # Ensure Directories Exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Set Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Set File Handler
    fh = logging.FileHandler(os.path.join(log_dir, log_name), 'a')
    fh.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    the_logger.addHandler(ch)
    the_logger.addHandler(fh)

    the_logger.info('Logger Initialized')

    return the_logger


def clean_logs(log_dir):

    if not os.path.exists(log_dir):
        return

    for f in os.listdir(log_dir):
        os.remove(os.path.join(log_dir, f))


def get_config(in_file):

    with open(in_file) as config:
        param_dict = json.load(config)

    return param_dict


def get_values_recurs(dict_):

    output = []

    if isinstance(dict_, dict):
        for value in dict_.values():
            if isinstance(value, dict):
                output += get_values_recurs(value)
            elif isinstance(value, list):
                for entry in value:
                    output += get_values_recurs({'_': entry})
            else:
                output += [value, ]
    return output


def check_layer_parameter(layer_item):

        # Check Whether the Layer Parameter is an Item ID or URL
        if str(layer_item).isalnum() is True and len(str(layer_item)) == 32:

            return layer_item

        elif layer_item.startswith('http'):

            layer_query = "!owner:esri_* ('type:\"Scene Service\" OR type:\"Feature Collection\" OR type:\"Layer\" OR type:\"Feature Service\" OR type:\"Map Service\" OR type:\"Vector Tile Service\" OR type:\"Image Service\"')"
            layer_list = gis.content.search(query=layer_query, max_items=10000)

            # Check if Layer is in the Organization
            for layer_object in layer_list:
                if str(layer_object.url) in layer_item:

                    logger.info(f'Item ID Found in Organization: {layer_object.id}')

                    return layer_object.id

            logger.info(f'{layer_item} Not Found in Organization')

            return layer_item


def check_apps_for_apps(webapp_df, app_object_df):

    # Create DataFrame for App Dependencies
    embed_webapps_df = pd.DataFrame(columns=['Owner', 'Title', 'ID', 'Type', 'URL', 'Sharing'])

    # Loop Through All Dependent Apps in DataFrame
    for index, row in webapp_df.iterrows():

        # Check All Apps for Embedded App
        for app_index, app_item in app_object_df.iterrows():

            try:
                # Get All Values in JSON of App Item
                app_json = get_values_recurs(app_item['Data'])

                # Search Through Values for References to Item IDs in App URLs
                for value in set(app_json):

                    if str(value).startswith("http"):

                        # Parse Webpage URL for item ID
                        parsed = urlparse(value)

                        # Web AppBuilder URLs
                        if parsed.query[:3] == "id=":
                            app_url_id = parsed.query[3:]
                        # Configurable Apps URLs
                        elif parsed.query[:6] == "appid=":
                            app_url_id = parsed.query[6:]
                        # Ops Dashboard URLs
                        elif parsed.fragment[:1] == "/":
                            app_url_id = parsed.fragment[1:]
                        else:
                            app_url_id = ''

                        if app_url_id.isalnum() is True and len(app_url_id) == 32:
                            if row["ID"] == app_url_id:

                                logger.info(f'ITEM ID FOUND - WEBAPP: {app_item["Title"]}')

                                # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                                app_id_details = app_item.drop(labels=['Data'])
                                app_details_dict = app_id_details.to_dict()
                                app_details_df = pd.DataFrame(app_details_dict, index=[0])

                                # Check the Selected App for Other Embedded Apps
                                recursive_apps = check_apps_for_apps(app_details_df, app_object_df)

                                # Add All Embedded Apps to Master DataFrame
                                embed_webapps_df = embed_webapps_df.append([app_details_df, recursive_apps], ignore_index=True, sort=False)
            except Exception as e:
                logger.warning(str(e))
                logger.warning(f'Ran into a problem with {app_item["ID"]}. Check app JSON for issues.')
                continue


    # Drop Duplicates from DataFrame
    embed_webapps_df = embed_webapps_df.drop_duplicates()

    return embed_webapps_df


def check_apps_for_webmaps(webmap_df, app_object_df):

    # Create DataFrame for App Dependencies
    webapps_df = pd.DataFrame(columns=['Owner', 'Title', 'ID', 'Type', 'URL', 'Sharing'])

    # Loop Through All Dependent Webmaps in DataFrame
    for index, row in webmap_df.iterrows():

        # Check All Apps for Webmap
        for app_index, app_item in app_object_df.iterrows():

            try:
                # Get All Values in JSON of App Item
                app_json = get_values_recurs(app_item['Data'])

                # Search Through Values for References to Item IDs
                for value in set(app_json):
                    if str(value).isalnum() is True and len(str(value)) == 32:
                        if row["ID"] == value:

                            logger.info(f'ITEM ID FOUND - WEBAPP: {app_item["Title"]}')

                            # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                            app_id_details = app_item.drop(labels=['Data'])
                            app_details_dict = app_id_details.to_dict()
                            app_details_df = pd.DataFrame(app_details_dict, index=[0])

                            webapps_df = webapps_df.append(app_details_df, ignore_index=True, sort=False)
            except Exception as e:
                logger.warning(str(e))
                logger.warning(f'Ran into a problem with {app_item["ID"]}. Check app JSON for issues.')
                continue

    # Drop Duplicates from DataFrame
    webapps_df = webapps_df.drop_duplicates()

    return webapps_df


def check_apps_for_layers(layer_item, app_object_df):

    # Create DataFrame for App Dependencies
    webapps_df = pd.DataFrame(columns=['Owner', 'Title', 'ID', 'Type', 'URL', 'Sharing'])

    # Check All Apps for Layer
    for index, app_item in app_object_df.iterrows():

        try:
            # Get All Values in JSON of App Item
            app_json = get_values_recurs(app_item['Data'])

            # Search Through Values for References to Item IDs or URLs
            for value in set(app_json):
                if str(value).isalnum() is True and len(str(value)) == 32:
                    if layer_item == value:

                        logger.info(f'ITEM ID FOUND - WEBAPP: {app_item["Title"]}')

                        # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                        app_id_details = app_item.drop(labels=['Data'])
                        app_details_dict = app_id_details.to_dict()
                        app_details_df = pd.DataFrame(app_details_dict, index=[0])

                        webapps_df = webapps_df.append(app_details_df, ignore_index=True, sort=False)

                elif str(value).startswith("http"):
                    if str(layer_item).isalnum() is True and len(str(layer_item)) == 32:

                        item_object = gis.content.get(layer_item)

                        if item_object.url in value:

                            logger.info(f'URL FOUND - WEBAPP: {app_item["Title"]}')

                            # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                            app_id_details = app_item.drop(labels=['Data'])
                            app_details_dict = app_id_details.to_dict()
                            app_details_df = pd.DataFrame(app_details_dict, index=[0])

                            webapps_df = webapps_df.append(app_details_df, ignore_index=True, sort=False)

                    elif layer_item in value:

                        logger.info(f'URL FOUND - WEBAPP: {app_item["Title"]}')

                        # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                        app_id_details = app_item.drop(labels=['Data'])
                        app_details_dict = app_id_details.to_dict()
                        app_details_df = pd.DataFrame(app_details_dict, index=[0])

                        webapps_df = webapps_df.append(app_details_df, ignore_index=True, sort=False)

        except Exception as e:
            logger.warning(str(e))
            logger.warning(f'Ran into a problem with {app_item["ID"]}. Check app JSON for issues.')
            continue

    # Drop Duplicates from DataFrame
    webapps_df = webapps_df.drop_duplicates()

    return webapps_df


def check_maps_for_layers(layer_item, webmap_object_df):

    # Create DataFrame for Webmap Dependencies
    webmaps_df = pd.DataFrame(columns=['Owner', 'Title', 'ID', 'Type', 'URL', 'Sharing'])

    # Check all Webmaps for Layer
    for index, map_item in webmap_object_df.iterrows():

        map_json = map_item['Data']

        try:
            # Search Through Values for References to Item IDs or URLs and Append Webmap to DataFrame
            if 'operationalLayers' in map_json.keys():
                for op in map_json['operationalLayers']:
                    if layer_item == [op['itemId'] if 'itemId' in op.keys() else ''][0]:

                        logger.info(f'ITEM ID FOUND - WEBMAP: {map_item["Title"]}')

                        # Remove the JSON from Webmap Item and Convert Series Object to Dictionary and back into a DataFrame
                        webmap_id_details = map_item.drop(labels=['Data'])
                        webmap_details_dict = webmap_id_details.to_dict()
                        webmap_deatils_df = pd.DataFrame(webmap_details_dict, index=[0])

                        webmaps_df = webmaps_df.append(webmap_deatils_df, ignore_index=True, sort=False)

                    elif str(layer_item).isalnum() is True and len(str(layer_item)) == 32:

                        item_object = gis.content.get(layer_item)

                        if item_object.url in [op['url'] if 'url' in op.keys() else op[
                        'styleUrl'] if 'styleUrl' in op.keys() else ''][0]:

                            logger.info(f'URL FOUND - WEBMAP: {map_item["Title"]}')

                            # Remove the JSON from Webmap Item and Convert Series Object to Dictionary and back into a DataFrame
                            webmap_id_details = map_item.drop(labels=['Data'])
                            webmap_details_dict = webmap_id_details.to_dict()
                            webmap_deatils_df = pd.DataFrame(webmap_details_dict, index=[0])

                            webmaps_df = webmaps_df.append(webmap_deatils_df, ignore_index=True, sort=False)

                    elif layer_item in [op['url'] if 'url' in op.keys() else op[
                        'styleUrl'] if 'styleUrl' in op.keys() else ''][0]:

                        logger.info(f'URL FOUND - WEBMAP: {map_item["Title"]}')

                        # Remove the JSON from Webmap Item and Convert Series Object to Dictionary and back into a DataFrame
                        webmap_id_details = map_item.drop(labels=['Data'])
                        webmap_details_dict = webmap_id_details.to_dict()
                        webmap_deatils_df = pd.DataFrame(webmap_details_dict, index=[0])

                        webmaps_df = webmaps_df.append(webmap_deatils_df, ignore_index=True, sort=False)

        except Exception as e:
            logger.warning(str(e))
            logger.warning(f'Ran into a problem with {map_item["ID"]}. Check webmap JSON for issues.')
            continue

    # Drop Duplicates from DataFrame
    webmaps_df = webmaps_df.drop_duplicates()

    return webmaps_df


if __name__ == "__main__":

    # Get Start Time
    start_time = time.time()

    # Get Script Directory
    this_dir = os.path.split(os.path.realpath(__file__))[0]

    # Get Logger
    t_format = datetime.datetime.fromtimestamp(start_time).strftime('%d_%m_%H_%M_%S')
    log_name = f'LOG_{t_format}.log'
    log_dir = os.path.join(this_dir, 'logs')
    clean_logs(log_dir)
    logger = get_logger(log_name, log_dir, 'LOGGER')

    # Configuration File
    config_file = os.path.join(this_dir, 'config.json')

    # Get Configuration Parameters
    params = get_config(config_file)
    base_url = params['portal_url']
    username = params['username']
    password = params['password']
    portal_max_items = params['max_items']
    layer_id_or_url = params['layer_id_or_url']

    # Get GIS Object (comment/uncomment preferred login method)
    gis = GIS(base_url, username, password, verify_cert=False)
    logger.info('Generated GIS object')

    # Get Layer
    logger.info(f'Retrieved from Config File: {layer_id_or_url}')
    logger.info(f'Checking if {layer_id_or_url} is an item in the organization....')
    layer = check_layer_parameter(layer_id_or_url)

    # Get List of Web Maps from Organization
    logger.info(f'Generating list of all webmap items in organization....')
    map_query = "!owner:esri_* (type:(\"Web Map\") -type:(\"Web Mapping Application\" OR \"Web Scene\"))"
    webmap_list = gis.content.search(query=map_query, max_items=portal_max_items)

    # Get JSON Data for List of Maps
    webmap_json_df = pd.DataFrame()
    for webmap in webmap_list:
        webmap_details = {'Owner': webmap.owner,
                          'Title': webmap.title,
                          'ID': webmap.id,
                          'Type': webmap.type,
                          'URL': webmap.homepage,
                          'Sharing': '',
                          'Data': webmap.get_data()}
        webmap_json_df = webmap_json_df.append(webmap_details, ignore_index=True)

    # Get List of Apps from Organization
    logger.info(f'Generating list of all app items in organization....')
    app_query = '!owner:esri_* (type:("Web Mapping Application" OR "Dashboard"))  -type:("Code Attachment" OR "Featured Items") -typekeywords:("MapAreaPackage") -type:("Map Area")'
    app_list = gis.content.search(query=app_query, max_items=portal_max_items)

    # Get JSON Data for List of Apps
    app_json_df = pd.DataFrame()
    for app in app_list:
        app_details = {'Owner': app.owner,
                       'Title': app.title,
                       'ID': app.id,
                       'Type': app.type,
                       'URL': app.url if app.url is not None else app.homepage,
                       'Sharing': '',
                       'Data': app.get_data()}
        app_json_df = app_json_df.append(app_details, ignore_index=True)

    # Check All Webmaps for Selected Layer
    logger.info(f'Checking webmaps for {layer}....')
    webmap_dependencies_df = check_maps_for_layers(layer, webmap_json_df)

    # Check All Apps for Selected Layer Referenced without a Webmap
    logger.info(f'Checking applications for {layer}....')
    webapp_layer_dependencies_df = check_apps_for_layers(layer, app_json_df)

    # Check Dependent Webmaps in All Apps
    logger.info(f'Checking applications for dependent webmaps....')
    webapp_map_dependencies_df = check_apps_for_webmaps(webmap_dependencies_df, app_json_df)

    # Merge App DataFrames and Drop Duplicate Records
    webapp_dependencies_df = webapp_layer_dependencies_df.append(webapp_map_dependencies_df, ignore_index=True, sort=False)
    webapp_dependencies_df = webapp_dependencies_df.drop_duplicates()

    # Check Dependent Apps in All Apps
    logger.info(f'Checking dependent applications for embedded applications....')
    embed_webapp_dependencies_df = check_apps_for_apps(webapp_dependencies_df, app_json_df)

    # Merge All DataFrames and Drop Duplicates
    layer_dependencies_df = webapp_dependencies_df.append(embed_webapp_dependencies_df, ignore_index=True, sort=False)
    layer_dependencies_df = layer_dependencies_df.append(webmap_dependencies_df, ignore_index=True, sort=False)
    layer_dependencies_df = layer_dependencies_df.drop_duplicates()

    # Write Results to a CSV
    csv_file = os.path.join(log_dir, 'layer_dependencies.csv')
    layer_dependencies_df.to_csv(csv_file, index=False)
    logger.info(f'CSV File Generated - {csv_file}')

    # Log Execution Time
    logger.info(f'Program Run Time: {round(((time.time() - start_time) / 60), 2)} Minute(s)')

    # Close Logger Handlers
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)