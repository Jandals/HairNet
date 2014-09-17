#---------------------------------------------------
# File HairNet.py
# Written by Rhett Jackson April 1, 2013
# Some routines were copied from "Curve Loop" by Crouch https://sites.google.com/site/bartiuscrouch/scripts/curveloop
# Some routines were copied from other sources
# Very limited at this time:
# NB 1) After running the script to create hair, the user MUST manually enter Particle Mode on the Head object and "touch" each point of each hair guide. Using a large comb brish with very low strength is a good way to do this. If it's not done, the hair strands are likely to be reset to a default/straight-out position during editing.
# NB 2) All meshes must have the same number of vertices in the direction that corresponds to hair growth
#---------------------------------------------------

bl_info = {
        "name":"HairNet",
        "author": "Rhett Jackson",
        "version": (0,4,7),
        "blender": (2,6,7),
        "location": "Properties",
        "category": "Particle",
        "description": "Creates a particle hair system with hair guides from mesh edges which start at marked seams.",
        "wiki_url": "http://wiki.blender.org/index.php?title=Extensions:2.6/Py/Scripts/Objects/HairNet",
        "tracker_url":"http://projects.blender.org/tracker/index.php?func=detail&aid=35062&group_id=153&atid=467"
        }

import bpy
from bpy.utils import register_module, unregister_module
from bpy.props import StringProperty

def debPrintVertEdges(vert_edges):
    print("vert_edges: ")
    for vert in vert_edges:
        print(vert, ": ", vert_edges[vert])
        
def debPrintEdgeFaces(edge_faces):
    print("edge_faces: ")
    for edge in edge_faces:
        print(edge, ": ", edge_faces[edge])
        
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
        print(edge.index)
        
def getEdgeFromKey(mesh,key):
    v1 = key[0]
    v2 = key[1]
    theEdge = 0
    for edge in mesh.edges:
        if v1 in edge.vertices and v2 in edge.vertices:
            #print("Found edge :", edge.index)
            return edge
    return 0

def debPrintLoc(func=""):
    obj = bpy.context.object
    print(obj.name, " ", func)
    print("Coords", obj.data.vertices[0].co)
 
def createHair(ob, guides, options):
    
    tempActive = bpy.context.scene.objects.active
    bpy.context.scene.objects.active = ob
    
    nGuides = len(guides)
    #print("nGguides", nGuides)
    nSteps = len(guides[0])
    #print("nSteps", nSteps)
    
    # Create hair particle system if  needed
    #bpy.ops.object.mode_set(mode='OBJECT')
    #bpy.ops.object.particle_system_add()
    '''
    psys = ob.particle_systems.active
    '''
    psys = options[2]
    #psys.name = 'HairNet System'
 
    # Particle settings
    pset = psys.settings
    
    if options[0] != 0:
        psys.settings = options[0]
    else:
        
        pset.type = 'HAIR'
        pset.name = ''.join([options[1].name, " Hair Settings"]) 
   
        pset.emit_from = 'FACE'
        pset.use_render_emitter = True
        pset.use_strand_primitive = True
     
        # Children
        pset.child_type = 'SIMPLE'
        pset.child_nbr = 6
        pset.rendered_child_count = 50
        pset.child_length = 1.0
        pset.child_length_threshold = 0.0
        pset.child_radius = 0.1
        pset.child_roundness = 1.0
        
    pset.hair_step = nSteps-1
    #This set the number of guides for the particle system. It may have to be the same for every instance of the system.
    pset.count = nGuides
 
    # Disconnect hair and switch to particle edit mode
    '''
    '''
    #bpy.ops.particle.disconnect_hair(all=True)
    


    
    # Set all hair-keys
    dt = 100.0/(nSteps-1)
    dw = 1.0/(nSteps-1)  

    # Connect hair to mesh
    # Segmentation violation during render if this line is absent.
    # Connecting hair moves the mesh points by an amount equal to the object's location

    bpy.ops.particle.particle_edit_toggle()
    
    #Connecting and disconnecting hair causes them to jump when other particle systems are created.
    #bpy.ops.particle.connect_hair(all=True)

    for m in range(nGuides):
        #print("Working on guide #", m)
        nSteps = len(guides[m])
        guide = guides[m]
        part = psys.particles[m]
        bpy.context.scene.tool_settings.particle_edit.use_preserve_root = False
        part.location = guide[0]
        #bpy.context.scene.tool_settings.particle_edit.use_preserve_root = True
        bpy.context.scene.tool_settings.particle_edit.use_preserve_length = False
        #print("Guide #", m)
        for n in range(0, nSteps):
            point = guide[n]
            #print("Hair point #", n, ": ", point)
            h = part.hair_keys[n]
            #h.co_local = point
            h.co = point
            h.time = n*dt
            h.weight = 1.0 - n*dw
    
    # Toggle particle edit mode
    
    bpy.ops.particle.particle_edit_toggle()

    # Unfortunately, here a manual step appears to be needed:
    # 1. Toggle to particle mode
    # 2. Touch object with a brush
    # 3. Toggle to object mode
    # 4. Toggle to edit mode
    # 5. Toggle to object mode
    # This should correspond to the code below, but fails due to
    # wrong context
    '''
    bpy.ops.particle.particle_edit_toggle()
    bpy.ops.particle.brush_edit()
    bpy.ops.particle.particle_edit_toggle()
    bpy.ops.object.editmode_toggle()
    bpy.ops.object.editmode_toggle()
    '''
    bpy.context.scene.objects.active = tempActive
    return

