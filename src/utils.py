#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import pandas as pd
from scipy.spatial import distance
from statistics import mean, stdev
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from skimage.external import tifffile
import xml.etree.cElementTree as et


################################################
# Some helper functions
################################################
def normalize(vector):
    # unpack
    x, y, z = vector
    # calculate length
    length = (x**2 + y**2 + z**2)**0.5
    # divide by length
    if length == 0:
        return (0,0,0)
    return (x/length, y/length, z/length)

def findCong(time, dist, max_dist):
    """
    Counts the number of continuous time points in which the two 
        tracks are under max_dist microns away
    - the time argument is a list of time points in which the two tracks are both present
    
    - the dist argument is the list of corresponding distances
    
    - the max_dist argument is a distance threshold (float or int)
    """
    t_cong = 0
    t_prev = time[0]-1
    all_periods = []
    for t, d in zip(time, dist):
        if t_prev + 1 != t: # not continuous
            if t_cong != 0:
                all_periods.append(t_cong)
            t_cong = 0
        if (d < max_dist):
            t_cong += 1
        t_prev = t 
    all_periods.append(t_cong)
    return max(all_periods)

################################################
# XML parsing related
################################################

def parseSpots(trackmate_xml_path):
    '''
    trackmate_xml_path : str
    parses the spots info from trackmate xml
    code adaptd from: https://github.com/hadim/pytrackmate
    '''
    root = et.fromstring(open(trackmate_xml_path).read())
    objects = []
    features = root.find('Model').find('FeatureDeclarations').find('SpotFeatures')
    features = [c.get('feature') for c in features.getchildren()] + ['ID'] + ['name']

    spots = root.find('Model').find('AllSpots')
    objects = []
    for frame in spots.findall('SpotsInFrame'):
        for spot in frame.findall('Spot'):
            single_object = []
            for label in features:
                single_object.append(spot.get(label))
            objects.append(single_object)

    spots_df = pd.DataFrame(objects, columns=features)

    return spots_df


def parseTracks(trackmate_xml_path):
    '''
    trackmate_xml_path : str
    
    this function complements pytrackmate module by parsing the tracks info 
        from trackmate xml file
        
    returns:
        df: a pandas dataframe containing general information per track, 
        df2: a pandas dataframe containing specific info per edge

    reference: 
        https://imagej.net/TrackMate
    '''
    
    tree = et.parse(trackmate_xml_path)
    root = tree.getroot()
    objects = []
    df = pd.DataFrame([])
    df2 = pd.DataFrame([])
    features = root.find('Model').find('FeatureDeclarations').find('TrackFeatures')
    features = [c.get('feature') for c in features.getchildren()]
    features.append('name')
    tracks = root.find('Model').find('AllTracks')
    objects = []
    edges = []
    
    for track in tracks.findall('Track'):
        single_object = []
        track_id = int(track.get("TRACK_ID"))
        for edge in track.findall('Edge'):
            edge_object = [track_id,
                    edge.get('SPOT_SOURCE_ID'), 
                     edge.get('SPOT_TARGET_ID'), 
                     edge.get('LINK_COST'),
                     edge.get('EDGE_TIME'),
                     edge.get('EDGE_X_LOCATION'),
                     edge.get('EDGE_Y_LOCATION'),
                     edge.get('EDGE_Z_LOCATION'),
                     edge.get('VELOCITY'),
                     edge.get('DISPLACEMENT')]
            
            edges.append(edge_object)               
        
        for label in features:
            single_object.append(track.get(label))
        objects.append(single_object)
      
        
    df = pd.DataFrame(objects, columns = features)
    #df = df.astype(np.float)
    df2 = pd.DataFrame(edges, columns = [
                    'TRACK_ID',
                    'SPOT_SOURCE_ID',
                    'SPOT_TARGET_ID',
                    'LINK_COST',
                    'EDGE_TIME',
                    'EDGE_X_LOCATION',
                    'EDGE_Y_LOCATION',
                    'EDGE_Z_LOCATION',
                    'VELOCITY',
                    'DISPLACEMENT'])
    df2 = df2.astype(np.float)
    
    return df, df2

def parseDim(trackmate_xml_path):
    f=open(trackmate_xml_path)
    ln=f.readline().split()
    while ln[0] != 'Geometry:':
        ln=f.readline().split()
    ln=f.readline().split()
    X = int(ln[4][:-1])
    ln=f.readline().split()
    Y = int(ln[4][:-1])
    ln=f.readline().split()
    Z = int(ln[4][:-1])
    ln=f.readline().split()
    T = int(ln[4][:-1]) 
    f.close()
    return (X,Y,Z,T)



################################################
# Registration related
################################################


