# Name: org_layer_dependencies.py
# Purpose: Looks through all users' content in your organization for layers and provides a CSV
#          output with all of the layer's dependencies, such as webmaps and webapps, as well as
#          other information about the layer item itself.
# Author: Taylor Teske
# Last Modified: 5/29/2020
# Python Version:   3.6
# ArcGIS Python API Version: 1.7.1
# ---------------------------------------------

import json
import os
import logging
import time
import datetime
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


def check_apps_for_apps(webapp_df, app_object_df):

    logger.info(f'Checking dependent applications for embedded applications....')

    # Create DataFrame for App Dependencies
    embed_webapps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

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

    logger.info(f'Checking applications for dependent webmaps....')

    # Create DataFrame for App Dependencies
    dep_apps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

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
                        if row['ID'] == value:

                            logger.info(f'ITEM ID FOUND - WEBAPP: {app_item["Title"]}')

                            # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                            app_id_details = app_item.drop(labels=['Data'])
                            app_details_dict = app_id_details.to_dict()
                            app_details_df = pd.DataFrame(app_details_dict, index=[0])

                            dep_apps_df = dep_apps_df.append(app_details_df, ignore_index=True, sort=False)
            except Exception as e:
                logger.warning(str(e))
                logger.warning(f'Ran into a problem with {app_item["ID"]}. Check app JSON for issues.')
                continue

    # Drop Duplicates from DataFrame
    dep_apps_df = dep_apps_df.drop_duplicates()

    return dep_apps_df


def check_apps_for_layers(layer_item, app_object_df):

    logger.info(f'Checking applications for {layer_item["Title"]}....')

    # Create DataFrame for App Dependencies
    dep_apps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    # Check All Apps for Layer
    for index, app_item in app_object_df.iterrows():

        try:
            # Get All Values in JSON of App Item
            app_json = get_values_recurs(app_item['Data'])

            # Search Through Values for References to Item IDs or URLs
            for value in set(app_json):
                if str(value).isalnum() is True and len(str(value)) == 32:
                    if layer_item['ID'] == value:

                        logger.info(f'ITEM ID FOUND - WEBAPP: {app_item["Title"]}')

                        # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                        app_id_details = app_item.drop(labels=['Data'])
                        app_details_dict = app_id_details.to_dict()
                        app_details_df = pd.DataFrame(app_details_dict, index=[0])

                        dep_apps_df = dep_apps_df.append(app_details_df, ignore_index=True, sort=False)

                elif str(value).startswith("http"):
                    if layer_item['URL'] in value:

                        logger.info(f'URL FOUND - WEBAPP: {app_item["Title"]}')

                        # Remove the JSON from App Item and Convert Series Object to Dictionary and back into a DataFrame
                        app_id_details = app_item.drop(labels=['Data'])
                        app_details_dict = app_id_details.to_dict()
                        app_details_df = pd.DataFrame(app_details_dict, index=[0])

                        dep_apps_df = dep_apps_df.append(app_details_df, ignore_index=True, sort=False)
        except Exception as e:
            logger.warning(str(e))
            logger.warning(f'Ran into a problem with {app_item["ID"]}. Check app JSON for issues.')
            continue

    # Drop Duplicates from DataFrame
    dep_apps_df = dep_apps_df.drop_duplicates()

    return dep_apps_df


