# MHS Network Test
This repository is to test a small portion of Bill Quinn's MHS PSC work. The idea is to create a small workflow where data is taken in XML form, transformed with Bill Quinn's scripts, and displayed with his d3.js code.

To keep this example as small as possible, we decided just to look at the JQA papers and the network visualization. To do this, we first need to transform the .ipynb that Bill Quinn experimented with, into a .py script, this is the `network-creation.py` file. This 
file also calls upon the `JQA_XML_parser.py` file in the scripts folder. It takes the XML files in the JQA-XML folder and transforms them to a flat json file of data for nodes and edges (This is the `jqa-coRef-network.json` file).

To run the script, you can run `python3 network-creation.py JQA-XML {length}` where the length is how many documents you want to process (a simple python indices is called). For example, running `python3 network-creation.py JQA-XML 100` takes around 30 seconds to run.
Whereas, running it on all of the files currently I'm not sure how long it would take (I tried running it overnight and it still was not done).

Then, the `index.html` file and the `network-coRef.js` files work together to produce the visualization, along with the styles folder.

One thing I have added is that the `network-creation.py` file also calls upon the PSC names database. This is to pass along the names of the individuals, as well as some other helpful information if needed. This is the one notable change I've
made to the python javascript, the other one being that I also link a node click to go to the requisite PSC name link (although this is not fully fleshed out on the PSC side). To help with the names, I also have a idtonames json file that keeps 
a record of the called API names so that multiple API calls to the same id is not needed.

In total, this should run very similarly to Bill Quinn's original notebook and visualizations goals, whereby you run all the cells, the output gets posted in a different directory where the visualization and index file can access it. In this
case, I've transformed the notebook into a .py script to avoid the manual running of cells, and put them in the same directory as the visualization tools, so when the script is run, you can start up a server (like with `python3 -m http.server`) and see
the visualization.

The idea hopefully is to continue to integrate more of Bill Quinn's notebooks into formats like this, to be run as python scripts and then transferred as json data to be visualized.