def findCroppedDim(tiff_path):
    with tifffile.TiffFile(tiff_path) as tif:
        # read tiff
        im_in = tif.asarray()
        if len(im_in.shape) == 4:
            n_frame, n_zstep, y_dim, x_dim = im_in.shape
        else:
            n_frame, n_zstep, n_channel, y_dim, x_dim = im_in.shape
        top = 0
        bottom = y_dim
        left = 0
        right = x_dim
        if len(im_in.shape) == 4:
            for t in range(n_frame):
                if not np.any(im_in[t][0]): # check if empty frame
                    continue
                # top border
                y = 0
                while im_in[t][0][y][int(x_dim/2)] == 0:
                    y+=1
                if top < y:
                    top = y
                # bottom border
                y = y_dim - 1
                while im_in[t][0][y][int(x_dim/2)] == 0:
                    y-=1
                if bottom > y:
                    bottom = y
                # left border
                x = 0
                while im_in[t][0][int(y_dim/2)][x] == 0:
                    x+=1
                if left < x:
                    left = x
                # right border
                x = x_dim - 1
                while im_in[t][0][int(y_dim/2)][x] == 0:
                    x-=1
                if right > x:
                    right = x
        else:
            for t in range(n_frame):
                if not np.any(im_in[t][0]): # check if empty frame
                    continue
                # top border
                y = 0
                while im_in[t][0][0][y][int(x_dim/2)] == 0:
                    y+=1
                if top < y:
                    top = y
                # bottom border
                y = y_dim - 1
                while im_in[t][0][0][y][int(x_dim/2)] == 0:
                    y-=1
                if bottom > y:
                    bottom = y
                
                # left border
                x = 0
                while im_in[t][0][0][int(y_dim/2)][x] == 0:
                    x+=1
                if left < x:
                    left = x
                # right border
                x = x_dim - 1
                while im_in[t][0][0][int(y_dim/2)][x] == 0:
                    x-=1
                if right > x:
                    right = x
    return top, bottom, left, right

def combine(csv_path,n_csv = 2):
    mat = pd.read_csv(csv_path+"1.csv", index_col=0, header=0)
    mat = mat[['X','Y']]
    mat = roi2mat(mat)
    counter = 2
    while counter<=n_csv:
        nextMat = pd.read_csv(csv_path+str(counter) + ".csv",index_col=0, header=0)
        nextMat = nextMat[['X','Y']]
        nextMat = roi2mat(nextMat)
        mat = combine_roi(mat, nextMat)
        counter+=1
    return mat

def register_movie(root, movie_name,pad=True):
    tiff = root+movie_name+'/'+movie_name+'.tif'
    r_tiff =root+movie_name+'/r_'+movie_name+'.tif'
    csv_path = root+movie_name+'/roi/'
    import os
    (_,_,filenames) = next(os.walk(csv_path))
    n_roi = len(filenames)
    print("Number of ROI found: ", n_roi)
    print("Start registration...")
    register_w_roi(tiff,r_tiff,csv_path,n_roi=n_roi,pad=True)
    print("Registration of {} was successful. Saved in {} .".format(movie_name, r_tiff))
    return
    
def register_w_roi(tiff_path,out_tiff_path, csv_path,n_roi=2,high_res=True,compress=1,pad=True):
    trans_mat = combine(csv_path, n_csv = n_roi)
    metadata = register(tiff_path,trans_mat,out_tiff_path,highres=high_res,compress=compress, pad=pad)
    return metadata

def roi2mat(roi_df):
    x = roi_df.iloc[:,0]
    y = roi_df.iloc[:,1]
    translation =[(0,0)]
    x0 = x[0]
    y0 = y[0]
    i = 1
    while i < len(x) :
        diff_x = int(round((x[i] - x0)))
        diff_y = int(round((y[i] - y0)))
        translation.append((diff_x, diff_y))
        i+=1
    
    return translation

def combine_roi(mat1, mat2):
    last_x, last_y = mat1[-1]
    mat2 = [(a+last_x, b+last_y) for a, b in mat2 ]
    mat2 = mat2[1:]
    mat = mat1 + mat2
    return mat

