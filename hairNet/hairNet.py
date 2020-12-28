#---------------------------------------------------
# File HairNet.py
# Written by Rhett Jackson April 1, 2013
# Some routines were copied from "Curve Loop" by Crouch https://sites.google.com/site/bartiuscrouch/scripts/curveloop
# Some routines were copied from other sources
# Very limited at this time:
# NB 1) After running the script to create hair, the user MUST manually enter Particle Mode on the Head object and "touch" each point of each hair guide. Using a large comb brish with very low strength is a good way to do this. If it's not done, the hair strands are likely to be reset to a default/straight-out position during editing.
# NB 2) All meshes must have the same number of vertices in the direction that corresponds to hair growth
#---------------------------------------------------


import bpy
import mathutils

import traceback


from mathutils import Vector
from bpy.props import *

from . import_properties import  *

versionString = "0.6.2"

#Start Debug
DEBUG = 0

if DEBUG == 1:
    import sys
    pydev_path = '/Users/rhett/.p2/pool/plugins/org.python.pydev.core_7.7.0.202008021154/pysrc'
    if sys.path.count(pydev_path) < 1: sys.path.append(pydev_path) 
    
    import pydevd
    
    pydevd.settrace(stdoutToServer=True, stderrToServer=True, suspend=False)
    
#End Debug

# It is always good to use wrapper prop when attacking to common data block such as Object to reduce blend junk
class HairNetConfig(PropertyGroup):
    masterHairSystem: StringProperty(
        name="hnMasterHairSystem",
        description="Name of the hair system to be copied by this proxy object.",
        default="")
    
    isHairProxy: BoolProperty(
            name="hnIsHairProxy",
            description="Is this object a hair proxy object?",
            default=False)

    isEmitter: BoolProperty(
            name="hnIsEmitter",
            description="Is this object a hair emitter object?",
            default=False)

    sproutHairs: IntProperty(
            name="hnSproutHairs",
            description="Number of additional hairs to add.",
            default=0)

    # subdivideHairSections: IntProperty(
    #         name="hnSubdivideHairSections",
    #         description="Number of subdivisions to add along the guide hairs",
    #         default=0)

def debPrintVertEdges(vert_edges):
    print("vert_edges: ")
    for vert in vert_edges:
        print(vert, ": ", vert_edges[vert])

def debPrintEdgeFaces(edge_faces):
    print("edge_faces: ")
    for edge in edge_faces:
        print(edge, ": ", edge_faces[edge])

def debPrintEdgeKeys(edges):
    for edge in edges:
        print(edge, " : ", edge.key)

def debPrintHairGuides(hairGuides):
    print("Hair Guides:")
    guideN=0

    for group in hairGuides:
        print("Guide #",guideN)
        i=0
        for guide in group:
            print(i, " : ", guide)
            i += 1
        guideN+=1

def debPrintSeams(seamVerts, seamEdges):
    print("Verts in the seam: ")
    for vert in seamVerts:
        print(vert)
    print("Edges in the seam: ")
    for edge in seamEdges:
        print(edge.key)

def debPrintLoc(func=""):
    obj = bpy.context.object
    print(obj.name, " ", func)
    print("Coords", obj.data.vertices[0].co)

def getEdgeFromKey(mesh,key):
    v1 = key[0]
    v2 = key[1]
    theEdge = 0
    for edge in mesh.edges:
        if v1 in edge.vertices and v2 in edge.vertices:
            #print("Found edge :", edge.index)
            return edge
    return 0

