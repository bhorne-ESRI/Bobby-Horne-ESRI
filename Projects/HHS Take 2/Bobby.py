from arcgis.gis import GIS
#source_portal_username = input("Enter username of source organization admin: ")
target=GIS(url="https://prof-services.maps.arcgis.com/home", username="bhorne_prof_services", password="78thbdv5")

#target_portal_username = input("Enter username of target organization admin: ")
source=GIS(url="https://ps-dbs.maps.arcgis.com/home", username="bhorne_ps_dbs", password="78tHbDv5")



item_ids = [
    #'', # instant app
    #'', # web map
    #'', # xlsx
    #'', # shapefile
    #'', # image
    #'', # pdf
    #'', # feature layer
    #'', # sd file
    #'', # site app
    #'', # story map
    '421c7ac24b6e4e6f9845277a5e5ced5e', # dashboard
    #'' # experience builder
]


# clone items
from arcgis.gis import User

items = []
for item_id in item_ids:
    try:
        item_detail = source.content.get(item_id)
        items.append(item_detail)
    except Exception as e:
        print(e)

print(str(len(items)) + " items will be cloned. See list below: ")
print(items)

def get_folder_name(gis, username, folder_id):
    user = User(gis, username)
    for folder in user.folders:
        if folder_id == folder['id']:
            return folder['title']
    print("Folder not found")
    return None

def deep_copy_content(item_list):
    for item in item_list:
        try:
            print("Cloning " + item.title)

            # get folder name
            folder = get_folder_name(source, item.owner, item.ownerFolder)

            # clone the item
            target.content.clone_items(items=[item], copy_data=True, search_existing_items=True, copy_global_ids=True, folder=folder, owner=item.owner)
            print("Successfully cloned " + item.title)
        except Exception as e:
            print(e)
    print("The function has completed")

deep_copy_content(items)