def translate(im_in,translation,hi_res=True,compression=1,padzeros = True):
    '''
        input:
        im_in: input tiff
        translation: translation matrix
        output:
        im_out: output tiff
        
        tifffile documentation: https://scikit-image.org/docs/0.12.x/api/skimage.external.tifffile.html
        '''
    
    # scalar multiply the translation matrix for high-res
    if hi_res == True:
        translation = np.array(translation) * compression
    translation = np.array(translation).astype(int)
    
    n_channel = 1
    if len(im_in.shape) == 5:
        # multiple channel
        print("Multiple channels detected...")
        n_frame, n_zstep, n_channel, y_dim, x_dim = im_in.shape
    else:
        # single channel
        print("Single channel detected...")
        n_frame, n_zstep, y_dim, x_dim = im_in.shape
    
    if padzeros == False:
        # create empty tiff
        im_out = np.zeros(im_in.shape)
        for t in range(n_frame):
            print("Start processing t = " + str(t))
            trans_x, trans_y = translation[t]
            for z in range(n_zstep):
                if n_channel == 1:
                    for y in range(y_dim):
                        for x in range(x_dim):
                            if (x+trans_x < 0) or (y+trans_y < 0):
                                continue
                            elif (x+trans_x >= x_dim) or (y+trans_y >= y_dim):
                                continue
                            else:
                                im_out[t][z][y][x] = im_in[t][z][y+trans_y][x+trans_x]
                else:
                    for ch in range(n_channel):
                        for y in range(y_dim):
                            for x in range(x_dim):
                                if (x+trans_x < 0) or (y+trans_y < 0):
                                    continue
                                elif (x+trans_x >= x_dim) or (y+trans_y >= y_dim):
                                    continue
                                else:
                                    im_out[t][z][ch][y][x] = im_in[t][z][ch][y+trans_y][x+trans_x]

    
    else:
        # search for extrema
        x_low, x_high  = 0, x_dim
        y_low, y_high  = 0, y_dim
        for t in range(n_frame):
            trans_x, trans_y = translation[t]
            if -trans_y < y_low:
                y_low = -trans_y
            if y_dim-trans_y > y_high:
                y_high = y_dim-trans_y
            if -trans_x < x_low:
                x_low = -trans_x
            if x_dim-trans_x > x_high:
                x_high = x_dim-trans_x
            
            x_high, x_low, y_high, y_low = int(x_high), int(x_low), int(y_high), int(y_low)
            x_dim_adj, y_dim_adj = x_high-x_low, y_high-y_low
            #create empty tiff
        if n_channel == 1:
            im_out = np.zeros((n_frame, n_zstep, y_dim_adj, x_dim_adj))
        else:
            im_out = np.zeros((n_frame, n_zstep, n_channel, y_dim_adj, x_dim_adj))
        # translate
        for t in range(n_frame):
            print("Start processing t = " + str(t))
            trans_x, trans_y = translation[t]
            for z in range(n_zstep):
                if n_channel==1:
                    for y in range(y_dim):
                        for x in range(x_dim):
                            im_out[t][z][y-trans_y-y_low][x-trans_x-x_low] = int(im_in[t][z][y][x])
                else:
                    for ch in range(n_channel):
                        for y in range(y_dim):
                            for x in range(x_dim):
                                im_out[t][z][ch][y-trans_y-y_low][x-trans_x-x_low] = int(im_in[t][z][ch][y][x])

    return im_out

def register(tiff_path, trans_mat, out_tiff_path, highres = True, compress = 1, pad = True):
    '''
        tiff_path: tiff file name
        trans_mat: translation matrix, can be obtained by roi2mat()
        highres: optional, if set to True, will multiply the trans_mat by compress (which is set to 3 by default)
        compress: as above
        pad: whehther or not pad the periphery to zeros. If false, will crop the tiff
        
        This function returns a dict of metadata, and writes the tiff to current working directory
        
        '''
    with tifffile.TiffFile(tiff_path) as tif:
        # read tiff
        im_in = tif.asarray()
        # read metadata as tif_tags (dict)
        tif_tags = tif.pages[0].tags.values()
    
    
    # register using trans_mat
    im_out = translate(im_in,trans_mat,hi_res=highres,compression=compress,padzeros=pad)
    im_out = im_out.astype('uint16')
    
    # save registered tiff, no compression
    with tifffile.TiffWriter(out_tiff_path, bigtiff = highres) as tif:
        for i in range(im_out.shape[0]):
            tif.save(im_out[i])
    return tif_tags

################################################
# Cell object
################################################
class cell(object):
    def __init__(self):
        self.centID_i = None # track object, i
        self.centID_j = None # track object, j
        self.t_overlap = None 
        self.t_cong = 0 # congression, continuous time duration under 5 micron
        self.sl_i = None # spindle length initial
        self.sl_f = None # spindle length final
        self.sl_min = None # minimum spindle length
        self.sl_max = None # maximum spindle length
        self.center = None # xyz coords of center
        self.center_stdev = None
        self.normal_stdev = None
        self.dist2border = None # dist from the center of cell to closest tiff border
        self.diam = None
        self.intensity = None
        self.contrast = None
        
############################################
# Spot object
############################################
class spot(object):
    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        self.t = None
        self.id = None
        self.raw_int = None
        self.Nbr = None
        self.currLoc = None
        self.sumInt = None
        self.next = None
        self.intRatio = None
        self.dist = None
        self.summinRatio = None
        self.diam = None
        self.maxInt = None
        self.contrast = None
 
    
################################################
# Edge object
################################################
class edge(object):
    def __init__(self):
        self.source = None
        self.target = None
        self.track_id = None
        self.t = None
        
################################################
# Track object
################################################
class track(object):
    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        self.id = None
        self.t_i = None
        self.t_f = None
        self.duration = None
        self.contrast = None
        self.intensity = None
        self.diameter = None
        
        
