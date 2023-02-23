# Name: app_dependencies.py
# Purpose: Takes in an item ID for an application used in your organization and provides a CSV output
#          with all of the app's dependencies, such as embedded apps, webmaps, and layers.
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


def check_item(app_data, layers_df, webmaps_df, apps_df):

    # Create DataFrame for Item Dependencies
    item_deps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    all_values = get_values_recurs(app_data)

    # Search through values for Item IDs and URLs
    for value in set(all_values):
        if str(value).isalnum() is True and len(str(value)) == 32:

            logger.info(f'APP JSON - ITEM ID FOUND - Verifying {value}')

            # Determine the Type of Item and Associated Dependencies
            item_id_deps = item_id_search(value, layers_df, webmaps_df, apps_df)

            item_deps_df = item_deps_df.append(item_id_deps, ignore_index=True, sort=False)

        elif str(value).startswith("http"):

            logger.info(f'APP JSON - URL FOUND - Verifying {value}')

            # Determine if URL is an App or Layer Dependency
            item_url_deps = check_url(value, layers_df, webmaps_df, apps_df)

            item_deps_df = item_deps_df.append(item_url_deps, ignore_index=True, sort=False)

    # Drop Duplicates from DataFrame
    item_deps_df = item_deps_df.drop_duplicates()

    return item_deps_df


def check_url(url, layers_df, webmaps_df, apps_df):

    # Create DataFrame for URL Dependencies
    url_deps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    # Parse URL for Item ID
    parsed = urlparse(url)

    # Web AppBuilder URLs
    if parsed.query[:3] == "id=":
        logger.info(f'Parsed URL Matches Web AppBuilder Scheme')
        url_id = parsed.query[3:]
    # Configurable Apps URLs
    elif parsed.query[:6] == "appid=":
        logger.info(f'Parsed URL Matches Configurable App Templates Scheme')
        url_id = parsed.query[6:]
    # Ops Dashboard URLs
    elif parsed.fragment[:1] == "/":
        logger.info(f'Parsed URL Matches Operations Dashboard Scheme')
        url_id = parsed.fragment[1:]
    else:
        logger.info(f'Parsed URL Does Not Match Any App URL Scheme')
        url_id = ''

    # Confirm the Item ID from the Parse; if Item ID is not Valid, Check for a REST URL Reference
    if url_id.isalnum() is True and len(url_id) == 32:
        for index, row in apps_df.iterrows():
            if row['ID'] == url_id:

                logger.info(f'ITEM ID FOUND IN URL - EMBEDDED WEBAPP: {row["Title"]}')

                # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                app_id_details = row.drop(labels=['Data'])
                app_details_dict = app_id_details.to_dict()
                app_details_df = pd.DataFrame(app_details_dict, index=[0])

                # Check the Selected App for Other Embedded Apps
                logger.info(f'Searching for dependencies in Embedded Webapp.......')
                recursive_apps = check_item(row['Data'], layers_df, webmaps_df, apps_df)

                # Add All Embedded Apps to Master DataFrame
                url_deps_df = url_deps_df.append([app_details_df, recursive_apps], ignore_index=True, sort=False)
    else:
        for index, row in layers_df.iterrows():
            if row['URL'] is not None and row['URL'] in url:

                logger.info(f'LAYER URL FOUND: {row["Title"]}')

                # Convert Series Object to Dictionary and back into a DataFrame
                layer_details_dict = row.to_dict()
                layer_details_df = pd.DataFrame(layer_details_dict, index=[0])

                url_deps_df = url_deps_df.append(layer_details_df, ignore_index=True, sort=False)

    return url_deps_df


def item_id_search(item_id, layers_df, webmaps_df, apps_df):

    # Create DataFrame for Item ID Dependencies
    item_id_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    if item_id in webmaps_df.values:
        for index, row in webmaps_df.iterrows():
            if row['ID'] == item_id:

                logger.info(f'ITEM ID FOUND - WEBMAP: {row["Title"]}')

                # Remove the JSON from Webmap Item and Convert Series Object to Dictionary and back into a DataFrame
                webmap_id_details = row.drop(labels=['Data'])
                webmap_details_dict = webmap_id_details.to_dict()
                webmap_deatils_df = pd.DataFrame(webmap_details_dict, index=[0])

                # Retrieve Layers in Selected Webmap
                dep_layers_df = check_maps_for_layers(row['Data'], layers_df)

                # Add All Item Dependencies to a Single DataFrame
                item_id_df = item_id_df.append([webmap_deatils_df, dep_layers_df], ignore_index=True, sort=False)

    elif item_id in layers_df.values:
        for index, row in layers_df.iterrows():
            if row['ID'] == item_id:

                logger.info(f'ITEM ID FOUND - LAYER: {row["Title"]}')

                # Convert Series Object to Dictionary and back into a DataFrame
                layer_details_dict = row.to_dict()
                layer_details_df = pd.DataFrame(layer_details_dict, index=[0])

                # Add Layer Item to DataFrame
                item_id_df = item_id_df.append(layer_details_df, ignore_index=True, sort=False)

    return item_id_df


