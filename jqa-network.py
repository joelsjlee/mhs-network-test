import json, sys, os, warnings
import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms import community
from networkx.readwrite import json_graph
from operator import itemgetter
import requests
import argparse
import time
# Import project-specific functions. 

from scripts.JQA_XML_parser import *
from scripts.network_helper_utils import createGraphObject
from scripts.read_write_helper_utils import grabFiles, save, networkAddNames

def createDataframe(files):
    '''Builds dataframe from the files list.'''
    # Build dataframe from XML files.
    # build_dataframe() called from Correspondence_XML_parser
    df = build_dataframe(files)

    # Unnest subject headings. 
    df['people'] = df['people'].str.split(r',|;')
    df = df.explode('people')

    # Remove leading and trailing whitespace.
    df['people'] = df['people'].str.strip()

    # Remove rows with empty values.
    df.replace('', np.nan, inplace = True)
    df.dropna(inplace = True)
    return df

def createAdjMatrix(df):
    # Filter dates by distribution.
    df = df.query('(people != "u") & (people != "source")') 
        #.query('(date < "1800-01-01") | (date >= "1830-01-01")')

    # Create adjacency matrix.
    adj = pd.crosstab(df['entry'], df['people'])

    # Convert entry-person matrix into an adjacency matrix of persons.
    adj = adj.T.dot(adj)

    # Change same-same connections to zero.
    np.fill_diagonal(adj.values, 0)

    # # Simple correlation matrix from dataframe.
    # adj = adj.corr()

    adj['source'] = adj.index

    df_graph = pd.melt(adj, id_vars = 'source', var_name = 'target', value_name = 'weight') \
        .query('(source != target) & (weight > 15)') # 20 is good
    
    return df_graph

def main():
    '''Main argument to parse the args and call all of the requisite functions. Once this runs, you can start a server and check out the index.html file.'''
    parser = argparse.ArgumentParser(description='Create Network Graph')
    parser.add_argument(
        'folder',
        help='The folder of MHS XML Files')
    parser.add_argument(
        'length',
        type=int,
        help='How many of the XML files you want to process.')
    parser.add_argument(
        'filename',
        help='The output json filename')
    args = parser.parse_args()

    print('Grabbing files')
    files = grabFiles(args.folder, args.length)
    print('Creating Dataframe')
    df = createDataframe(files)
    print('Creating Adjacency Matrix')
    df_graph = createAdjMatrix(df)
    print('Creating Graph Object')
    start_time = time.time()
    data = createGraphObject(df_graph)
    print("Creating Graph Object time:", time.time() - start_time, "seconds.")
    print('Adding Names from MHS PSC API')
    networkAddNames(data)
    print('Saving data as json')
    save(data, args.filename)

if __name__ == "__main__":
    main()

