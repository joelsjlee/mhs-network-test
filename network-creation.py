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
# Python files (.py) have to be in same folder to work.
lib_path = os.path.abspath(os.path.dirname('scripts/JQA_XML_parser.py'))
sys.path.append(lib_path)
from JQA_XML_parser import *

def grabFiles(folder, length):
    '''Takes in the folder for the XML docs and how many xml documents you would like to use.'''
    files = []
    # The way this folder is laid out may change because its different than the other authors.
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in [f for f in filenames if f.endswith(".xml")]:
            files.append(os.path.join(dirpath, filename))
    # I'm using list indices here as a stop gap to test on lower lists. You could also use a random sample for variety
    return files[:length]

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
    # communities = community.naive_greedy_modularity_communities(subgraph)
    # communities = community.k_clique_communities(subgraph, 5)
    communities = community.greedy_modularity_communities(subgraph)
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
    '''
    This function loads the idtoname.json file, which is a dictionary used to store and track the relationship between
    the ids and the names of the people. Load the file, and check if the current nodes are tracked in the json file, and if
    not, we call the PSC names database API to fill in the names and add it to the json.
    '''
    # Open idtoname json and load it.
    with open('data/idtoname.json') as f:
        d = json.load(f)
    # Iterate over all of the nodes
    for node in data['nodes']:
        # If the node already exists in our json, then we can just add the name to the node
        # This can be edited if we want additional information from the PSC API in the node 
        if node['id'] in d:
            node['name'] = (d[node['id']]['given_name'] + " " + d[node['id']]['family_name'])
        else:
            # Otherwise, we make a requests call to the PSC database API to grab the names information
            request_url = "https://primarysourcecoop.org/mhs-api/ext/names?huscs={}".format(node['id'])
            try:
                response = requests.get(request_url)
            except requests.exceptions.RequestException as e:  # This is the correct syntax
                raise SystemExit(e)
            # Now we similar add the name to the node
            node['name'] = response.json()['data'][node['id']]['given_name'] + " " + response.json()['data'][node['id']]['family_name']
            # And we add the name API response to our json for safe keeping
            d[node['id']] = response.json()['data'][node['id']]
            # Write out to the json
            with open('data/idtoname.json', 'w') as f:
                json.dump(d, f)

def save(data, filename):
    '''Simple function just to save the json file to the data folder.'''
    with open(filename, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
    addNames(data)
    print('Saving data as json')
    save(data, args.filename)

if __name__ == "__main__":
    main()

