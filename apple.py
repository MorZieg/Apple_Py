###########################################################################################
# Apple PY - Automatic Portioning Preventing Lengthy manual Element assignment for PYthon #
# Version 1.3                                                                             #
# License: GPLv3                                                                          #
# Moritz O. Ziegler - mziegler@gfz-potsdam.de, Malte Ziebarth, Karsten Reiter             #
# Manual: http://doi.org/10.2312/wsm.2020.002                                             #
# Download: http://github.com/MorZieg/APPLE_PY                                            #
###########################################################################################
import numpy as np, scipy.spatial as sp, collections

#### USER INPUT ###
geometry = 'simple.inp'
horizons = ['simple.txt']
strata = ['dark_blue','green','yellow','light_blue','pink']
twodelem = 'yes'
fname = 'simple_units_elements.set'
# distrib = 'normal'
# elems_exclude = []

###########################################################################################
def main(geometry,horizons,strata,twodelem,fname,distrib=None,elems_exclude=None):
  # Input check
  #input_check(horizons,strata,distrib)
  
  print('Running Apple PY v1.3')
  
  # Read the nodes and elements from the geometry file.
  [nodes,elements] = read_geom(geometry,twodelem,elems_exclude)
  
  # Transfer nodes and elememts into a single set.
  els = node_elem_var(nodes,elements)
  
  # Create a collector for each rock unit.
  elsets = []
  for _ in range(len(strata)):
    elsets.append([])
  
  # Assign elements to a unit.
  if len(horizons) == 1:
    elsets = single_horizon_file(horizons,nodes,els,elsets,distrib)
  else:
    elsets = multiple_horizon_files(horizons,nodes,els,elsets,distrib)
  
  print(' ')
  print('All elements assigned to units')
  
  # Write element set output file
  write_set_file(fname,strata,elsets)
  
  print('APPLE PY successfully completed')
  
###########################################################################################
###########################################################################################
def read_geom(geometry,twodelem,elems_exclude):
  
  # Read nodes and elements from geometry file in Abaqus format.
  fid = open(geometry,'r')
  line = fid.readline()
  elements = []
  
  while True:
    if line[0:5] == '*****': # Indicates the end of the input file.
      break
    elif line[0:5] == '*NODE':
      (nodes, line) = nodearray(fid)
    elif line[0:5] == '*ELEM':
      # Exclude user-defined units
      naun = line[(line.find('ELSET=')+6):-1]
      naun = naun.split()
      if elems_exclude is not None:
        if  any(s == naun[0] for s in elems_exclude):
          print('ATTENTION! %s: Not loaded (user-defined)' % naun[0])
          line = fid.readline()
          continue
      # Exclude 2D elements on request
      pos = line.find('TYPE=')
      if twodelem == 'omit' and ( line[(pos+5):(pos+7)] == 'S3' or line[(pos+5):(pos+7)] == 'S4' ):
        print('ATTENTION! %s: Not loaded (2D elements)' % naun[0])
        line = fid.readline()
      else:
        [elems, line] = elemarray(fid)
        elements.append(elems)
        print('%s: Elements loaded' % naun[0])
    else:
      line = fid.readline()
  fid.close()
  
  return [nodes,elements]
  
###########################################################################################
def node_elem_var(nodes,elements):
  # Combine all element sets/components/element types into a single variable.
  els = []
  for i in range(len(elements)):
    for j in range(len(elements[i])):
      els.append(elements[i][j])
  
  print('%d nodes loaded.' % len(nodes))
  print('%d elements loaded.' % len(els))
  
  return els
  
###########################################################################################
def single_horizon_file(horizons,nodes,els,elsets,distrib):
  
  # Read the depth of the horizons at different locations
  ungeom = read_horizon_depth(horizons[0])
  
  if distrib is not None:
    # Estimation of horizon depths from mean and standard deviation.
    ungeom = mean_sd(ungeom,distrib)
  
  # Assign nodes to vertical lines.
  node_ungeom = node2vertline(np.asarray(ungeom),nodes)
    
  # Assign elements to vertical lines.
  elem_mdepth_ungeom = elem2vertline(els,node_ungeom)
  
  # Assign each element to a unit.
  for i, elem in enumerate(elem_mdepth_ungeom):
    depth = ungeom[int(elem[2])][2:]
    ind = assign_elems(depth,elem)
    elsets[ind].append(elem[0])
  
  return elsets
  