# returns all edge loops that a vertex is part of
def getLoops(obj, v1, vert_edges, edge_faces, seamEdges):
    debug = False

    me = obj.data
    if not vert_edges:
        # Create a dictionary with the vert index as key and edge-keys as value
        #It's a list of verts and the keys are the edges the verts belong to
        vert_edges = dict([(v.index, []) for v in me.vertices if v.hide!=1])
        for ed in me.edges:
            for v in ed.key:
                if ed.key[0] in vert_edges and ed.key[1] in vert_edges:
                    vert_edges[v].append(ed.key)
        if debug: debPrintVertEdges(vert_edges)
    if not edge_faces:
        # Create a dictionary with the edge-key as key and faces as value
        # It's a list of edges and the faces they belong to
        edge_faces = dict([(ed.key, []) for ed in me.edges if (me.vertices[ed.vertices[0]].hide!=1 and me.vertices[ed.vertices[1]].hide!=1)])
        for f in me.polygons:
            for key in f.edge_keys:
                if key in edge_faces and f.hide!=1:
                    edge_faces[key].append(f.index)
        if debug : debPrintEdgeFaces(edge_faces)

    ed_used = [] # starting edges that are already part of a loop that is found
    edgeloops = [] # to store the final results in
    for ed in vert_edges[v1.index]: #ed is all the edges v1 is a part of
        if ed in ed_used:
            continue
        seamTest = getEdgeFromKey(me, ed)
        if seamTest.use_seam:
            #print("Edge ", seamTest.index, " is a seam")
            continue

        vloop = [] # contains all verts of the loop
        poles = [] # contains the poles at the ends of the loop
        circle = False # tells if loop is circular
        n = 0 # to differentiate between the start and the end of the loop

        for m in ed: # for each vert in the edge
            n+=1
            active_ed = ed
            active_v  = m
            if active_v not in vloop:
                vloop.insert(0,active_v)
            else:
                break
            stillGrowing = True
            while stillGrowing:
                stillGrowing = False
                active_f = edge_faces[active_ed] #List of faces the edge belongs to
                new_ed = vert_edges[active_v] #list of edges the vert belongs to
                if len(new_ed)<3: #only 1 or 2 edges
                    break
                if len(new_ed)>4: #5-face intersection
                    # detect poles and stop growing
                    if n>1:
                        poles.insert(0,vloop.pop(0))
                    else:
                        poles.append(vloop.pop(-1))
                    break
                for i in new_ed: #new_ed - must have 3 or 4 edges coming from the vert
                    eliminate = False # if edge shares face, it has to be eliminated
                    for j in edge_faces[i]: # j is one of the face indices in edge_faces
                        if j in active_f:
                            eliminate = True
                            break
                    if not eliminate: # it's the next edge in the loop
                        stillGrowing = True
                        active_ed = i
                        if active_ed in vert_edges[v1.index]: #the current edge contains v1

                            ed_used.append(active_ed)
                        for k in active_ed:
                            if k != active_v:
                                if k not in vloop:

                                    if n>1:
                                        vloop.insert(0,k)
                                    else:
                                        vloop.append(k)


                                    active_v = k
                                    break
                                else:
                                    stillGrowing = False # we've come full circle
                                    circle = True
                        break
        #TODO: Function to sort vloop. Use v1 and edge data to walk the ring in order
        vloop = sortLoop(obj, vloop, v1, seamEdges, vert_edges)
        edgeloops.append([vloop, poles, circle])
    for loop in edgeloops:
        for vert in loop[0]:
            me.vertices[vert].select=True
            #me.edges[edge].select=True
    return edgeloops, vert_edges, edge_faces




def getSeams(obj):
    debug = False
    #Make a list of all edges marked as seams
    error = 0
    seamEdges = []
    for edge in obj.data.edges:
        if edge.use_seam:
            seamEdges.append(edge)

    #Sort the edges in seamEdges
#     seamEdges = sortEdges(seamEdges)

    #Make a list of all verts in the seam
    seamVerts = []
    for edge in seamEdges:
        for vert in edge.vertices:
            if vert not in seamVerts:
                seamVerts.append(vert)

    if(len(seamEdges) < 2):
        error = 2
        return 0, 0, error

    seamVerts = sortSeamVerts(seamVerts, seamEdges)
    if debug: debPrintSeams(seamVerts, seamEdges)

    if(len(seamEdges) == 0):
        error = 2

    return seamVerts, seamEdges, error

def getNextVertInEdge(edge, vert):
    if vert == edge.vertices[0]:
        return edge.vertices[1]
    else:
        return edge.vertices[0]

def makeNewHairSystem(headObject,systemName):
    bpy.ops.object.mode_set(mode='OBJECT')
    #Adding a particle modifier also works but requires pushing/pulling the active object and selection.
    headObject.modifiers.new("HairNet", 'PARTICLE_SYSTEM')

    #Set up context override
#    override = {"object": headObject, "particle_system": systemName}
#    bpy.ops.object.particle_system_add(override)
    headObject.particle_systems[-1].name = systemName
    headObject.particle_systems[-1].settings.type = 'HAIR'
    headObject.particle_systems[-1].settings.render_step = 5
    return headObject.particle_systems[systemName]

def makePolyLine(objName, curveName, cList):
    #objName and curveName are strings cList is a list of vectors
    curveData = bpy.data.curves.new(name=curveName, type='CURVE')
    curveData.dimensions = '3D'

