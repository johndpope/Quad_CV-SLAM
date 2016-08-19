"""
Created on Wed Jun 1 2016

@author: Yang
"""
#!python3


####TODO
# 2D3D correspondence
# Index points

#module
import numpy as np
import cv2
import math
import cvtools

#constants
import modes


#custom classes
from convexHull import ConvexHull
from KLTtracker import KLTtracker
from pointCloud import PointCloud
from reconstructor import PointReconstructor

#parameters
showROIBox = True
showKeypoints = True
showTracks = True

ROIUpdateFrames = 10
MatchUpdateFrames = 5

#set up mode
mode = modes.PRE_INIT

#videoInput
cap = cv2.VideoCapture("data050.avi")
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
diagLength = math.sqrt(width**2+height**2)


#object initialization
convexHull = ConvexHull()
bf = cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck = True)
orb = cv2.ORB_create()
tracker = None
rect = None
p0 = None
p1 = None
pointCloud = None

map2D3D = []
map3D2D = []

K = np.matrix([[width,0,width/2],[0,width,height/2],[0,0,1]])

#threshold
distThresh = 0.3

cv2.ocl.setUseOpenCL(False)

#frame counter
counter = 0

#main loop
while(cap.isOpened()):
    ret, frame = cap.read()
    if(type(frame)!=np.ndarray):
        break

    #updates ROI every certain number of frames
    if(counter%ROIUpdateFrames==0 and counter!=0):
        hull,rect = convexHull.boundingRect(frame)
        
    
    if(mode==modes.PRE_INIT):
        #gets ROI
        hull,rect = convexHull.boundingRect(frame)
        img = frame[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2]]
        kp, des = orb.detectAndCompute(img, None)
        
        if(counter==1):
            mode = modes.INIT
            tracker = KLTtracker(frame,kp,des,rect)
            

    elif(mode==modes.INIT):
        img = frame[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2]]
        
        #refreshes points being tracked every certain number of frames
        if(counter%MatchUpdateFrames==0 and counter!=0):
            p0,p1 = tracker.match(frame,orb,bf)
        else:
            p0,p1 = tracker.track(frame)
        kp, des = orb.detectAndCompute(img, None)

        #get percent drift
        average = 0
        for i in range(len(p0)):
            average+=math.sqrt((p0[i][0]-p1[i][0])**2+(p0[i][1]-p1[i][1])**2)
        average/=p0.size
        percentDist = (average/diagLength)*100

        #if percent drift passes threshold
        if(percentDist>distThresh):
            #creates essential matrix
            P1 = K*np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0]])
            F = cv2.findFundamentalMat(p0, p1,cv2.FM_8POINT)[0]
            E = K.transpose()*F*K
            U,S,V = np.linalg.svd(E)
            possible = cvtools.getProjectionMatrices(U,S,V)
            P2 = cvtools.getCorrectProjectionMatrix(possible, K, p0, p1)
            P2 = K*P2

            print(P1)
            print(P2)

            #creates pointCloud
            pointCloud = cv2.triangulatePoints(P1,P2,p0.transpose(),p1.transpose())
            mode = modes.PNP

            map2D3D = list(range(pointCloud.shape[1]))
            map3D2D = list(range(pointCloud.shape[1]))
            
    elif(mode==modes.PNP):
        img = frame[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2]]
        if(counter%MatchUpdateFrames==0 and counter!=0):
            p0,p1 = tracker.match(frame,orb,bf)
        else:
            p0,p1 = tracker.track(frame, True, map2D3D, map3D2D)

        kp, des = orb.detectAndCompute(img, None)

##        average = 0
##        for i in range(len(p0)):
##            average+=math.sqrt((p0[i][0]-p1[i][0])**2+(p0[i][1]-p1[i][1])**2)
##        average/=p0.size
##        percentDist = (average/diagLength)*100
##        if(percentDist>distThresh):
##            P1 = K*np.array([[1,0,0,0],[0,1,0,0],[0,0,1,0]])
##            F = cv2.findFundamentalMat(p0, p1,cv2.FM_8POINT)[0]
##            E = K.transpose()*F*K
##            U,S,V = np.linalg.svd(E)
##            possible = cvtools.getProjectionMatrices(U,S,V)
##            P2 = cvtools.getCorrectProjectionMatrix(possible, K, p0, p1)
##            P2 = K*P2
##            
##            p = cv2.triangulatePoints(P1,P2,p0.transpose(),p1.transpose())
##            temp = [0]*4
##            temp[0] = np.append(pointCloud[0],p[0])
##            temp[1] = np.append(pointCloud[1],p[1])
##            temp[2] = np.append(pointCloud[2],p[2])
##            temp[3] = np.append(pointCloud[3],p[3])
##            pointCloud = np.array(temp)
        
    #draws point tracks
    if(showTracks):
        if(p0!=None and p1!=None):
            for i in range(len(p0)):
                frame = cv2.line(frame,tuple(p0[i]),tuple(p1[i]),(0,255,0),2)

    #draws keypoints
    if(showKeypoints):
        img = frame[rect[1]:rect[1]+rect[3],rect[0]:rect[0]+rect[2]]
        if(img.size!=0):
            img = cv2.drawKeypoints(img, kp, img, color=(255,0,0))

    #draws ROI            
    if(showROIBox):        
        frame = cv2.drawContours(frame,[hull],-1,(0,0,255),1)
        frame = cv2.rectangle(frame,(rect[0],rect[1]),(rect[0]+rect[2],rect[1]+rect[3]),(255,0,0),1)

    cv2.imshow('frame',frame)
    k = cv2.waitKey(16) & 0xff
    if k == ord("q"):
        break

    counter+=1


cap.release()
cv2.destroyAllWindows()

print(pointCloud)
#cvtools.clusterPointCloud(pointCloud, 100)
cvtools.plotPointCloud(pointCloud)
