###########################################################################################
# Apple PY - Automatic Portioning Preventing Lengthy manual Element assignment for PYthon #
# Version 1.3																		      #
# License: GPLv3																	      #
# Moritz O. Ziegler - mziegler@gfz-potsdam.de, Malte Ziebarth, Karsten Reiter		      #
# Manual: http://doi.org/10.2312/wsm.2020.002										      #
# Download: http://github.com/MorZieg/APPLE_PY										      #
###########################################################################################
def main():
  import numpy as np
  
  files = ['01_Quarternary.dat','02_Cretaceous.dat','03_Jurassic.dat','04_Basement.dat']
  comment = '#'
  fname = 'horizons.txt'
  
  # Load the first horizon
  horizons = [[]]
  print('Loading File %s' % files[0])
  fid = open(files[0])
  num = 0
  while True:
    line = fid.readline()
    if line == '':
      break
    elif line[0] == comment: # Ignore commented lines
      continue
    
    line = str.split(line)
    if num != 0:
      horizons.append([])
    for i in range(3):
      horizons[num].append(float(line[i]))
    num += 1  
  
  horizons = np.asarray(horizons)
    
  fid.close()

  
  # Load all the following horizons
  files = files[1:]
  for i, file in enumerate(files):
    # Add a new column to the horizons variable for each new horizon and set the depth to 9999
    print('Loading File %s' % file)
    horizons = np.append(horizons,np.zeros([len(horizons),1]),1)
    horizons[:,(i+3)] = 9999
    fid = open(file)
    gp = 0
    
    while True:
      line = fid.readline()
      if line == '':
        break
      elif line[0] == comment:
        continue
      
      line = str.split(line)
      coord = [ float(line[0]), float(line[1])]
      depth = float(line[2])
      
      # Add the horizon depth to the array.
      if (len(horizons)-1) >= gp:
        # Check whether the x and y coordinates from the array and the newly added horizon match.
        if horizons[gp,0] != coord[0] or horizons[gp,1] != coord[1]:
          # If the coordinates do not match find if there are any coordinates that match.
          if np.any((horizons[:,0]==coord[0]) & (horizons[:,1]==coord[1])):
            # Find the index in the array that matches the coordinates.
            idx = np.where((horizons[:,0]==coord[0]) & (horizons[:,1]==coord[1]))
            horizons[idx[0][0],(i+3)] = depth
          else:
            #If the coordinate gridpoint is not yet defined, create a new one at the end of the horizons file.
            horizons = np.append(horizons,[np.full(i+4, 9999)],axis=0)
            horizons[-1,0] = coord[0]
            horizons[-1,1] = coord[1]
            horizons[-1,-1] = depth
          
        else:
          # If the coordinates match - add the depth.
          horizons[gp,(i+3)] = depth      
      else:
        #If the coordinate gridpoint is not yet defined, create a new one at the end of the horizons file.
        horizons = np.append(horizons,[np.full(i+4, 9999)],axis=0)
        horizons[-1,0] = coord[0]
        horizons[-1,1] = coord[1]
        horizons[-1,-1] = depth
      
      gp += 1
  
  # Convert missing horizons (9999) to depths beginning from the deepest horizon.
  print('Creating APPLE PY syntax')
  horizons = np.fliplr(horizons)
  for i,line in enumerate(horizons[:,:-2]):
    # If the deepest unit is not the same throughout the model, an arbitrary horizon of -100000 is assigned as the top of the pinching out unit in areas where it is not present.
    nd = -100000
    for k,d in enumerate(line):
      if d != 9999:
        # If the depth of a horizon is defined, update the variable nd.
        nd = d
      horizons[i,k] = nd
  horizons = np.fliplr(horizons)
  
  # Write output file
  print('Writing horizons file')
  fid = open(fname, 'w')
  for _,line in enumerate(horizons[:,:]):
    fid.write('%f' % line[0])
    for _,d in enumerate(line[1:]):
      fid.write(', %f' % d)
    fid.write('\n')
  fid.close()
  
###########################################################################################
if __name__ == '__main__':
  main()
###########################################################################################