def sortLoop(obj, vloop, v1, seamEdges, vert_edges):
    #The hair is either forward or reversed. If it's reversed, reverse it again. Otherwise do nothing.
    loop = []
    loopRange = len(vloop)-1
    
    if vloop[0] == v1.index:
        loop = vloop.copy()
        
    else:
        loop = vloop[::-1]
    return loop

def getHairsFromFibers(hair):
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

    
# Hair guides. Four hair with five points each.
def createHairGuides(obj, edgeLoops):
    hairGuides = []
    
    #For each loop
    for loop in edgeLoops:
        thisGuide = []
        #For each vert in the loop
        for vert in loop[0]:
            thisGuide.append(obj.data.vertices[vert].co)
        hairGuides.append(thisGuide)
    
    return hairGuides    

def getSeams(obj):
    debug = False
    #Make a list of all edges marked as seams
    error = 0
    seamEdges = []
    for edge in obj.data.edges:
        if edge.use_seam:
            seamEdges.append(edge)
    #Make a list of all verts in the seam
    seamVerts = []
    for edge in seamEdges:
        for vert in edge.vertices:
            if vert not in seamVerts:
                seamVerts.append(vert)
                
    if debug: debPrintSeams(seamVerts, seamEdges)
    
    if(len(seamEdges) == 0):
        error = 2
    
    return seamVerts, seamEdges, error

def getNextVertInEdge(edge, vert):
    if vert == edge.vertices[0]:
        return edge.vertices[1]
    else:
        return edge.vertices[0]
    

def loopsToGuides(obj, edgeLoops, hairGuides):
    guides = hairGuides
    #guides = []
    
    for loop in edgeLoops:
        hair = [] 
        #hair is a list of coordinate sets. guides is a list of lists
        for vert in loop[0]:
            
            hair.append(obj.data.vertices[vert].co.to_tuple())
        guides.append(hair)
    return guides

def fibersToGuides(hairObj):
    guides = []
    hairs = getHairsFromFibers(hairObj)
    
    for hair in hairs:
        guide = []
        for vertIdx in hair:
            guide.append(hairObj.data.vertices[vertIdx].co.to_tuple())
        guides.append(guide)
    return guides
        

def checkGuides(hairGuides):
    length = 0
    for guide in hairGuides:
        if length == 0:
            length = len(guide)
        else:
            if length != len(guide):
                return 1
    return 0
        

