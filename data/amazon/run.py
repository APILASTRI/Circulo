import os
import urllib.request
import igraph as ig
import gzip
import pickle
import shutil
import sys
from circulo.download_utils import download_with_notes, _unzip

## First pass at downloading SNAP data.
# 1. SNAP uses gzip for compression
# 2. There are overlapping communities, but graphml attributes cannot be lists so stored as string
# 3. Uses pickle file instead to store graph object (keeping groundtruth as list)
# 4. igraph wants to keep vertex ids sequential but SNAP data is not, so some empty nodes are created
# 5. after deleting these isolate nodes, the ids are remapped to remain sequetial, so have to also remap ground truth

DOWNLOAD_URL = 'http://snap.stanford.edu/data/bigdata/communities/com-amazon.ungraph.txt.gz'
DATA_ZIP_NAME = 'amazon.txt.gz'
DATA_NAME = 'amazon.txt'
GRAPH_NAME = 'amazon.graphml'

DOWNLOAD_URL_GROUNDTRUTH = 'http://snap.stanford.edu/data/bigdata/communities/com-amazon.all.cmty.txt.gz'
GROUNDTRUTH_ZIP_NAME = 'amazon-cmty.txt.gz'
GROUNDTRUTH_NAME = 'amazon-cmty.txt'

PICKLE_NAME = 'amazon-graph.pickle'

def _download(data_dir):
    '''
    downloads graph from SNAP website
    '''
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

    #download the graph as an edgelist
    download_with_notes(DOWNLOAD_URL, DATA_ZIP_NAME, data_dir)

    #download ground truth
    download_with_notes(DOWNLOAD_URL_GROUNDTRUTH, GROUNDTRUTH_ZIP_NAME, data_dir)

def _prepare(data_dir):

    data_path_old = os.path.join(data_dir, DATA_NAME + ".old")
    data_path = os.path.join(data_dir, DATA_NAME)

    #remove non edge data from edgelist
    shutil.move(data_path, data_path_old)

    with open(data_path_old, "r") as f:
        with open(data_path, "w") as out:
            for line in f:
                if(line.startswith('#') == False):
                    out.write(line)

    datapath = os.path.join(data_dir,DATA_NAME)
    groundtruthpath = os.path.join(data_dir,GROUNDTRUTH_NAME)
    graphpath = os.path.join(data_dir,GRAPH_NAME)
    picklepath = os.path.join(data_dir,PICKLE_NAME)

    print('Creating graphml file')
    # Read in Edgelist. Note that igraph creates extra nodes
    # with no edges for ids missing in sequential order
    # from the graph. We will delete these isolates later
    g = ig.Graph.Read_Edgelist(datapath,directed=False)

    # Assign communities as node attributes
    import csv
    with open(groundtruthpath,'r') as gtp:
            csvreader = csv.reader(gtp,delimiter='\t')
            # note that converting to graphml, attributes cannot be lists
            # only boolean,int,long,float,double,or string
            #
            # storing groundtruth communities as both arrays and strings
            # so that graphml file can retain attribute
            g.vs.set_attribute_values('groundtruth',[[]])
            g.vs.set_attribute_values('groundtruth_str',[''])

            count = 0
            for line in csvreader:
                for v in line:
                    v = int(v)
                    if g.vs[v]['groundtruth']:
                            g.vs[v]['groundtruth'] += [count]
                            g.vs[v]['groundtruth_str'] += ',' + str(count)
                    else:
                        g.vs[v]['groundtruth'] = [count]
                        g.vs[v]['groundtruth_str'] = str(count)
                count += 1
                max_clusters = count

    # remove isolates - this changes node ids!
    g.delete_vertices(g.vs.select(_degree=0))

    # Write out graphml file
    g.write_graphml(graphpath)

    # Write out groundTruth VertexCover as pickle
    print('Saving graph pickle')
    clusters = [[] for i in range(max_clusters)]
    for v in g.vs:
        for c in v['groundtruth']:
            clusters[c].append(v.index) #have to re-do this since id's were likely changed by removing isolates
    groundtruth_vc = ig.VertexCover(g,clusters)

    # save groundtruth cover as class variable
    setattr(g,'groundtruth',groundtruth_vc)
    with open(picklepath,'wb') as savefile:
        pickle.dump(g,savefile)

def get_graph():
    data_dir = os.path.join(os.path.dirname(__file__),'data')
    pickle_path = os.path.join(data_dir,PICKLE_NAME)

    #make sure the serialized graph exists
    if not os.path.isfile(pickle_path):
        _download(data_dir)
        _prepare(data_dir)
    else:
        print(pickle_path,'already exists. Using old file')

    with open(pickle_path,'rb') as loadfile:
        return pickle.load(loadfile)

def get_ground_truth(G=None):

    if G is None:
        G = get_graph()

    return G.groundtruth

def main():
    g = get_graph()

if __name__ == '__main__':
    main()