#     objectData = bpy.data.objects.new(objName, curveData)
#     objectData.location = (0,0,0) #object origin
#     bpy.context.scene.objects.link(objectData)

    polyline = curveData.splines.new('BEZIER')
    polyline.bezier_points.add(len(cList)-1)
    for num in range(len(cList)):
        x, y, z = cList[num]
        polyline.bezier_points[num].co = (x, y, z)
        polyline.bezier_points[num].handle_left_type = polyline.bezier_points[num].handle_right_type = "AUTO"

#     return objectData
    return curveData

def preserveSelection():
    #Preserve Active and selected objects
    storedActive = bpy.context.object
    storedSelected = []
    for sel in bpy.context.selected_objects:
        storedSelected.append(sel)

    return storedActive, storedSelected




def changeSelection(thisObject):
    storedActive, storedSelected = preserveSelection()

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=thisObject
    thisObject.select_set(state=True)
    return storedActive, storedSelected

def restoreSelection(storedActive, storedSelected):
    #Restore active object and selection
    bpy.context.view_layer.objects.active=storedActive
    bpy.ops.object.select_all(action='DESELECT')
    for sel in storedSelected:
        sel.select = True

def removeParticleSystem(object, particleSystem):
    override = {"object": object, "particle_system": particleSystem}
    bpy.ops.object.particle_system_remove(override)


def sortEdges(edgesList):
    sorted = []
    debPrintEdgeKeys(edgesList)

    return edgesList

def sortLoop(obj, vloop, v1, seamEdges, vert_edges):
    #The hair is either forward or reversed. If it's reversed, reverse it again. Otherwise do nothing.
    loop = []
    loopRange = len(vloop)-1

    if vloop[0] == v1.index:
        loop = vloop.copy()

    else:
        loop = vloop[::-1]
    return loop

def sortSeamVerts(verts, edges):

    debug = False
    sortedVerts = []
    usedEdges = []
    triedVerts = []
    triedEdges = []
    startingVerts = []

    #Make a list of starting points so that each island will have a starting point. Make another "used edges" list

    def findEndpoint(vert):
        for thisVert in verts:
            count = 0
            if thisVert not in triedVerts:
                triedVerts.append(thisVert)
                #get all edges with thisVert in it
                all_edges = [e for e in edges if thisVert in e.vertices]

                if len(all_edges) == 1:
                    #The vert is in only one edge and is thus an endpoint
                    startingVerts.append(thisVert)
                    #walk to the other end of the seam and add verts to triedVerts
                    walking = True
                    thatVert = thisVert
                    beginEdge = thatEdge = all_edges[0]
                    while walking:
                        #get the other vert in the edge
                        if thatVert == thatEdge.key[0]:
                            thatVert = thatEdge.key[1]
                        else:
                            thatVert = thatEdge.key[0]
                        #Add current edge to triedEdges
                        triedEdges.append(thatEdge)
                        if thatVert not in triedVerts: triedVerts.append(thatVert)
                        #Put next edge in thatEdge
                        nextEdge = [e for e in edges if thatVert in e.vertices and e not in triedEdges]
                        if len(nextEdge) == 1:
                            #This means one edge was found that wasn't already used
                            thatEdge = nextEdge[0]
                        else:
                            #No unused edges were found
                            walking = False

    #                 break
        #at this point, we have found an endpoint
        if debug:
            print("seam endpoint", thisVert)
            print("ending edge", beginEdge.key)
        #get the edge the vert is in
        #for thisEdge in edges:
        return beginEdge, thisVert

    for aVert in verts:
        if aVert not in triedVerts:
            thisEdge, thisVert = findEndpoint(aVert)

    #Now, walk through the edges to put the verts in the right order

    for thisVert in startingVerts:
        thisEdge = [x for x in edges if (thisVert in x.key)][0]
        sortedVerts.append(thisVert)
        keepRunning = True
        while keepRunning:
            for newVert in thisEdge.key:
                if debug: print("next vert is #", newVert)
                if thisVert != newVert:
                    #we have found the other vert if this edge
                    #store it and find the next edge
                    thisVert = newVert
                    sortedVerts.append(thisVert)
                    usedEdges.append(thisEdge)
                    break
            try:
                thisEdge = [x for x in edges if ((thisVert in x.key) and (x not in usedEdges))][0]
            except:
                keepRunning = False
            if debug: print("next vert is in edge", thisEdge.key)




    return sortedVerts



def totalNumberSubdivisions(points, cuts):
    return points + (points - 1)*cuts

