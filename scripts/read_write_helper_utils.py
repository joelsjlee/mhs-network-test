import os
import json
import requests

def grabFiles(folder, length):
    '''Takes in the folder for the XML docs and how many xml documents you would like to use.'''
    files = []
    # The way this folder is laid out may change because its different than the other authors.
    for dirpath, dirnames, filenames in os.walk(folder):
        for filename in [f for f in filenames if f.endswith(".xml")]:
            files.append(os.path.join(dirpath, filename))
    # I'm using list indices here as a stop gap to test on lower lists. You could also use a random sample for variety
    return files[:length]

def save(data, filename):
    '''Simple function just to save the json file to the data folder.'''
    with open(filename, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def networkAddNames(data):
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
            json_data = response.json()['data']
            if json_data:
                node['name'] = json_data[node['id']]['given_name'] + " " + json_data[node['id']]['family_name']
                # And we add the name API response to our json for safe keeping
                d[node['id']] = json_data[node['id']]
            # I was running into a case with sedgewick-theodoreI where there was no json response. I;m not sure if this is an error or not
            # But I just set the name to the id if I run into this case.
            else:
                node['name'] = node['id']
            # Write out to the json
    with open('data/idtoname.json', 'w') as f:
        json.dump(d, f)