###########################################################################################
def multiple_horizon_files(horizons,nodes,els,elsets,distrib):
  import numpy as np
  
  topunit = 0
  # Iterate over the number of provided horizon files.
  for i in range(len(horizons)):
    print(' ')
    print('Horizon file: %s' % horizons[i])
    
    # Read the depth of the horizons at different locations
    ungeom = read_horizon_depth(horizons[i])
    
    if distrib is not None:
      # Estimation of horizon depths from mean and standard deviation.
      ungeom = mean_sd(ungeom,distrib)
    
    # Assign nodes to vertical lines.
    node_ungeom = node2vertline(np.asarray(ungeom),nodes)
    
    # Assign elements to vertical lines.
    elem_mdepth_ungeom = elem2vertline(els,node_ungeom)
    
    # Assign each element to a unit.
    assigned = []
    for i, elem in enumerate(elem_mdepth_ungeom):
      depth = ungeom[int(elem[2])][2:]
      ind = assign_elems(depth,elem)
      ind += topunit
      if ind != len(depth) + topunit:
        elsets[ind].append(elem[0])
        assigned.append(i)
          
    topunit += len(depth)
    
    for i in range(len(assigned)-1,-1,-1):
      del els[assigned[i]]
  
  for i,elem in enumerate(els):
    elsets[topunit].append(elem[0])
  
  return elsets
  
###########################################################################################
def write_set_file(fname,strata,elsets):
  # Write element sets to a new set file.
  import os
  
  fid = open(fname, 'w')
  fid.write('** Element sets created by APPLE PY v1.3\n** http://github.com/MorZieg/APPLE_PY\n**\n')
  for i, n in enumerate(strata):
    fid.write('*ELSET, ELSET=%s_new\n\t' % n)
    for j, el in enumerate(elsets[i]):
      fid.write('%d, ' % el)
      if ((j+1)/8.).is_integer():
        fid.seek(fid.tell() - 1, os.SEEK_SET)
        fid.truncate()
        fid.write('\n\t')
      
    fid.seek(fid.tell() - 2, os.SEEK_SET)
    fid.truncate()
    fid.write('\n')
  
  fid.write('*****')
  fid.close()
  
  print('Element sets written to file.')
  
###########################################################################################
###########################################################################################
def nodearray(fid):
  # Function that reads the nodes from an Abaqus input file.
  nodes = [[]]
  num = 0
  while True:
    line = fid.readline()
    if line[0] == '*':
      break
    elif num != 0:
      nodes.append([])
    line = str.replace(line,',',' ')
    line = str.split(line)
    for i in range(4):
      nodes[num].append(float(line[i]))
    num += 1
  return nodes, line

###########################################################################################
def elemarray(fid):
  #Function to read the elements from an Abaqus input file.
  elems = [[]]
  num = 0
  line = fid.readline()
  while True:
    # If a new command line starts: break
    if line[0] == '*':
      break
    # If a new element starts and the line is not a command line and not the first line
    elif num != 0:
      elems.append([])
    # If the element definition ends at the end of the line there is no 'comma'
    eol = ','
    while eol == ',':
      eol = str.split(line)[-1][-1]
      line = str.replace(line,',',' ')
      line = str.split(line)
      for i in range(len(line)):
        elems[num].append(float(line[i]))
      line = fid.readline()
    num += 1
  return elems, line
  
###########################################################################################
def read_horizon_depth(horizon):
  # Read the depth of the horizons at different locations
  ungeom = []
  
  with open(horizon,'r') as f:
    line = f.readline()
    while line.split() != []:
      ungeom.append([float(x) for x in line.split(',')])
      line = f.readline()
    
  print('%d gridpoints loaded from horizons file %s.' % (len(ungeom),horizon))
  
  return ungeom
  