mesh_kinds=[
    ("SHEET", "Sheets","Create hair from sheets"),
    ("FIBER", "Fibermesh","Create hair from loose edges"),
    ("CURVE", "Curves","Create hair from curve splines")
]

class HAIRNET_OT_operator (bpy.types.Operator):
    bl_idname = "hairnet.operator"
    bl_label = "HairNet"
    bl_options = {"REGISTER", 'UNDO'}
    bl_description = "Makes hair guides from mesh edges."

    meshKind : EnumProperty(items=mesh_kinds, name="Generator kind", default="FIBER")
    
    targetHead = False
    headObj = 0
    hairObjList = []
    hairProxyList = []
    
    @classmethod
    def poll(self, context):
        return(context.mode == 'OBJECT')

    def execute(self, context):
        debug = False
        error = 0   #0 = All good
                    #1 = Hair guides have different lengths
                    #2 = No seams in hair object
                    #3 = Bevel on curve object

        targetObject = self.headObj

        for thisHairObj in self.hairObjList:
            options = [
                       0,                   #0 the hair system's previous settings
                       thisHairObj,         #1 The hair object
                       0,                   #2 The hair system. So we don't have to rely on the selected system
                       self.targetHead,      #3 Target a head object?
                       targetObject,         #4 targetObject
                       "name"               #5 particle system name
                       ]

            #Get dependency graph
            """depsgraph = bpy.context.evaluated_depsgraph_get()
            thisHairObj = thisHairObj.evaluated_get(depsgraph)
            options[1] = thisHairObj"""
            
            #A new hair object gets a new guides list
            hairGuides = []

            #if not self.targetHead:
            if thisHairObj.hn_cfg.isEmitter:
                targetObject = thisHairObj
                
            #targetObject = targetObject.evaluated_get(depsgraph)

            #targetObject = targetObject.evaluated_get(depsgraph)
            
            config=thisHairObj.hn_cfg
            
            sysName = ''.join(["HN", thisHairObj.name])
            options[5] = sysName

            if sysName in targetObject.particle_systems:
                #if this proxy object has an existing hair system on the target object, preserve its current settings
                if config.masterHairSystem == "":
                    '''_TS Preserve and out'''
                    options[0] = targetObject.particle_systems[sysName].settings
                    options[2] = targetObject.particle_systems[sysName]

                else:
                    '''TS Delete settings, copy, and out'''
                    #Store a link to the system settings so we can delete the settings
                    delSet = targetObject.particle_systems[sysName].settings
                    #Get active_index of desired particle system
                    bpy.context.object.particle_systems.active_index = bpy.context.object.particle_systems.find(sysName)
                    #Delete Particle System
                    removeParticleSystem(targetObject, targetObject.particle_systems[sysName])
                    #Delete Particle System Settings
                    bpy.data.particles.remove(delSet)
                    #Copy Hair settings from master.
                    options[0] = bpy.data.particles[config.masterHairSystem].copy()

                    options[2] = makeNewHairSystem(targetObject,sysName)
            else:
                #Create a new hair system
                if config.masterHairSystem != "":
                    '''T_S copy, create new and out'''
                    options[0] = bpy.data.particles[config.masterHairSystem].copy()
