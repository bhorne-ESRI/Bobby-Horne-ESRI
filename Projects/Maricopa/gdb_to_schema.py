# -*- coding: utf-8 -*-
"""
Created on Wed May 26 09:23:10 2021

@author: Dave Crawford
"""

def fc_to_schema_df(fc):
    fields = arcpy.ListFields(fc)
    dicts = []
    for field in fields:
        dicts.append(
                {"NAME": field.name,
                 "ALIAS": field.aliasName,
                 "TYPE": field.type,
                 "LENGTH": field.length,
                 "PRECISION": field.precision,
                 "SCALE": field.scale,
                 "NULLABLE": field.isNullable,
                 "REQUIRED": field.required,
                 "DOMAIN": field.domain,
                 "DEFAULT": field.defaultValue
                        })
    return pandas.DataFrame(dicts)



def domains_to_df():
    domains = arcpy.da.ListDomains()
    dicts = []
    for domain in domains:
        if domain.domainType == 'CodedValue':
            for cv in domain.codedValues:
                dicts.append({
                        "DOMAIN_NAME": domain.name,
                        "DOMAIN_TYPE": "CODED",
                        "FIELD_TYPE": domain.type,
                        "DESCRIPTION": domain.codedValues[cv],
                        "CODE": cv})
        else:
            for rv in domain.range:
                dicts.append({
                        "DOMAIN_NAME": domain.name,
                        "DOMAIN_TYPE": "RANGE",
                        "FIELD_TYPE": domain.type,
                        "DESCRIPTION": rv
                        })
            pass
    return pandas.DataFrame(dicts)
        


import pandas
import arcpy

gdb = r"C:\Users\bob10704\OneDrive - Esri\Desktop\Projects\1.Active Projects\Maricopa County\Maricopa County\Default.gdb"
out_excel = r"C:\Users\bob10704\OneDrive - Esri\Desktop\Projects\1.Active Projects\Maricopa County\Data_Dictionary.xlsx"
#gdb = input('FGDB to document: ')
#out_excel = input('Path to excel document: ')


def gdb_to_excel(gdb, out_excel):
    
    # TODO - Add prefixes for feature classes / tables
    arcpy.env.workspace = gdb
    domains = domains_to_df()
    dfs = {"Domains": domains}
    for fc in arcpy.ListFeatureClasses() + arcpy.ListTables():
        dfs[fc] = fc_to_schema_df(fc)
        
    with pandas.ExcelWriter(out_excel) as xl:
        for df in dfs:
            dfs[df].to_excel(xl, df, index=False)
    
    
        

gdb_to_excel(gdb, out_excel)

