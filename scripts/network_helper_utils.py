import networkx as nx
import pandas as pd
from operator import itemgetter
from networkx.algorithms import community
from networkx.readwrite import json_graph


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