#                     options[2] = self.headObj.particle_systems[sysName]

                '''_T_S create new and out'''
                options[2] = makeNewHairSystem(targetObject,sysName)

            if (self.meshKind=="SHEET"):
                if debug: print("Hair sheet "+ thisHairObj.name)
                #Create all hair guides
                #for hairObj in self.hairObjList:
                #Identify the seams and their vertices
                #Start looking here for multiple mesh problems.
                seamVerts, seamEdges, error = getSeams(thisHairObj)

                if(error == 0):
                    vert_edges = edge_faces = False
                    #For every vert in a seam, get the edge loop spawned by it
                    for thisVert in seamVerts:
                        edgeLoops, vert_edges, edge_faces = getLoops(thisHairObj, thisHairObj.data.vertices[thisVert], vert_edges, edge_faces, seamEdges)
                        '''Is loopsToGuides() adding to the count of guides instead of overwriting?'''
                        hairGuides = self.loopsToGuides(thisHairObj, edgeLoops, hairGuides)
                    if debug: debPrintHairGuides(hairGuides)
                    #Take each edge loop and extract coordinate data from its verts

            if (self.meshKind=="FIBER"):
                hairObj = self.hairObjList[0]
                if debug: print("Hair fiber")
                hairGuides = self.fibersToGuides(hairObj)

            if (self.meshKind=="CURVE"):
                #Preserve Active and selected objects
                tempActive = headObj = bpy.context.object
                tempSelected = []
                tempSelected.append(bpy.context.selected_objects[0])
                tempSelected.append(bpy.context.selected_objects[1])
                #hairObj = bpy.context.selected_objects[0]
                hairObj = thisHairObj
                bpy.ops.object.select_all(action='DESELECT')

                if hairObj.data.bevel_object != None:
                    error = 3


                bpy.context.view_layer.objects.active=hairObj
                hairObj.select_set(state=True)

                if debug: print("Curve Head: ", headObj.name)
                bpy.ops.object.convert(target='MESH', keep_original=True)
                fiberObj = bpy.context.active_object

                if debug:
                    print("Hair Fibers: ", fiberObj.name)
                    print("Hair Curves: ", hairObj.name)

                hairGuides = self.fibersToGuides(fiberObj)

                bpy.ops.object.delete(use_global=False)

                #Restore active object and selection
                bpy.context.view_layer.objects.active=tempActive
                bpy.ops.object.select_all(action='DESELECT')
                for sel in tempSelected:
                    sel.select_set(state=True)
    #            return {'FINISHED'}

            if (self.checkGuides(hairGuides)):
                error = 1

            #Process errors
            if error != 0:
                if error == 1:
                    self.report(type = {'ERROR'}, message = "Mesh guides have different lengths")
                if error == 2:
                    self.report(type = {'ERROR'}, message = ("No seams were defined in " + targetObject.name))
                    removeParticleSystem(targetObject, options[2])
                if error == 3:
                    self.report(type = {'ERROR'}, message = "Cannot create hair from curves with a bevel object")
                return{'CANCELLED'}

            #Subdivide hairs
            hairGuides = self.subdivideGuideHairs(hairGuides, thisHairObj)

            #Create the hair guides on the hair object
            self.createHair(targetObject, hairGuides, options)

        return {'FINISHED'}

    def invoke (self, context, event):

        self.headObj = bpy.context.object

        #Get a list of hair objects
        self.hairObjList = []
        for obj in bpy.context.selected_objects:
            if obj != self.headObj or obj.hn_cfg.isEmitter:
                self.hairObjList.append(obj)


        #if the last object selected is not flagged as a self-emitter, then assume we are creating hair on a head
        #Otherwise, each proxy will grow its own hair

        if not self.headObj.hn_cfg.isEmitter:
            self.targetHead=True
            if len(bpy.context.selected_objects) < 2:
                self.report(type = {'ERROR'}, message = "Selection too small. Please select two objects")
                return {'CANCELLED'}
        else:
            self.targetHead=False




        return self.execute(context)

    def checkGuides(self, hairGuides):
        length = 0
        for guide in hairGuides:
            if length == 0:
                length = len(guide)
            else:
                if length != len(guide):
                    return 1
        return 0

    def createHair(self, ob, guides, options):
        debug = False
        
        tempActive = bpy.context.active_object
        bpy.context.view_layer.objects.active = ob
        
        if debug: print("Active Object: ", bpy.context.active_object.name)

        nGuides = len(guides)
        if debug: print("nGguides", nGuides)
        nSteps = len(guides[0])
        if debug: print("nSteps", nSteps)

        # Create hair particle system if  needed
        #bpy.ops.object.mode_set(mode='OBJECT')
        #bpy.ops.object.particle_system_add()

        psys = options[2]

        # Particle settings
        pset = psys.settings

        if options[0] != 0:
            #Use existing settings
            psys.settings = options[0]
            pset = options[0]
        else:
            #Create new settings
            #pset.type = 'HAIR'
            pset.emit_from = 'FACE'
            ob.show_instancer_for_render = False
            pset.use_strand_primitive = True

            # Children
            pset.child_type = 'SIMPLE'
            pset.child_nbr = 6
            pset.rendered_child_count = 50
            pset.child_length = 1.0
            pset.child_length_threshold = 0.0
            pset.child_radius = 0.1
            pset.child_roundness = 1.0

        #Rename Hair Settings
        #pset.name = ''.join([options[2].name, " Hair Settings"])
        pset.hair_step = nSteps-1
        #This set the number of guides for the particle system. It may have to be the same for every instance of the system.
        pset.count = nGuides

        #Render the emitter object?
        if options[3]:
            ob.show_instancer_for_render = True
        else:
            ob.show_instancer_for_render = False
    
        # Disconnect hair and switch to particle edit mode
        # Connect hair to mesh
        # Segmentation violation during render if this line is absent.
        # Connecting hair moves the mesh points by an amount equal to the object's location

        bpy.ops.particle.particle_edit_toggle()
        bpy.context.scene.tool_settings.particle_edit.tool = 'COMB'
        bpy.ops.particle.brush_edit(stroke=[{'name': '', 'location': (0, 0, 0), 'mouse': (0, 0), 'pressure': 0, 'size': 0, 'pen_flip': False, 'time': 0, 'is_start': False}])
        bpy.ops.particle.particle_edit_toggle()
        bpy.context.scene.tool_settings.particle_edit.use_emitter_deflect = False
        bpy.context.scene.tool_settings.particle_edit.use_preserve_root = False
        bpy.context.scene.tool_settings.particle_edit.use_preserve_length = False

        bpy.ops.particle.disconnect_hair(all=True)
        #Connecting and disconnecting hair causes them to jump when other particle systems are created.
        bpy.ops.particle.connect_hair(all=True)
        
        targetObj = options[4]
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depObj = targetObj.evaluated_get(depsgraph)
        psys = depObj.particle_systems[options[5]]
    
        for m in range(0, nGuides):
            #print("Working on guide #", m)
            nSteps = len(guides[m])
            guide = guides[m]
            part = psys.particles[m]
            part.location = guide[0]

            #print("Guide #", m)
            for n in range(0, nSteps):
                point = guide[n]
                #print("Hair point #", n, ": ", point)
                h = part.hair_keys[n]
                #h.co_local = point
                h.co = point
                #print("h.co = ", h.co)
                
        # Toggle particle edit mode
        bpy.ops.particle.particle_edit_toggle()
        bpy.ops.particle.particle_edit_toggle()
        
        bpy.context.view_layer.objects.active = tempActive
        return

    def createHairGuides(self, obj, edgeLoops):
        hairGuides = []

        #For each loop
        for loop in edgeLoops:
            thisGuide = []
            #For each vert in the loop
            for vert in loop[0]:
                thisGuide.append(obj.data.vertices[vert].co)
            hairGuides.append(thisGuide)

        return hairGuides

    def fibersToGuides(self, hairObj):
        guides = []
        hairs = self.getHairsFromFibers(hairObj)

        for hair in hairs:
            guide = []
            for vertIdx in hair:
                guide.append(hairObj.data.vertices[vertIdx].co.to_tuple())
            guides.append(guide)
        return guides

    def getHairsFromFibers(self, hair):
        me = hair.data
        usedV = []
        usedE = []
        guides = []

        # Create a dictionary with the vert index as key and edge-keys as value
        #It's a list of verts and the keys are the edges the verts belong to
        vert_edges = dict([(v.index, []) for v in me.vertices if v.hide!=1])
        for ed in me.edges:
            for v in ed.key:
                if ed.key[0] in vert_edges and ed.key[1] in vert_edges:
                    vert_edges[v].append(ed.key)

        #endPoints = dict([(v, []) for v in vert_edges if len(vert_edges[v])<2])
        endPoints = [v for v in vert_edges if len(vert_edges[v])<2]

        #For every endpoint
        for vert in endPoints:
                hair=[]
                #print("first endpoint is ", vert)
                #check if EP has been used already in case it was a tail end already
                if vert not in usedV:
                    #lookup the endpoint in vert_edges to get the edge(s) it's in
                    thisEdge = getEdgeFromKey(me,vert_edges[vert][0])
                    #print("Got edge ", thisEdge)
                    #Add the vert to the hair
                    hair.append(vert)
                    #mark the current vert as used
                    #mark the current edge as used
                    usedE.append(thisEdge)
                    usedV.append(vert)
                    #get the next/other vert in the edge
                    #make it the current vert
                    vert = getNextVertInEdge(thisEdge,vert)
                    #print("got next vert ", vert, " edges", vert_edges[vert])
                    #while the number of edges the current vert is  > 1
                    while len(vert_edges[vert])>1:
                        #lookup the endpoint in vert_edges to get the edge(s) it's in
                        thisEdge = getEdgeFromKey(me,vert_edges[vert][0])

                        if thisEdge in usedE:
                            thisEdge = getEdgeFromKey(me,vert_edges[vert][1])
                        #Add the vert to the hair
                        hair.append(vert)
                        #mark the current vert as used
                        #mark the current edge as used
                        usedE.append(thisEdge)
                        usedV.append(vert)
                        #get the next/other vert in the edge
                        #make it the current vert
                        vert = getNextVertInEdge(thisEdge,vert)
                        #print("vert #", vert)
                        #print("edge #", thisEdge)
                        #print(vert_edges[vert])


                    #Add the current vert to the hair
                    hair.append(vert)
                    #mark the current vert as used
                    usedV.append(vert)
                    #add the hair to the list of hairs
                    guides.append(hair)

        #guides now holds a list of hairs where each hair is a list of vertex indices in the mesh "me"
        return guides

    def loopsToGuides(self, obj, edgeLoops, hairGuides):
        guides = hairGuides
        #guides = []

        for loop in edgeLoops:
            hair = []
            #hair is a list of coordinate sets. guides is a list of lists
            for vert in loop[0]:
                #co originally came through as a tuple. Is a Vector better?
                hair.append(obj.data.vertices[vert].co)
    #             hair.append(obj.data.vertices[vert].co.to_tuple())
            guides.append(hair)
        return guides

    def subdivideGuideHairs(self, guides, hairObj):
        debug = True
        #number of points in original guide hair
        hairLength = len(guides[0])

        #original number of hairs
        numberHairs = len(guides)

        #number of hairs added between existing hairs
        hairSprouts = hairObj.hn_cfg.sproutHairs

        #subdivide hairs
        if hairObj.hn_cfg.sproutHairs > 0:
            #initialize an empty array so we don't have to think about inserting entries into lists. Check into this for later?
            newHairs = [[0 for i in range(hairLength)] for j in range(totalNumberSubdivisions(numberHairs, hairSprouts))]
            if debug: print ("Subdivide Hairs")
            newNumber = 1

            #initial condition
            start = guides[0][0]
            newHairs[0][0] = start
    #         debPrintHairGuides(newHairs)
            #for every hair pair, start at the root and send groups of four guide points to the interpolator
            #index identifies which row is current
            #kndex identifies the current hair in the list of new points
            #jndex identifies the current hair in the old list of hairs
            for index in range(0, hairLength):
                if debug: print("Hair Row ", index)
                #add the first hair's points
                newHairs[0][index] = guides[0][index]
                #Make a curve from the points in this row
                thisRow = []
                for aHair in guides:
                    thisRow.append(aHair[index])
                curveObject = makePolyLine("rowCurveObj", "rowCurve", thisRow)
                for jndex in range(0, numberHairs-1):
    #                 knot1 = curveObject.data.splines[0].bezier_points[jndex]
    #                 knot2 = curveObject.data.splines[0].bezier_points[jndex + 1]
                    knot1 = curveObject.splines[0].bezier_points[jndex]
                    knot2 = curveObject.splines[0].bezier_points[jndex + 1]
                    handle1 = knot1.handle_right
                    handle2 = knot2.handle_left
                    newPoints = mathutils.geometry.interpolate_bezier(knot1.co, handle1, handle2, knot2.co, hairSprouts+2)


                    #add new points to the matrix
                    #interpolate_bezier includes the endpoints so, for now, skip over them. re-write later to be a cleaner algorithm
                    for kndex in range(0, len(newPoints)-2):
                        newHairs[1+kndex+jndex*(1+hairSprouts)][index] = newPoints[kndex+1]
    #                     if debug: print("newHairs[", 1+kndex+jndex*(1+hairSprouts), "][", index, "] = ", newPoints[kndex], "SubD")
    #                     newHairs[jndex*(1+hairSprouts)][index] = newPoints[kndex]
    #                     print("knot1 = ", knot1)
    #                     print("knot2 = ", knot2)
    #                     print("newHairs[", 1+kndex+jndex*(1+hairSprouts), "][", index, "] = ", newPoints[kndex])
                        newNumber = newNumber + 1


                    #add the end point
                    newHairs[(jndex+1)*(hairSprouts+1)][index] = guides[jndex+1][index]
    #                 if debug: print("newHairs[", (jndex+1)*(hairSprouts+1), "][", index, "] = ", guides[jndex][index], "Copy")
                    newNumber = newNumber + 1

                #clean up the curve we created
                bpy.data.curves.remove(curveObject)
            if debug:
                print("NewHairs")
                debPrintHairGuides(newHairs)
            guides = newHairs

        return guides