###########################################################################################
def mean_sd(ungeom,distrib):
  # The mean depths and a standard deviation are used to estimate the horizon depth.
  import numpy as np
  
  num_horz = int((len(ungeom[0]) - 2) / 2)
  out = []
  
  for i in range(len(ungeom)):
    temp = [ungeom[i][0],ungeom[i][1]]
    
    for j in range(2,2*num_horz+2,2):
      if distrib == 'normal':
        temp.append(np.random.normal(ungeom[i][j],ungeom[i][j+1]))
        
      elif distrib == 'uniform':
        temp.append(np.random.uniform(ungeom[i][j],ungeom[i][j+1]))
        
      elif distrib == 'mean_depth':
        temp.append(ungeom[i][j])
        
    out.append(temp)
  
  print('Horizon depths estimated from %s distribution.' % distrib)
  
  return out
  
###########################################################################################
def node2vertline(horde,nodes):
  # Find the closest vertical line for each used node by a nearest-neighbour function
  nod =np.asarray(nodes)
  xynodes = nod[:,1:3]
  node_horde = np.empty([len(nod[:,0]),3])
  
  tree = sp.cKDTree(horde[:,0:2])
  x, ind = tree.query(xynodes,k=1)
  
  # Create a variable that contains the node number, the node depth (z-comnponent), and the number of the closest vertical profile.
  node_horde[:,0] = nod[:,0]
  node_horde[:,1] = nod[:,3]
  node_horde[:,2] = ind
  
  return node_horde
  
###########################################################################################
def elem2vertline(els,node_ungeom):
  # Find the vertical line that is most representative for each element.
  import numpy as np
  
  # Create a dictionary to look up the nodes and the corresponding vertical profile.
  dict = {node_ungeom[0,0]:0}
  for i in range(len(node_ungeom[:,0])):
    dict.update({node_ungeom[i,0]:i})
  
  # Iterate over elements.
  elem_mean_depth = []
  elem_ungeom = []
  elem_mdepth_ungeom = []
  for i in range(len(els)):
    single_depth = []
    ungeom_points = []
    for node in els[i][1:]:
      # For each element each constituting node is queried for its depth and the associated vertical profile.
      ind = dict[node]    
      single_depth.append(node_ungeom[ind,1])
      ungeom_points.append(float(node_ungeom[ind,2]))
    # Compute mean depth of each element by the mean depth of the associated nodes and find the preferred vertical line for an element by the vertical line that is most often assigned to a node of the element.
    x = collections.Counter(ungeom_points)
    elem_mdepth_ungeom.append([els[i][0], np.mean(single_depth), x.most_common()[0][0]])
  
  print('Elements assigned to vertical line.')
  
  return elem_mdepth_ungeom
  
###########################################################################################
def assign_elems(depth,elem):
  # Assign an element to a unit. Returns the number of the unit. 0 relates to the topmost unit.
  i = 0
  while (elem[1] < depth[i]) or (depth[i] == 9999):
    i += 1
    if i == len(depth):
      break
  return i
  
###########################################################################################
def input_check(horizons,strata,distrib):
  import sys
  
  # Is the distribution type supported?
  if distrib is not None:
    if (distrib != 'normal') and (distrib != 'uniform') and (distrib != 'mean_depth'):
      print('ERROR! Distribution type not supported.')
      sys.exit()
  
  # Are enough units specified?
  expected_units = 0
  for i in range(len(horizons)):
    with open(horizons[i]) as fid:
      first_line = fid.readline()
      expected_units += (len([float(x) for x in first_line.split(', ')]) - 2)
  
  if distrib is not None and int(expected_units/2) + 1 != int(len(strata)):
    print('ERROR! Number of units and horizons mismatch.')
    print('Did you provide a standard deviation?')
    sys.exit()
    
  if distrib is None and expected_units + 1 != len(strata):
    print('ERROR! Number of units and horizons mismatch.')
    print('Did you provide a standard deviation?')
    sys.exit()
    
###########################################################################################
if __name__ == '__main__':
  if 'elems_exclude' not in locals():
    elems_exclude = None
  if 'distrib' not in locals():
    distrib = None
  main(geometry,horizons,strata,twodelem,fname,distrib,elems_exclude)
###########################################################################################