def check_maps_for_layers(layer_item, webmap_object_df, app_object_df):

    logger.info(f'Checking webmaps for {layer_item["Title"]}....')

    # Create DataFrame for Webmap Dependencies
    dep_webmaps_df = pd.DataFrame(columns=['Owner', 'Title', 'Type', 'ID', 'URL', 'Sharing'])

    # Check all Webmaps for Layer
    for index, map_item in webmap_object_df.iterrows():

        map_json = map_item['Data']

        try:
            # Search Through Values for References to Item IDs or URLs and Append Webmap to DataFrame
            if 'operationalLayers' in map_json.keys():
                for op in map_json['operationalLayers']:
                    if (layer_item['ID'] == [op['itemId'] if 'itemId' in op.keys() else ''][0])\
                        or (layer_item['URL'] is not None and layer_item['URL'] in [op['url'] if 'url' in op.keys() else
                                                                      op['styleUrl'] if 'styleUrl' in op.keys() else
                                                                      ''][0]):

                        logger.info(f'ITEM ID FOUND - WEBMAP: {map_item["Title"]}')

                        # Remove the JSON from Webmap Item and Convert Series Object to Dictionary and back into a DataFrame
                        webmap_id_details = map_item.drop(labels=['Data'])
                        webmap_details_dict = webmap_id_details.to_dict()
                        webmap_details_df = pd.DataFrame(webmap_details_dict, index=[0])

                        dep_webmaps_df = dep_webmaps_df.append(webmap_details_df, ignore_index=True, sort=False)

        except Exception as e:
            logger.warning(str(e))
            logger.warning(f'Ran into a problem with {map_item["ID"]}. Check webmap JSON for issues.')
            continue

    # Drop Duplicates from DataFrame
    dep_webmaps_df = dep_webmaps_df.drop_duplicates()

    # Check if Selected Webmaps are in Any Apps
    dep_map_apps_df = check_apps_for_webmaps(dep_webmaps_df, app_object_df)

    # Check if Layer Item is in Any Apps without a Webmap
    dep_layer_apps_df = check_apps_for_layers(layer_item, app_object_df)

    # Merge App DataFrames to Check Embedded Apps
    dep_apps_df = dep_layer_apps_df.append(dep_map_apps_df, ignore_index=True)
    dep_apps_df = dep_apps_df.drop_duplicates()

    # Check Dependent Apps in All Apps
    dep_embed_app_df = check_apps_for_apps(dep_apps_df, app_object_df)

    # Merge App Dependencies DataFrames
    dep_apps_df = dep_apps_df.append(dep_embed_app_df, ignore_index=True)
    dep_apps_df = dep_apps_df.drop_duplicates()

    return dep_webmaps_df, dep_apps_df


if __name__ == "__main__":

    # Get Script Directory
    this_dir = os.path.split(os.path.realpath(__file__))[0]

    # Get Logger
    start_time = time.time()
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

    # Get GIS Object (comment/uncomment preferred login method)
    gis = GIS(base_url, username, password, verify_cert=False)
    logger.info('Generated GIS object')

    # Get List of Hosted Feature Layers from Organization
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

    # Get JSON Data for List of Maps
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

    # Get JSON Data for List of Apps
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

    # Get All Layer Types for Each User and Add to a DataFrame
    item_deps_df = pd.DataFrame(columns=['Owner', 'Layer Title', 'Layer Type', 'Layer ID', 'Layer URL', 'Sharing', 'Web Maps', 'Web Apps'])

    for index, layer in org_layers_df.iterrows():

        logger.info(f'CHECKING FOR DEPENDENCIES - LAYER: {layer["Title"]}')

        webmap_df, app_df = check_maps_for_layers(layer, org_webmaps_df, org_apps_df)

        row_df = {'Owner': layer['Owner'],
                  'Layer Title': layer['Title'],
                  'Layer Type': layer['Type'],
                  'Layer ID': layer['ID'],
                  'Layer URL': layer['URL'],
                  'Sharing': layer['Sharing'],
                  'Web Maps': webmap_df.to_dict('records'),
                  'Web Apps': app_df.to_dict('records')}

        item_deps_df = item_deps_df.append(row_df, ignore_index=True, sort=False)

    # Write out Results to a CSV
    csv_file = os.path.join(log_dir, 'org_layers.csv')
    item_deps_df.to_csv(csv_file, index=False)
    logger.info(f'CSV File Generated - {csv_file}')

    # Log Execution Time
    logger.info(f'Program Run Time: {round(((time.time() - start_time) / 60), 2)} Minute(s)')

    # Close Logger Handlers
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)