class HAIRNET_PT_panel(bpy.types.Panel):
    bl_idname = "HAIRNET_PT_HairNet"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "particle"
    bl_label = "HairNet " + versionString
    


    def draw(self, context):

        self.headObj = context.object

        #Get a list of hair objects
        self.hairObjList = context.selected_objects
        if self.headObj in self.hairObjList:
            self.hairObjList.remove(self.headObj)

        layout = self.layout

        row = layout.row()
        row.label(text = "Objects Start here")

        #Is this a hair object?

        row = layout.row()
        try:
            row.prop(self.headObj.hn_cfg, 'isEmitter', text = "Emit Hair on Self")
        except:
            pass

        #Draw this if this is a head object
        if not self.headObj.hn_cfg.isEmitter:
            box = layout.box()
            row = box.row()
            row.label(text = "Hair Object:")
            row.label(text = "Master Hair System:")
            for thisHairObject in self.hairObjList:
                row = box.row()
                row.prop_search(thisHairObject.hn_cfg, 'masterHairSystem',  bpy.data, "particles", text = thisHairObject.name)
                row = box.row()
                row.label(text = "Guide Subdivisions:")
                row.prop(thisHairObject.hn_cfg, 'sproutHairs', text = "Subdivide U")
#                 row.prop(thisHairObject, 'hnSubdivideHairSections', text = "Subdivide V")

        #Draw this if it's a self-emitter object
        else:
            box = layout.box()
            try:
                row = box.row()
                row.label(text = "Master Hair System")
                row = box.row()
                row.prop_search(self.headObj.hn_cfg, 'masterHairSystem',  bpy.data, "particles", text = self.headObj.name)

            except:
                pass
            row = box.row()
            row.label(text = "Guide Subdivisions:")
            row.prop(self.headObj.hn_cfg, 'sproutHairs', text = "Subdivide U")