################################################
# Pairer object
################################################
class TrackPairer(object):
    def __init__(self,xml,DIM=None,maxdist=11,mindist=4,maxcongdist=4,minoverlap=10):
        """
        Initialzing a pairer object
        
        - The xml argument is path of the TrackMate xml input, as a string
                
        - The DIM argument is an option for user to input the dimension (width,y=height) of the movie, optional
        
        - The maxdist argument is a distance threshold of how far away two paired centrosomes can be at any time point
        
        - The maxcongdist argument is a distance threshold of hor far away two centrosomes can be but still counted as "in congression"
        
        - The minoverlap argument is a duration threshold. Two tracks with fewer overlapped frames will be filtered.
    
        - The mindist arguent is a distance threshold of the minimum proximity two centrosomes must have for at least 1 time frame in order to be considered as "paired"
        """
        print("Input parameters: ")
        print("maxdist (um): ",maxdist)
        print("mindist (um) : ",mindist)
        print("maxcongdist (um) : ",maxcongdist)
        print("minoverlap (s) ",minoverlap)
        # store the provided variables
        self.xml_path = xml
        self.min_overlap = minoverlap
        self.max_dist = maxdist
        self.min_dist = mindist
        self.maxcongdist = maxcongdist
        self.DIM = DIM
        
        # create dynamic variables
        self.nbrTracks = []
        self.allTracks = {}
        self.allSpots = {}
        self.allEdges = {}
        self.cells = []
        self.top = None
        self.bottom = None
        self.left = None
        self.right = None
        
    def track_dist2border(self, x, y):
        '''
        Finds the distance of track mean position to the closest border
        '''
        toTop = y - self.top
        toBottom = self.bottom - y 
        toLeft = x - self.left
        toRight = self.right - x
        return min([toTop, toBottom, toLeft, toRight])

        
    def getAllTracks(self, f, originalMovie):
        # read tiff dim
        if self.DIM == None:
            self.top, self.bottom, self.left, self.right = findCroppedDim(tiff_path = originalMovie)
        # read from xml all info about tracks
        track_general, track_detail = parseTracks(self.xml_path)
                
        # populate edge objects
        for index, row in track_detail.iterrows():
            myEdge = edge()
            myEdge.source = int(row['SPOT_SOURCE_ID'])
            myEdge.target = int(row['SPOT_TARGET_ID'])
            myEdge.track_id = int(row['TRACK_ID'])
            myEdge.t = float(int(row['EDGE_TIME'])) # round to nearest int
            if myEdge.track_id in self.allEdges:
                self.allEdges[myEdge.track_id][myEdge.t] = myEdge.source
            else:
                self.allEdges[myEdge.track_id] = {myEdge.t: myEdge.source}        
        # populate the track objects
        for index, row in track_general.iterrows():
            myTrack = track()
            myTrack.id = int(row['TRACK_ID'])
            myTrack.x = float(row['TRACK_X_LOCATION'])
            myTrack.y = float(row['TRACK_Y_LOCATION'])
            myTrack.z = float(row['TRACK_Z_LOCATION'])
            myTrack.t_i = float(row['TRACK_START']) 
            myTrack.t_f = float(row['TRACK_STOP'])
            myTrack.duration = float(row['TRACK_DURATION'])
            myTrack.diameter, myTrack.contrast, myTrack.intensity = self.findTrackInfo(myTrack)
            # apply the border filter
            dist2border = self.track_dist2border(myTrack.x, myTrack.y)
            if dist2border <= 0: # track on border, discard the track
                f.write(str(int(myTrack.id)) + ' not included: outside border\n')
                continue
            # apply the track duration filter
            if myTrack.duration < self.min_overlap:
                f.write(str(int(myTrack.id)) +' not included: duration less than min_overlap\n')
                continue
            # centrosome diameter filter
            self.allTracks[myTrack.id] = myTrack
        return self.allTracks
    
    def getAllSpots(self):
        spots = parseSpots(self.xml_path)
        # populate the track objects
        for index, row in spots.iterrows():
            mySpot = spot()
            mySpot.id = int(row['ID'])
            mySpot.x = float(row['POSITION_X'])
            mySpot.y = float(row['POSITION_Y'])
            mySpot.z = float(row['POSITION_Z'])
            mySpot.diam = float(row['ESTIMATED_DIAMETER'])
            mySpot.maxInt = float(row['MAX_INTENSITY'])
            mySpot.contrast = float(row['CONTRAST'])
            self.allSpots[mySpot.id] = mySpot
        return self.allSpots
    
    def findTrackInfo(self, myTrack):
        # print(myTrack.id)
        t = myTrack.t_i
        maxInt = []
        diam = []
        contrast = []
        while t <= myTrack.t_f:
            if t not in self.allEdges[myTrack.id]: 
                t+=1
                continue
            spotID = self.allEdges[myTrack.id][int(t)]
            spot = self.allSpots[spotID]
            maxInt.append(spot.maxInt)
            contrast.append(spot.contrast)
            diam.append(spot.diam)
            t+=1
        if len(diam) <1:
            return 0,0,0
        return mean(diam), mean(contrast), mean(maxInt)
        
    
    def findDist(self, id_i, id_j):
        '''
        finds the distance between two tracks over time
        input: id_i and id_j are track id's
        '''
        # create list of time
        time = [] 
        # create a list of corresponding distance 
        sl = []
        centers = {'x': [], 'y':[], 'z': []}
        normals = {'x': [], 'y':[], 'z': []}
        # get track objects by id
        trackI = self.allTracks[id_i]
        trackJ = self.allTracks[id_j]
        # find start and stop time (overlapped between two tracks)
        start = max([trackI.t_i,trackJ.t_i])
        stop = min([trackI.t_f, trackJ.t_f])
        if stop - start <= 0:
            return
        t = start 
        
        while t < stop :    
            # calculate distance
            # find ids of spots from i, j
            if t not in self.allEdges[trackI.id]: 
                # note: allEdges[trackI.id] is a dict, k is time, v is spot_id
                t+=1
                continue
            if t not in self.allEdges[trackJ.id]:
                t+=1
                continue
            # get spot id
            spot_i = self.allEdges[trackI.id][t]
            spot_j = self.allEdges[trackJ.id][t]
            # find spot loc by spot id
            ix = self.allSpots[spot_i].x
            iy = self.allSpots[spot_i].y
            iz = self.allSpots[spot_i].z
            jx = self.allSpots[spot_j].x
            jy = self.allSpots[spot_j].y
            jz = self.allSpots[spot_j].z
            dist = distance.euclidean((ix,iy,iz),(jx,jy,jz))
            center = ((ix+jx)/2, (iy+jy)/2, (iz+jz)/2)
            normal = ((ix-jx), (iy-jy), (iz-jz))
            # normalized normal vector
            n_normal = normalize(normal)
            # update dynamic variables
            time.append(t)
            sl.append(dist)
            centers['x'].append(center[0])
            centers['y'].append(center[1])
            centers['z'].append(center[2])
            normals['x'].append(n_normal[0])
            normals['y'].append(n_normal[1])
            normals['z'].append(n_normal[2])
            t+=1
        return sl, centers, normals, time
          
    def cell_dist2border(self):
        '''
        Finds the distance of cell center to the closest border
        '''
        for myCell in self.cells:          
            # unpack cell_center
            x, y, z = myCell.center
            toTop = y - self.top
            toBottom = self.bottom - y 
            toLeft = x - self.left
            toRight = self.right - x
            myCell.dist2border = min([toTop, toBottom, toLeft, toRight])

    def findNeighbors(self, f, originalMovie, framerate):
        # 1. spots bookkeeping
        self.allSpots = self.getAllSpots()
        # 2. tracks and edges bookkeeping
        self.allTracks = self.getAllTracks(f, originalMovie)
        # 3. find neighbors by crude filters
        print("Total number of tracks: " + str(len(self.allTracks)) )
        for myTrack in self.allTracks.values():            
            for nbr in self.allTracks.values():
                # 1) if track duration less than min_overlap, out
                if nbr.duration < self.min_overlap:
                    continue
                # 2)  myTrack is the same track as nbr, out
                elif myTrack.id == nbr.id:
                    continue
                # 3) find period of overlap: if fewer frames than min_overlap , out
                t_start = max([myTrack.t_i, nbr.t_i]) 
                t_stop = min([myTrack.t_f, nbr.t_f])
                if t_stop - t_start < self.min_overlap:
                    f.write(str(int(myTrack.id)) + ' and ' + str(int(nbr.id)) + ' not pair: overlap time too short\n')
                    continue
                # 4) find max distance: if greater than max_dist um, out
                dist, centers, normals, time = self.findDist(myTrack.id, nbr.id)
                if len(dist) < 2:
                    f.write(str(int(myTrack.id)) + ' and ' + str(int(nbr.id)) + ' not pair: overlap time too short (<2) \n')
                    continue
                avg_dist = mean(dist)
                max_dist = max(dist)
                min_dist = min(dist)
                if avg_dist > self.max_dist:
                    f.write(str(int(myTrack.id)) + ' and ' + str(int(nbr.id)) + ' not pair: too far away\n')
                    continue
                # 5) find min distance, if greater than min_dist microns, out FOR DEBUG
                if min_dist > self.min_dist:
                    f.write(str(int(myTrack.id)) + ' and ' + str(int(nbr.id)) + ' not pair: too far away (min distance filter) \n')
                    continue
                # filtering finished, fill in cell info
                myCell = cell()
                myCell.centID_i = myTrack.id
                myCell.centID_j = nbr.id
                myCell.t_overlap = t_stop - t_start
                myCell.sl_i = dist[0]
                myCell.sl_f = dist[-1]
                myCell.sl_max = max_dist
                myCell.sl_min = min_dist
                myCell.center = (mean(centers['x']), mean(centers['y']), mean(centers['z']))
                stdev_x = stdev(centers['x'])
                stdev_y = stdev(centers['y'])
                stdev_z = stdev(centers['z'])
                stdev_x_n = stdev(normals['x'])
                stdev_y_n = stdev(normals['y'])
                stdev_z_n = stdev(normals['z'])
                myCell.center_stdev = (stdev_x**2 + stdev_y**2 + stdev_z**2)**0.5
                myCell.normal_stdev = (stdev_x_n**2 + stdev_y_n**2 + stdev_z_n**2)**0.5
                myCell.t_cong = findCong(time, dist, self.maxcongdist) * framerate
                myCell.contrast = (myTrack.contrast + nbr.contrast)/2
                myCell.intensity = (myTrack.intensity + nbr.intensity)/2
                myCell.diameter = (myTrack.diameter + nbr.diameter)/2
                self.cells.append(myCell)
        self.cell_dist2border()
        return self.cells
    
    def linkID(self, trackIDList):
        '''
        Creates a dictionary of trackID: [SpotIDs]
        '''
        track2spot = {}
        spot2track = {}
        for trackID in trackIDList:
            track2spot[trackID] = []
            track = self.allTracks[trackID]
            start = track.t_i
            stop = track.t_f            
            t = start 
            while t < stop :    
                if t not in self.allEdges[trackID]: 
                    t+=1
                    continue
                # get spot id
                spotID = self.allEdges[trackID][t]
                t+=1
                track2spot[trackID].append(spotID)
                spot2track[spotID] = trackID
        return track2spot, spot2track
        
    def pred2SpotCSV(self,r_xml_path,out_folder,out_name):
        pred = pd.read_csv(out_folder+'/predictions.csv')
        spots = parseSpots(r_xml_path)
        allTracks = []
        allPairs = []
        for index, row in pred.iterrows():
            if int(row['Predicted_Label']) == 1 :
                i = int(row['centID_i'])
                j = int(row['centID_j'])
                allTracks.append(i)
                allTracks.append(j)
                allPairs.append((i,j))
        allTracks = list(set(allTracks)) # unique
        if allTracks == []: 
            print("No cells found")
            return 
        track2spots, spot2track = self.linkID(allTracks) # link spot to track
        for i, j in allPairs:
            if (j,i) in allPairs:
                allPairs.remove((j,i))
                
        allSpotIDs = []        
        for k, v in track2spots.items():
            allSpotIDs = allSpotIDs + v
        mySpots = {}    
        for index, row in spots.iterrows():
            spotID = int(row['ID'])
            if spotID in allSpotIDs:
                row['TRACK_ID'] = spot2track[spotID]
                mySpots[spotID]=row
        counter = 0
        allSpots = []
        for i, j in allPairs:
            counter+=1
            spots_i = track2spots[i]
            spots_j = track2spots[j]
            name_i ='Cent_'+str(counter)+'a'
            name_j ='Cent_'+str(counter)+'b'
            for spotID in spots_i:
                spotSeries = mySpots[spotID].copy()
                spotSeries['Label'] = name_i
                allSpots.append(spotSeries)
            for spotID in spots_j:
                spotSeries = mySpots[spotID].copy()
                spotSeries['Label'] = name_j
                allSpots.append(spotSeries)
        df = pd.DataFrame(allSpots)
        # reorder
        df = df[["Label", "ID", "TRACK_ID",
                 "QUALITY", "POSITION_X","POSITION_Y", 
                 "POSITION_Z", "POSITION_T", "FRAME", 
                 "RADIUS", "VISIBILITY", "MANUAL_COLOR", 
                 "MEAN_INTENSITY", "MEDIAN_INTENSITY",
                 "MIN_INTENSITY", "MAX_INTENSITY",
                 "TOTAL_INTENSITY", "STANDARD_DEVIATION",
                 "ESTIMATED_DIAMETER", "ESTIMATED_DIAMETER", "SNR"]]
        
        df['POSITION_Z'] = df['POSITION_Z'].astype('float') 
        df['POSITION_X'] = df['POSITION_X'].astype('float') 
        df['POSITION_Y'] = df['POSITION_Y'].astype('float') 
        df['POSITION_T'] = df['POSITION_T'].astype('float')  
        
        df.to_csv(out_name, index=False)
        print("Number of cells found: " + str(len(allPairs)))
        return allSpots, allPairs
        
        
