# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
        "name":"hairNet",
        "author": "Rhett Jackson",
        "version": (0,6,5),
        "blender": (2,90,0),
        "location": "Properties",
        "category": "Particle",
        "description": "Creates a particle hair system with hair guides from mesh edges which start at marked seams.",
        "wiki_url": "http://wiki.blender.org/index.php?title=Extensions:2.6/Py/Scripts/Objects/HairNet",
        "tracker_url":"http://projects.blender.org/tracker/index.php?func=detail&aid=35062&group_id=153&atid=467"
        }


if "bpy" in locals():
    import importlib
    importlib.reload(hairNet)
    importlib.reload(import_properties)
else:
    from . import hairNet
    from . import import_properties

import bpy


# ### REGISTER ###



def register():
	hairNet.register()
	#import_properties.register()


def unregister():
	hairNet.unregister()
	#import_properties.unregister()

if __name__ == "__main__":
    register()