class HairNet (bpy.types.Operator):
    bl_idname = "particle.hairnet"
    bl_label = "HairNet"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Makes hair guides from mesh edges."
    
    meshKind = StringProperty()
    
    headObj = 0
    hairObjList = []
    
    @classmethod
    def poll(self, context):
        return(context.mode == 'OBJECT')
    
    
    def execute(self, context):
        
        
        
        error = 0   #0 = All good
                    #1 = Hair guides have different lengths
                    #2 = No seams in hair object
        for thisHairObj in self.hairObjList:            
            options = [
                       0,                   #0 the hair system's previous settings
                       thisHairObj, #1 The hair object
                       0                    #2 The hair system. So we don't have to rely on the selected system
                       ]
            #A new hair object gets a new guides list
            hairGuides = []
            
            print("******Start Here*******")
            sysName = ''.join(["HN", thisHairObj.name])
            #Get the head object. It's the last one selected
            #headObj = bpy.context.object
            
            #Preserve hair settings if they exist. Else create a new hair system
            if sysName in self.headObj.particle_systems:
                options[0] = self.headObj.particle_systems[sysName].settings
                options[2] = self.headObj.particle_systems[sysName]
                '''
                if sysName != self.headObj.particle_systems.active.name:
                    self.report(type = {'ERROR'}, message = "The selected particle system does not match the selected hair object.")
                    return{'CANCELLED'}
                '''
            else:
                bpy.ops.object.mode_set(mode='OBJECT')
                #bpy.ops.object.particle_system_remove()
                bpy.ops.object.particle_system_add()
                self.headObj.particle_systems.active.name = sysName
                options[2] = self.headObj.particle_systems.active
            
                
            psys = self.headObj.particle_systems[sysName]
            psys.name = sysName
            
            if (self.meshKind=="SHEET"):
                print("Hair sheet")
                #Create all hair guides
                #for hairObj in self.hairObjList:
                #Identify the seams and their vertices
                seamVerts, seamEdges, error = getSeams(thisHairObj)
            
                vert_edges = edge_faces = False
                #For every vert in a seam, get the edge loop spawned by it
                for thisVert in seamVerts:
                    edgeLoops, vert_edges, edge_faces = getLoops(thisHairObj, thisHairObj.data.vertices[thisVert], vert_edges, edge_faces, seamEdges)
                    '''Is loopsToGuides() adding to the count of guides instead of overwriting?'''
                    hairGuides = loopsToGuides(thisHairObj, edgeLoops, hairGuides)
                #debPrintHairGuides(hairGuides)
                #Take each edge loop and extract coordinate data from its verts
                #hairGuides = createHairGuides(hairObj, edgeLoops)
                
            if (self.meshKind=="FIBER"):
                hairObj = self.hairObjList[0]
                print("Hair fiber")
                #fibers = getHairsFromFibers(hairObj)
                hairGuides = fibersToGuides(hairObj)
            
            if (self.meshKind=="CURVE"):
                #Preserve Active and selected objects
                tempActive = headObj = bpy.context.object
                tempSelected = []
                tempSelected.append(bpy.context.selected_objects[0])
                tempSelected.append(bpy.context.selected_objects[1])
                hairObj = bpy.context.selected_objects[0]
                bpy.ops.object.select_all(action='DESELECT')
                
                if hairObj.data.bevel_object != None:
                    error = 3
                    
                
                bpy.context.scene.objects.active=hairObj
                hairObj.select=True
                
                print("Curve Head: ", headObj.name)
                bpy.ops.object.convert(target='MESH', keep_original=True)
                fiberObj = bpy.context.active_object
                            
                print("Hair Fibers: ", fiberObj.name)
                print("Hair Curves: ", hairObj.name)
                
                hairGuides = fibersToGuides(fiberObj)
                
                bpy.ops.object.delete(use_global=False)
                
                #Restore active object and selection
                bpy.context.scene.objects.active=tempActive
                bpy.ops.object.select_all(action='DESELECT')
                for sel in tempSelected:
                    sel.select = True
    #            return {'FINISHED'}
                
            if (checkGuides(hairGuides)):
                error = 1
            
            #Process errors
            if error != 0:
                if error == 1:
                    self.report(type = {'ERROR'}, message = "Mesh guides have different lengths")
                if error == 2:
                    self.report(type = {'ERROR'}, message = "No seams were defined")
                if error == 3:
                    self.report(type = {'ERROR'}, message = "Cannot create hair from curves with a bevel object")
                return{'CANCELLED'}
            
            #debPrintLoc(func="Execute 2")
        
            #Create the hair guides on the hair object
            createHair(self.headObj, hairGuides, options)
       
        #debPrintLoc(func="Execute 3")
        return {'FINISHED'}
    
    def invoke (self, context, event):
        
        if len(bpy.context.selected_objects) < 2:
            self.report(type = {'ERROR'}, message = "Selection too small. Please select two objects")
            return {'CANCELLED'}
#         elif len(bpy.context.selected_objects) > 2:
#             self.report(type = {'ERROR'}, message = "Selection too large. Please select two objects")
#             return {'CANCELLED'}
        
        self.headObj = bpy.context.object
        
        #Get a list of hair objects
        self.hairObjList = bpy.context.selected_objects
        self.hairObjList.remove(self.headObj)
        
        return self.execute(context)
        
class HairNetPanel(bpy.types.Panel):
    bl_idname = "PARTICLE_PT_HairNet"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "particle"
    bl_label = "HairNet 0.4.7"

    def draw(self, context):
        obj = context.object
        layout = self.layout
            
        layout.label("HairNet")
        
        layout.operator("particle.hairnet", text="Add Hair From Sheets").meshKind="SHEET"
        layout.operator("particle.hairnet", text="Add Hair From Fibers").meshKind="FIBER"
        layout.operator("particle.hairnet", text="Add Hair From Curves").meshKind="CURVE"
        
    
def register():
    unregister_module(__name__)
    register_module(__name__)
    
    

def unregister():
    unregister_module(__name__)
    
if __name__ == '__main__':
    register()