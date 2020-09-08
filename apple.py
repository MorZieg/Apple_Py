###########################################################################################
# Apple PY - Automatic Portioning Preventing Lengthy manual Element assignment for PYthon #
# Version 1.02																		      #
# License: GPLv3																	      #
# Moritz O. Ziegler - mziegler@gfz-potsdam.de, Malte Ziebarth, Karsten Reiter		      #
# Manual: http://doi.org/10.2312/wsm.2019.001										      #
# Download: http://github.com/MorZieg/APPLE_PY										      #
###########################################################################################
import numpy as np, scipy.spatial as sp, collections

#### USER INPUT ###
# ATTENTION! If you are working with only one unit/element set in the variable strata or
# elems_exclude use either:
# squared brackets, e.g. elems_exclude = ['disregarded_unit']
# or
# append a comma after the string, e.g. elems_exclude = ('disegarded_unit',)

geometry = 'test.inp'
horizons = 'horizons.txt'
strata = ('Unit_1','Unit_2','Unit_3','Unit_4','Unit_5','Unit_6')
twodelem = 'omit'
fname = 'elements.set'
#elems_exclude = ()

###########################################################################################
def main(geometry,horizons,strata,twodelem,fname,elems_exclude):
#### READING GEOMETRY ####
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
			if 'elems_exclude' in locals():
				if  any(s == naun[0] for s in elems_exclude):
					print 'ATTENTION! %s: Not loaded (user-defined)' % naun[0]
					line = fid.readline()
					continue
			# Exclude 2D elements on request
			pos = line.find('TYPE=')
			if twodelem == 'omit' and ( line[(pos+5):(pos+7)] == 'S3' or line[(pos+5):(pos+7)] == 'S4' ):
				print 'ATTENTION! %s: Not loaded (2D elements)' % naun[0]
				line = fid.readline()
			else:
				[elems, line] = elemarray(fid)
				elements.append(elems)
				print '%s: Elements loaded' % naun[0]
		else:
			line = fid.readline()
	fid.close()
	
	# Combine all element sets/components/element tyypes into a single variable.
	els = []
	for i in range(len(elements)):
		for j in range(len(elements[i])):
			els.append(elements[i][j])
	els = np.asarray(els)
	nod = np.asarray(nodes)
	
	print '%d nodes loaded.' % len(nodes)
	print '%d elements loaded.' % len(els)
	
	# Read the depth of the horizons at different locations
	ungeom = []
	with open(horizons,'r') as f:
		ungeom = [[float(x) for x in line.split(', ')] for line in f]
	ungeom = np.asarray(ungeom)
	
	if ( len(ungeom[1,:]) - 1) != len(strata):
		print 'ERROR! Number of horizons mismatch!'
		return
	else:
		print '%d gridpoints loaded from horizons file.' % len(ungeom)
		print ' '
		
	#### ASSIGN ELEMENTS TO ROCK UNITS ####	
	# Find the closest vertical line for each node by a nearest-neighbour function
	xynodes = nod[:,1:3]
	node_ungeom = np.empty([len(nod[:,0]),3])
	
	tree = sp.cKDTree(ungeom[:,0:2])
	x, ind = tree.query(xynodes,k=1)
	
	# Create a variable that contains the node number, the node depth (z-comnponent), and the number of the closest vertical profile.
	node_ungeom[:,0] = nod[:,0]
	node_ungeom[:,1] = nod[:,3]
	node_ungeom[:,2] = ind
	
	print 'All vertical profiles assigned to nodes.'
	print ' '
	
	# Create a dictionary to look up the nodes and the corresponding vertical profile.
	dict = {node_ungeom[0,0]:0}
	for i in range(len(node_ungeom[:,0])):
		dict.update({node_ungeom[i,0]:i})
	
	# Iterate over elements
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
		
		if (i/10000.).is_integer():
			print '%d vertical profiles and mean depths assigned.' % i
	print 'All vertical profiles assigned to elements and mean depths computed.'
	print ' '
	
	
	depth = np.asarray(ungeom[:,2:])
	elsets = []
	# Create a collector for each rock unit.
	for _ in range(len(strata)):
		elsets.append([])
	
	# Assign each element to a unit.
	for i, elem in enumerate(elem_mdepth_ungeom):
		ind = assign_elems(depth[int(elem[2])],elem)
		elsets[ind].append(elem[0])
		if (i/100000.).is_integer():
			print '%d elements assigned to units' % i
	print 'All elements assigned to units'
	print ' '
	
	# Write element sets to a new set file.
	print 'Writing elements set'
	fid = open(fname, 'w')
	for i, n in enumerate(strata):
		fid.write('*ELSET, ELSET=%s_new\n\t' % n)
		for j, el in enumerate(elsets[i]):
			fid.write('%d, ' % el)
			if ((j+1)/9.).is_integer():
				fid.seek(-1,1)
				fid.truncate()
				fid.write('\n\t')
		fid.seek(-2,1)
		fid.truncate()
		fid.write('\n')
	fid.write('*****')
	fid.close()
	print ' '
	print 'APPLE PY successfully completed'
	print ' '	
	
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
def assign_elems(depth,elem):
	# Assign an element to a unit. Returns the number of the unit. 0 relates to the topmost unit.
	i = 0
	while (elem[1] < depth[i]) or (depth[i] == 9999):
		i += 1
		if i == len(depth):
			break
	return i

###########################################################################################
if __name__ == '__main__':
	if 'elems_exclude' not in locals():
		elems_exclude = ()
	main(geometry,horizons,strata,twodelem,fname,elems_exclude)
###########################################################################################