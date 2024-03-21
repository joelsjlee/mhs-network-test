import re, json, glob, csv, sys, os, warnings
import pandas as pd
import numpy as np
import itertools as iter
import networkx as nx
import xml.etree.ElementTree as ET
import seaborn as sns
import matplotlib.pyplot as plt
from networkx.algorithms import community
from networkx.readwrite import json_graph
from json import JSONEncoder
from operator import itemgetter
from collections import Counter
import argparse
import time
import requests

from scripts.Correspondence_XML_parser import *
from scripts.network_helper_utils import createGraphObject
from scripts.read_write_helper_utils import grabFiles, save, networkAddNames

def createDataframe(files):
    df = build_dataframe(files)

    # Lowercase values in source, target, and reference columns.
    df['source'] = df['source'].str.lower()
    df['target'] = df['target'].str.lower()
    df['references'] = df['references'].str.lower()

    # Split references into list objects.
    df['references'] = df['references'].str.split(r',|;')

    return df

def createAdjMatrix(df):
    # Explode list so that each list value becomes a row.
    refs = df.explode('references')

    # Create file-person matrix.
    refs = pd.crosstab(refs['file'], refs['references'])

    # Repeat with correspondence (source + target)
    source = pd.crosstab(df['file'], df['source'])
    target = pd.crosstab(df['file'], df['target'])

    # Sum values of sources to refs or create new column with sources' values.
    for col in source:
        if col in refs:
            refs[str(col)] = refs[str(col)] + source[str(col)]
        else:
            refs[str(col)] = source[str(col)]

    # Repeat for targets.
    for col in target:
        if col in refs:
            refs[str(col)] = refs[str(col)] + target[str(col)]
        else:
            refs[str(col)] = target[str(col)]

    # Convert entry-person matrix into an adjacency matrix of persons.
    refs = refs.T.dot(refs)

    # # Change diagonal values to zero. That is, a person cannot co-occur with themself.
    # np.fill_diagonal(refs.values, 0)

    # Create new 'source' column that corresponds to index (person).
    refs['source'] = refs.index

    # # Reshape dataframe to focus on source, target, and weight.
    # # Rename 'people' column name to 'target'.
    df_graph = pd.melt(refs, id_vars = ['source'], var_name = 'target', value_name = 'weight') \
        .rename(columns = {'references':'target'}) \
        .query('(source != target) & (weight > 3)') \
        .query('(source != "u") & (target != "u")')

    # Remove rows with empty source or target.
    df_graph['source'].replace('', np.nan, inplace=True)
    df_graph['target'].replace('', np.nan, inplace=True)
    df_graph.dropna(subset=['source', 'target'], inplace=True)

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