def cell2df(cells):
    myDict = {
        'center_stdev': [],
               'normal_stdev': [],
              'sl_f': [],
              'sl_i': [],
              'sl_max': [],
              'sl_min': [],
              't_cong': [],
              't_overlap': [],
              'intensity': [],
              'diameter': [],
              'contrast': [],
              'centID_i': [],
              'centID_j': []}
    for myCell in cells:
        myDict['center_stdev'].append(myCell.center_stdev)
        myDict['normal_stdev'].append(myCell.normal_stdev)
        myDict['sl_f'].append(myCell.sl_f)
        myDict['sl_i'].append(myCell.sl_i)
        myDict['sl_max'].append(myCell.sl_max)
        myDict['sl_min'].append(myCell.sl_min)
        myDict['t_cong'].append(myCell.t_cong)
        myDict['t_overlap'].append(myCell.t_overlap)
        myDict['intensity'].append(myCell.intensity)
        myDict['diameter'].append(myCell.diameter)
        myDict['contrast'].append(myCell.contrast)
        myDict['centID_i'].append(myCell.centID_i)
        myDict['centID_j'].append(myCell.centID_j)
    
    df = pd.DataFrame(myDict)
    
    # normalize contrast and intensity
        
    scaler = MinMaxScaler()
    df['contrast'] = scaler.fit_transform(df['contrast'].values.reshape(-1,1))
    df['intensity'] = scaler.fit_transform(df['intensity'].values.reshape(-1,1))

    return df

