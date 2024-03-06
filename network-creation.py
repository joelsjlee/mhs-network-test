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
import requests
import argparse
# Import project-specific functions. 
# Python files (.py) have to be in same folder to work.
lib_path = os.path.abspath(os.path.dirname('scripts/JQA_XML_parser.py'))
sys.path.append(lib_path)
from JQA_XML_parser import *

def grabFiles(folder, length):
    files = []
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in [f for f in filenames if f.endswith(".xml")]:
            files.append(os.path.join(dirpath, filename))
    return files[:length]

def createDataframe(files):
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

def createGraphObject(df_graph):
    # Initialize graph object.
    G = nx.from_pandas_edgelist(df_graph, 'source', 'target', 'weight')

    # Add nodes.
    nodes = list( dict.fromkeys( df_graph['source'].values.tolist() + df_graph['target'].values.tolist() ))
    nodes = pd.DataFrame(nodes, columns = ['source'])
    G.add_nodes_from(nodes)

    print (G)

    # Set degree attributes.
    nx.set_node_attributes(G, dict(G.degree(G.nodes())), 'degree')

    # Sort nodes by degree and print top results.
    sorted_degree = sorted(dict(G.degree(G.nodes())).items(),
                        key = itemgetter(1), reverse = True)

    print ("Top 10 nodes by degree:")
    for d in sorted_degree[:10]:
        print (f'\t{d}')

    # Measure network density.
    density = nx.density(G)
    print (f"Network density: {density:.3f}")

    # Related to diameter, check if network is connected and, therefore, can have a diameter.
    print (f"Is the network connected? {nx.is_connected(G)}")

    # Find triadic closure (similar to density).
    triadic_closure = nx.transitivity(G)
    print (f"Triadic closure: {triadic_closure:.3f}\n")


    # Get a list of network components (communities).
    # Find the largest component.
    components = nx.connected_components(G)
    largest_component = max(components, key = len)

    # Create a subgraph of the largest component and measure its diameter.
    subgraph = G.subgraph(largest_component)
    diameter = nx.diameter(subgraph)
    print (f"Network diameter of the largest component: {diameter:.3f}")

    # Find centrality measures. 
    betweenness_dict = nx.betweenness_centrality(subgraph) # Run betweenness centrality
    eigenvector_dict = nx.eigenvector_centrality(subgraph) # Run eigenvector centrality
    degree_cent_dict = nx.degree_centrality(subgraph)

    # Assign each centrality measure to an attribute.
    nx.set_node_attributes(subgraph, betweenness_dict, 'betweenness')
    nx.set_node_attributes(subgraph, eigenvector_dict, 'eigenvector')
    nx.set_node_attributes(subgraph, degree_cent_dict, 'degree_cent')

    # Find communities. naive_greedy_modularity_communities
    communities = community.naive_greedy_modularity_communities(subgraph)
    # communities = community.k_clique_communities(subgraph, 5)
    # communities = community.greedy_modularity_communities(subgraph)
    # communities = community.kernighan_lin_bisection(subgraph)

    # Create a dictionary that maps nodes to their community.
    modularity_dict = {}
    for i, c in enumerate(communities):
        for name in c:
            modularity_dict[name] = i
            
    # Add modularity information to graph object.
    nx.set_node_attributes(subgraph, modularity_dict, 'modularity')
    data = json_graph.node_link_data(subgraph)
    return data

def addNames(data):
    with open('data/idtoname.json') as f:
        d = json.load(f)
    for node in data['nodes']:
        if node['id'] in d:
            node['name'] = (d[node['id']]['given_name'] + " " + d[node['id']]['family_name'])
        else:
            request_url = "https://primarysourcecoop.org/mhs-api/ext/names?huscs={}".format(node['id'])
            response = requests.get(request_url)
            node['name'] = response.json()['data'][node['id']]['given_name'] + " " + response.json()['data'][node['id']]['family_name']
            d[node['id']] = response.json()['data'][node['id']]
            with open('data/idtoname.json', 'w') as f:
                json.dump(d, f)

def save(data):
    with open("data/jqa_coRef-network.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Create Network Graph')
    parser.add_argument(
        'folder',
        help='The folder of MHS XML Files')
    parser.add_argument(
        'length',
        type=int,
        help='How many of the XML files you want to process.')
    args = parser.parse_args()

    print('Grabbing files')
    print(type(args.length))
    files = grabFiles(args.folder, args.length)
    print('Creating Dataframe')
    df = createDataframe(files)
    print('Creating Adjancency Matrix')
    df_graph = createAdjMatrix(df)
    print('Creating Graph Object')
    data = createGraphObject(df_graph)
    print('Adding Names from MHS PSC API')
    addNames(data)
    print('Saving data as json')
    save(data)

if __name__ == "__main__":
    main()