class HAIRNET_PT_view_panel(bpy.types.Panel):
    bl_label = "HairNet"
    bl_idname = "HAIRNET_PT_view_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Hair"
    bl_context = "objectmode"
    bl_options = {"DEFAULT_CLOSED"}
    
    
    def draw(self, context):
        object = context.active_object
        if object is not None:
            self.drawButtons(self.layout)
            self.drawDetails(self.layout, context)
    
    def drawButtons(self, layout):
        col = layout.box().column(align = True)
        
        row = col.row(align = True)
        row.label(text="Make Hair")
        
        row = col.row()
        row.label(text ="Add Hair From:")
        
        row = col.row(align = True)
        for kind in mesh_kinds:
            row = col.row(align = True)
            row.operator("hairnet.operator", text=kind[1]).meshKind=kind[0]
        

    def drawDetails(self, layout, context):
        self.headObj = context.object


        #Get a list of hair objects
        self.hairObjList = context.selected_objects
        if self.headObj in self.hairObjList:
            self.hairObjList.remove(self.headObj)

        layout = self.layout

        row = layout.row()
        #row.label(text = "Objects Start here")

        '''Is this a hair object?'''

        row = layout.row()
        try:
            row.prop(self.headObj.hn_cfg, 'isEmitter', text = "Emit Hair on Self")
        except:
            pass

        #Draw this if this is a head object
        if not self.headObj.hn_cfg.isEmitter:
            box = layout.box()
            row = box.row()
            row.label(text = "Hair Object:")
            row.label(text = "Use Settings:")
            for thisHairObject in self.hairObjList:
                config=thisHairObject.hn_cfg
                row = box.row()
                row.prop_search(config, 'masterHairSystem',  bpy.data, "particles", text = thisHairObject.name)
                row = box.row()
                row.label(text = "Add Guides:")
                row.prop(config, 'sproutHairs', text = "SubD")
#                 row.prop(thisHairObject, 'hnSubdivideHairSections', text = "Subdivide V")

        #Draw this if it's a self-emitter object
        else:
            box = layout.box()
            try:
                row = box.row()
                row.label(text = "Use Settings")
                
                row = box.row()
                row.prop_search(self.headObj.hn_cfg, 'masterHairSystem',  bpy.data, "particles", text = self.headObj.name)

            except:
                pass
            row = box.row()
            row.label(text = "Guide Subdivisions:")
            row.prop(self.headObj.hn_cfg, 'sproutHairs', text = "SubD")



classes = (
    HAIRNET_OT_operator, 
    HAIRNET_PT_panel, 
    HAIRNET_PT_view_panel,
    HairNetConfig,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Object.hn_cfg=PointerProperty(type=HairNetConfig)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == '__main__':
    register()
