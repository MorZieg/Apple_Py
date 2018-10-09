#### APPLE PY - Automatic Portioning Preventing Lengthy manual Element assignment for PYthon
#### Version 0.9
#### Copyright: Moritz Ziegler - mziegler@gfz-potsdam.de
def main():
	import numpy as np, collections
	
	#### USER INPUT ###
	geometry = 'mixed_elems.inp'
	horizons = 'mixed.txt'
	strata = ('Unit_1','Unit_2','Unit_3','Unit_4','Unit_5')
	twodelem = 'no'
	#unit_exclude = [[]]
	
	
	#### READING GEOMETRY ####
	# Read nodes and elements from geometry file in Abaqus format.
	fid = open(geometry,'r')
	line = fid.readline()
	elements = []
	
	while True:
		if line[0:5] == '*****':
			break
		elif line[0:5] == '*NODE':
			(nodes, line) = nodearray(fid)
		elif line[0:5] == '*ELEM':
			# Exclude user-defined units
			naun = line[(line.find('ELSET=')+6):-1]
			naun = naun.split()
			if 'unit_exclude' in locals():
				if  any(s == naun for s in unit_exclude):
					print 'ATTENTION! %s: Not loaded (user-defined)' % naun[0]
					line = fid.readline()
					continue
			# Exclude 2D elements on request
			pos = line.find('TYPE=')
			if twodelem == 'no' and ( line[(pos+5):(pos+7)] == 'S3' or line[(pos+5):(pos+7)] == 'S4' ):
				print 'ATTENTION! %s: Not loaded (2D elements)' % naun[0]
				line = fid.readline()
			else:
				[elems, line] = elemarray(fid)
				elements.append(elems)
				print '%s: Elements loaded' % naun[0]
		else:
			line = fid.readline()
	fid.close()
	
	els = []
	for i in range(len(elements)):
		for j in range(len(elements[i])):
			els.append(elements[i][j])
	els = np.asarray(els)
	nod = np.asarray(nodes)
	
	# Read the depth of the hoizons at different locations
	ungeom = []
	with open(horizons,'r') as f:
		ungeom = [[float(x) for x in line.split(', ')] for line in f]
	ungeom = np.asarray(ungeom)
	
	if ( len(ungeom[1,:]) - 1) != len(strata):
		print 'ERROR! Number of horizons mismatch!'
		return
	
	#### ASSIGN ELEMENTS TO ROCK UNITS ####
	# Find the closest vertical line for each node
	xynodes = nod[:,1:3]
	node_ungeom = []
	for i in range(len(nod)):
		dist_2 = np.sum((ungeom[:,0:2] - xynodes[i,:])**2, axis=1)
		node_ungeom.append([nod[i,0], np.argmin(dist_2)])
	node_ungeom = np.asarray(node_ungeom)
	
	# Iterate over elements
	elem_mean_depth = []
	elem_ungeom = []
	elem_mdepth_ungeom = []
	for i in range(len(els)):
		single_depth = []
		ungeom_points = []
		for node in els[i][1:]:
			# Compute mean depth of each element by the mean depth of the associated nodes
			ind = np.where(nod[:,0] == node)
			single_depth.append(nod[ind,3])
			
			# Find preferred vertical line for an element by the vertical line that is most often assigned to a node of the element.
			ind = np.where(node_ungeom[:,0] == node)
			ungeom_points.append(float(node_ungeom[ind,1]))
		x = collections.Counter(ungeom_points)
		elem_mdepth_ungeom.append([els[i][0], np.mean(single_depth), x.most_common()[0][0]])

	# Assign rock units to elements (ungeom depth is top of units, excluding topmost unit)
	depth = np.asarray(ungeom[:,2:])
	elsets = []
	# Create a collector for each element set.
	for _ in range(len(strata)):
		elsets.append([])
	
	# Assign each element to a unit.
	for _, elem in enumerate(elem_mdepth_ungeom):
		ind = assign_elems(depth[int(elem[2])],elem)
		elsets[ind].append(elem[0])
		
	# Write element sets to file a new set file.
	fname = 'elements.set'
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
	
#############################################################################################################
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

#############################################################################################################
def elemarray(fid):
	#Function to read the elements from an Abaqus input file.
	elems = [[]]
	num = 0
	line = fid.readline()
	while True:
		# If a new command line starts break
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
#############################################################################################################
def assign_elems(depth,elem):
	# Assign an element to a unit. Returns the number of the unit. 0 relates to the topmost unit.
	i = 0
	while (elem[1] < depth[i]) or (depth[i] == 9999):
		i += 1
		if i == len(depth):
			break
	return i

#############################################################################################################
if __name__ == '__main__':
	main()

#############################################################################################################