def pair(clf,r_xml_path,originalMovie,out_folder,csv_path,maxdist=11,mindist=4,maxcongdist=4,minoverlap=10,dim=None):
    f = open(out_folder+'/console.txt', 'w')
    print('Original movie: ' + originalMovie)
    # crude pairer, generate features
    if dim == None:
        myPairer = TrackPairer(r_xml_path,maxdist=maxdist,mindist=mindist,maxcongdist=maxcongdist,minoverlap=minoverlap)
    else: 
        myPairer = TrackPairer(r_xml_path,DIM = dim,maxdist=maxdist,mindist=mindist,maxcongdist=maxcongdist,minoverlap=minoverlap)
        myPairer.left, myPairer.right, myPairer.top, myPairer.bottom = dim 
    framerate = getFramerate(r_xml_path)
    cells = myPairer.findNeighbors(f, originalMovie,framerate)
    df = cell2df(cells)
    df.to_csv(out_folder+'/features.csv', index = False, header=True)
    print("Potential pairs generated.")
    # generate features panel for ml clf
    X_df = pd.read_csv(out_folder+'/features.csv', usecols = range(11))    
    X = X_df.to_numpy()
    # predict
    y_pred = clf.predict(X)
    df['Predicted_Label'] = y_pred
    df = df.loc[df['centID_j'] > df['centID_i']]
    df.to_csv (out_folder+'/predictions.csv', index = False, header=True)
    print("Predictions generated.")
    f.close()
    myPairer.pred2SpotCSV(r_xml_path,out_folder,csv_path)
        
       