def check_maps_for_layers(map_data, layers_df):

    # Create DataFrame for Layer Dependencies
    dep_layers_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    # Check all Layers in DataFrame against Webmap Operational Layers
    for index, row in layers_df.iterrows():

        try:
            # Search Through Values for References to Layer Item IDs or URLs
            if 'operationalLayers' in map_data.keys():
                for op in map_data['operationalLayers']:
                    if (row['ID'] == [op['itemId'] if 'itemId' in op.keys() else ''][0])\
                        or (row['URL'] is not None and row['URL'] in [op['url'] if 'url' in op.keys() else
                                                                      op['styleUrl'] if 'styleUrl' in op.keys() else
                                                                      ''][0]):

                        logger.info(f'LAYER ITEM FOUND IN WEBMAP - {row["Title"]}')

                        # Convert Series Object to Dictionary and back into a DataFrame
                        layer_details_dict = row.to_dict()
                        layer_details_df = pd.DataFrame(layer_details_dict, index=[0])

                        dep_layers_df = dep_layers_df.append(layer_details_df, ignore_index=True, sort=False)

        except Exception as e:
            logger.warning(str(e))
            logger.warning(f'Ran into a problem with JSON Data. Check webmap JSON for issues.')
            continue

    # Drop Duplicates from DataFrame
    dep_layers_df = dep_layers_df.drop_duplicates()

    return dep_layers_df


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
    max_portal_items = params['max_items']
    app_id = params['app_id']

    # Get GIS Object (comment/uncomment preferred login method)
    gis = GIS(base_url, username, password, verify_cert=False)
    logger.info('Generated GIS object')

    # Get App and App JSON
    logger.info(f'App ID Retrieved from Config File: {app_id}')
    app_item = gis.content.get(app_id)
    app_json = app_item.get_data()

    # Get List of Layers from Organization
    logger.info(f'Generating list of all layer items in organization....')
    layer_query = "!owner:esri_* ('type:\"Feature Collection\" OR type:\"Layer\" OR type:\"Feature Service\" OR type:\"Map Service\" OR type:\"Vector Tile Service\" OR type:\"Image Service\"')"
    layer_list = gis.content.search(query=layer_query, max_items=max_portal_items)

    # Create DataFrame from Layer Object
    org_layers_df = pd.DataFrame()
    for layer in layer_list:
        layer_details = {'Owner': layer.owner,
                         'Title': layer.title,
                         'Type': layer.type,
                         'ID': layer.id,
                         'URL': layer.url,
                         'Sharing': ''}
        org_layers_df = org_layers_df.append(layer_details, ignore_index=True)

    # Get List of Web Maps from Organization
    logger.info(f'Generating list of all webmap items in organization....')
    map_query = "!owner:esri_* (type:(\"Web Map\") -type:(\"Web Mapping Application\" OR \"Web Scene\"))"
    webmap_list = gis.content.search(query=map_query, max_items=max_portal_items)

    # Get DataFrame from Map Object
    org_webmaps_df = pd.DataFrame()
    for webmap in webmap_list:
        webmap_details = {'Owner': webmap.owner,
                          'Title': webmap.title,
                          'Type': webmap.type,
                          'ID': webmap.id,
                          'URL': webmap.homepage,
                          'Sharing': '',
                          'Data': webmap.get_data()}
        org_webmaps_df = org_webmaps_df.append(webmap_details, ignore_index=True)

    # Get List of Apps from Organization
    logger.info(f'Generating list of all app items in organization....')
    app_query = '!owner:esri_* (type:("Web Mapping Application" OR "Dashboard"))  -type:("Code Attachment" OR "Featured Items") -typekeywords:("MapAreaPackage") -type:("Map Area")'
    app_list = gis.content.search(query=app_query, max_items=max_portal_items)

    # Get DataFrame from App Object
    org_apps_df = pd.DataFrame()
    for app in app_list:
        app_details = {'Owner': app.owner,
                       'Title': app.title,
                       'Type': app.type,
                       'ID': app.id,
                       'URL': app.url if app.url is not None else app.homepage,
                       'Sharing': '',
                       'Data': app.get_data()}
        org_apps_df = org_apps_df.append(app_details, ignore_index=True)

    # Check for Item Dependencies in App Item
    logger.info(f'Checking {app_item.title} for item dependencies....')
    app_deps_df = check_item(app_json, org_layers_df, org_webmaps_df, org_apps_df)

    # Write Results to a CSV
    csv_file = os.path.join(log_dir, f'{app_id}_dependencies.csv')
    app_deps_df.to_csv(csv_file, index=False)
    logger.info(f'CSV File Generated - {csv_file}')

    # Log Execution Time
    logger.info(f'Program Run Time: {round(((time.time() - start_time) / 60), 2)} Minute(s)')

    # Close Logger Handlers
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)