def features2spots(features,r_xml_path,movie,output_csv_path):
    # pred to spots
    spots_df = parseSpots(r_xml_path)
    spots = getAllSpots(r_xml_path)
    tracks , edges = getAllTracks(r_xml_path, spots)
    allTracks = []
    allPairs = []
    for index, row in features.iterrows():
        # if int(row['Predicted_Label']) == 1 : 
        i = int(row['centID_i'])
        j = int(row['centID_j'])
        allTracks.append(i)
        allTracks.append(j)
        allPairs.append((i,j))
    allTracks = list(set(allTracks)) # unique
    if allTracks == []: 
        print("No cells found")
        return
    track2spots, spot2track = linkID(allTracks,tracks, edges) # link spot to track
    for i, j in allPairs:
        if (j,i) in allPairs:
            allPairs.remove((j,i))
            
    allSpotIDs = []        
    for k, v in track2spots.items():
        allSpotIDs = allSpotIDs + v
    mySpots = {}    
    for index, row in spots_df.iterrows():
        spotID = int(row['ID'])
        if spotID in allSpotIDs:
            row['TRACK_ID'] = spot2track[spotID]
            mySpots[spotID]=row
    counter = 0
    allSpots = []
    for i, j in allPairs:
        counter+=1
        spots_i = track2spots[i]
        spots_j = track2spots[j]
        name_i ='Cent_'+str(counter)+'a'
        name_j ='Cent_'+str(counter)+'b'
        for spotID in spots_i:
            spotSeries = mySpots[spotID].copy()
            spotSeries['Label'] = name_i
            allSpots.append(spotSeries)
        for spotID in spots_j:
            spotSeries = mySpots[spotID].copy()
            spotSeries['Label'] = name_j
            allSpots.append(spotSeries)
    
    df = pd.DataFrame(allSpots)
    # reorder
    df = df[["Label", "ID", "TRACK_ID",
             "QUALITY", "POSITION_X","POSITION_Y", 
             "POSITION_Z", "POSITION_T", "FRAME", 
             "RADIUS", "VISIBILITY", "MANUAL_COLOR", 
             "MEAN_INTENSITY", "MEDIAN_INTENSITY",
             "MIN_INTENSITY", "MAX_INTENSITY",
             "TOTAL_INTENSITY", "STANDARD_DEVIATION",
             "ESTIMATED_DIAMETER", "ESTIMATED_DIAMETER", "SNR"]]
    
    df['POSITION_Z'] = df['POSITION_Z'].astype('float')
    df['POSITION_X'] = df['POSITION_X'].astype('float') 
    df['POSITION_Y'] = df['POSITION_Y'].astype('float') 
    df['POSITION_T'] = df['POSITION_T'].astype('float') 
    
    
    df.to_csv('{}_spots_all.csv'.format(movie), index=False)
    print("Number of cells: " + str(len(allPairs)))

def getAllTracks(xml_path,allSpots):
    track_general, track_detail = parseTracks(xml_path)
    allEdges = {}
    allTracks = {}
    for index, row in track_detail.iterrows():
        myEdge = edge()
        myEdge.source = int(row['SPOT_SOURCE_ID'])
        myEdge.target = int(row['SPOT_TARGET_ID'])
        myEdge.track_id = int(row['TRACK_ID'])
        myEdge.t = float(int(row['EDGE_TIME'])) # round to nearest int
        if myEdge.track_id in allEdges:
            allEdges[myEdge.track_id][myEdge.t] = myEdge.source
        else:
            allEdges[myEdge.track_id] = {myEdge.t: myEdge.source}        
    # populate the track objects
#     track_general['TRACK_DURATION'] =  track_general['TRACK_DURATION']/60
#     track_general['TRACK_START'] =  track_general['TRACK_START']/60
#     track_general['TRACK_STOP'] =  track_general['TRACK_STOP']/60
    
    for index, row in track_general.iterrows():
        myTrack = track()
        myTrack.id = int(row['TRACK_ID'])
        myTrack.x = float(row['TRACK_X_LOCATION'])
        myTrack.y = float(row['TRACK_Y_LOCATION'])
        myTrack.z = float(row['TRACK_Z_LOCATION'])
        myTrack.t_i = float(row['TRACK_START'])
        myTrack.t_f = float(row['TRACK_STOP'])
        myTrack.duration = float(row['TRACK_DURATION'])
        myTrack.diameter, myTrack.contrast, myTrack.intensity = findTrackInfo(myTrack, allEdges, allSpots)
        allTracks[myTrack.id] = myTrack
    return allTracks, allEdges

def getAllSpots(xml_path):
    spots = parseSpots(xml_path)
    allSpots = {}
    # populate the track objects
    for index, row in spots.iterrows():
        mySpot = spot()
        mySpot.id = int(row['ID'])
        mySpot.x = float(row['POSITION_X'])
        mySpot.y = float(row['POSITION_Y'])
        mySpot.z = float(row['POSITION_Z'])
        mySpot.diam = float(row['ESTIMATED_DIAMETER'])
        mySpot.maxInt = float(row['MAX_INTENSITY'])
        mySpot.contrast = float(row['CONTRAST'])
        allSpots[mySpot.id] = mySpot
    return allSpots

def findTrackInfo(myTrack, allEdges, allSpots):
    # print(myTrack.id)
    t = myTrack.t_i
    maxInt = []
    diam = []
    contrast = []
    while t <= myTrack.t_f:
        if t not in allEdges[myTrack.id]: 
            t+=1
            continue
        spotID = allEdges[myTrack.id][int(t)]
        spot = allSpots[spotID]
        maxInt.append(spot.maxInt)
        contrast.append(spot.contrast)
        diam.append(spot.diam)
        t+=1
    if len(diam) <1:
        return 0,0,0
    return mean(diam), mean(contrast), mean(maxInt)
    


def linkID(trackIDList, allTracks,allEdges):
    '''
    Creates a dictionary of trackID: [SpotIDs]
    '''
    track2spot = {}
    spot2track = {}
    for trackID in trackIDList:
        track2spot[trackID] = []
        track = allTracks[trackID]
        start = track.t_i
        stop = track.t_f            
        t = start 
        while t < stop :    
            if t not in allEdges[trackID]: 
                t+=1
                continue
            # get spot id
            spotID = allEdges[trackID][t]
            t+=1
            track2spot[trackID].append(spotID)
            spot2track[spotID] = trackID
    return track2spot, spot2track


def getFramerate(xml):
    with open(xml, 'r') as f:
        lines = f.readlines()
        for l in lines:
            if l.startswith("  T ="):
                import re
                framerate = float(re.findall(r'\d+', l)[2] + '.' + re.findall(r'\d+', l)[3])
                print("framerate (per sec): ", framerate)
                return framerate
        framerate = input("framerate not found in xml.. Please input manually: ")
        return framerate
    
    
def spots2coords(out_csv,out_coords,out_cellid):
    try:
        spots = pd.read_csv(out_csv)
    except FileNotFoundError:
        print("Spots csv not found.")
        return
    cent_dict = {}
    for index, row in spots.iterrows():
        cell_id = row['Label'][:-1]
        side = row['Label'][-1]
        if cell_id not in cent_dict:
            cent_dict[cell_id] = {'a':{},'b':{}}
        frame = row['FRAME']
        cent_dict[cell_id][side][frame] = (row['POSITION_X'],row['POSITION_Y'],row['POSITION_Z'])
    df_list = []
    for cell_id, mydict in cent_dict.items():
        id = 'Cell_'+cell_id.split("_")[1]
        frames = set(mydict['a'].keys()).intersection(mydict['b'].keys())
        for f in frames:
            x,y,z = [(mydict['a'][f][0] + mydict['b'][f][0])/2,
                   (mydict['a'][f][1] + mydict['b'][f][1])/2,
                   (mydict['a'][f][2] + mydict['b'][f][2])/2 ]
            df_list.append([id, f,x,y,z])
    df = pd.DataFrame(df_list)
    df.columns = ['Cell','Frame','X','Y','Z']
    df.to_csv(out_coords,sep='\t',index=None)
    pd.DataFrame(df['Cell'].unique()).to_csv(out_cellid,index=None,header=None)
