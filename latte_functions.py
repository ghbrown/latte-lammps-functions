
import copy
from datetime import datetime
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt

"""
A collection of functions useful for working with the LATTE code (written by scientists at Los Alamos National Lab).
This collection of functions was written by Gabriel Brown, University of Illinois Urbana-Champaign.
"""

def getLATTEProperty(prprty,fileName):
    """
    Searches LATTE output text file and returns the specified
    property as a number.
    NOTE: does not yet work for nonscalar values like tensors,
        do to this one would need to have explicity checks for
        the names associated with tensor inputs
    ---Inputs---
    prprty: name of desired property (must be exact), string
    fileName: name of file in which to search
    ---Outputs---
    propertyValue: value(s) of property, data type depends on
        property (could be a scalar, tensor, etc.)
    """
    fileObject=open(fileName,'r')
    propertyNameLength=len(prprty)
    lines=fileObject.readlines()
    fileObject.close()
    for line in lines:
        if (line[0:propertyNameLength]==prprty):
            propertyString=line.split()[-1] #get last element in split (the value)
            return float(propertyString)
    return 'Specified property not found.'


def getNumberOfAtoms(simulationDictionary):
    """
    Determines the number of atoms in a simulation specified by simulationDictionary.
    """
    groups=simulationDictionary['groupDictionaries']
    numberOfAtoms=0
    for group in groups:
        numberOfAtoms+=group["qArray"].shape[0]
    return numberOfAtoms
        

def dat2GroupDict(fileName):
    #WILL NEED SOME FIXING TO ACCOMODATE CHANGE TO SIMULATION DICTIONARIES
    """
    Takes arbitrary LATTE .dat file, creates array of atomic coordinates
    for every atom type present in file and stores a list of unique atom types.
    Also stores periodicity vectors of simulation domain.
    ---Inputs---
    fileName: file name (or relative path to file), string
    ---Outputs---
    qDictionary: dictionary containing the list of coordinate arrays (one for
        each atom type), a list of periodicity vectors, and a (string) list of
        the unique atom types in the same order, dictionary
    """
    fileObject=open(fileName,'r')
    content=fileObject.readlines()
    fileObject.close()
    content=[x.strip() for x in content]
    N_atoms=int(content[0])
    existingAtoms=[] #allocate list for atom types which have already been found
    qsList=[] #allocate list to contain coordinate lists for corresponding atoms
    boxPeriodicityVectors=[0]*3 #allocate list to store periodicity vectors of box size
    for irow,row in enumerate(content[1:4]): #extract box periodicity vectors
        rowList=row.split()
        curPeriodicityVector=np.array([float(elem) for elem in rowList])
        boxPeriodicityVectors[irow]=curPeriodicityVector
    for irow,row in enumerate(content[4:4+N_atoms]):
        rowList=row.split()
        curAtomType=rowList[0] #get atom type of current row
        curCoordinatesFloat=[float(elem) for elem in rowList[1:4]] #convert coordinate string list into list of floats
        if (curAtomType in existingAtoms): #if current atom type exists
            atomTypeIndex=existingAtoms.index(curAtomType) #find index of coordinate list
            qsList[atomTypeIndex].append(curCoordinatesFloat) #append current coordinates to this existing list
        else: #if current atom type does not exist yet
            existingAtoms.append(curAtomType) #add current atom type to existing atoms types
            qsList.append([curCoordinatesFloat]) #add first line in a new coordinate list for the new atom type
                
    qArrayList=[np.array(elem) for elem in qsList] #convert list of coordinate lists to list of numpy coordinate arrays
    qDictionary= {
        "boxVectors": boxPeriodicityVectors,
        "atomTypes": existingAtoms,
        "qs": qArrayList
    }
    return qDictionary


def groupDict2Dat(fileName,groupDictionary,twoDimensional=False):
    #WILL NEED SOME FIXING TO ACCOMODATE CHANGE TO SIMULATION DICTIONARIES
    """
    Takes a dictionary defining a set of atomic coordinates and
    simulation domain and writes to LATTE's .dat format.
    ---Inputs---
    fileName: the file to which the configuration will be written (including the file extension), string
    groupDictionary: the dictionary which holds the information about the configuration, dictionary
    twoDimensional: optional input which allows users to configure systems which are traditionally two dimensionsal (only two box vectors) and set a third box vector which will take the value of this variable, float (if used)
    ---Outputs---
    NONE, the information is just written to file defined by fileName
    """

    fileObject=open(fileName,'w+')
    if twoDimensional: #take special care to set z values of two dimensional
        zHeight=twoDimensional #change to a more sensible variable name
        groupDictionary=translateCoordinates(groupDictionary,np.array([0,0,zHeight]))
        zPeriodicityVector=np.array([0,0,zHeight*2]) #make artificially large lattice vector in z direction to ensure no 2-D periodicity
        groupDictionary['boxVectors']=np.vstack((groupDictionary['boxVectors'],zPeriodicityVector))
    qList=groupDictionary['qs']
    N_atoms=getNumberOfAtoms(groupDictionary)
    N_dim=qList[0].shape[1]

    #write number of atoms
    fileObject.write('       '+str(N_atoms)+'\n')
    #loop over rows of cellSizeArray and write in cell dimensions
    for i in range(N_dim):
        dataFloat=groupDictionary['boxVectors'][i]
        dataString=[f"{element:.4f}" for element in dataFloat]
        fileObject.write('   '+'   '.join(dataString)+'\n')
    #loop over each atom type, loop over each atom in each type and write coordinates to file
    for q in qList:  
        for i in range(q.shape[0]):
            dataFloat=q[i,:]
            dataString=[f"{element:.5f}" for element in dataFloat]
            fileObject.write('C'+'    '+'   '.join(dataString)+'\n')

    print('Wrote .dat file:',fileName)
    print('Number of atoms:',N_atoms)
    fileObject.close()


"""
SIMULATION SHOULD BE A COLLECTION OF GROUPS, EACH GROUP HAS ITS OWN DATA, AND ONLY CONSISTS OF ONE ATOM TYPE WHICH IS LISTED IN GROUP DATA
rewrite code so this is satisfied
"""

def refreshMetaData(simulationDictionary):
    """
    Updates the metadata (list containing number of atomtypes, and
    list containing corresponding masses) of a given simulation dictionary.
    """
    atomTypeListFull=[]
    massListFull=[]
    for groupNumber,group in enumerate(simulationDictionary["groupDictionaries"]):
        atomTypeListFull+=group["atomTypeList"] #assumes atom types are sorted
        massListFull+=group["massList"] 

    simulationDictionary["nAtoms"]=getNumberOfAtoms(simulationDictionary)
    simulationDictionary["atomTypeList"]=atomTypeListFull
    simulationDictionary["massList"]=massListFull
    simulationDictionary["nAtomTypes"]=len(atomTypeListFull)

def simulationDictionaryToLAMMPSData(fileName,groupDictionary,twoDimensional=False):
    """
    Takes a dictionary defining a set of atomic coordinates and
    simulation domain and writes to LATTE's .dat format.
    ---Inputs---
    fileName: the file to which the configuration will be written (including the file extension), string
    simulationDictionary: the dictionary which holds the information about the configuration, dictionary
    twoDimensional: optional input which allows users to configure systems which are traditionally two dimensionsal (only two box vectors) and set a third box vector which will take the value of this variable, float (if used)
    ---Outputs---
    NONE, the information is written to file defined by fileName
    """

    fileObject=open(fileName,'w+')
    if twoDimensional: #take special care to set z values of two dimensional
        zHeight=twoDimensional
        simulationDictionary=translateCoordinates(groupDictionary,np.array([0,0,zHeight]))
        zPeriodicityVector=np.array([0,0,zHeight*2]) #make artificially large lattice vector in z direction to ensure no 2-D periodicity
        simulationDictionary["boxVectors"]=np.vstack((groupDictionary["boxVectors"],zPeriodicityVector))
    groups=simulationDictionary["groupDictionaries"]
    N_atoms=simulationDictionary["nAtoms"]
    N_atomtypes=simulationDictionary["nAtomTypes"]
    N_dim=3 #can one do better than this?

    #header and cumulative data
    fileObject.write('LAMMPS Description\n \n')
    fileObject.write(str(N_atoms)+' atoms\n \n')
    fileObject.write(str(N_atomtypes)+' atom types\n \n')
    #box size
    dimLabels=['x','y','z']
    for i in range(N_dim):
        boxVector=simulationDictionary['boxVectors'][i]
        minMax=[str(np.min(boxVector)),str(np.max(boxVector))]
        extentLabels=[dimLabels[i]+'lo',dimLabels[i]+'hi\n']
        fileObject.write(' '.join(minMax)+' '+' '.join(extentLabels))
    fileObject.write('\n')
    fileObject.write('Masses\n\n')
    for atomTypeNumber,mass in enumerate(simulationDictionary["massList"]):
        fileObject.write(str(atomTypeNumber+1)+' '+str(mass)+'\n')
    fileObject.write('\n')
    #information for each atom
    fileObject.write('Atoms\n\n')
    for igroup,group in enumerate(groups):  
        atomicData=group['qArray']
        for i in range(atomicData.shape[0]):
            dataFloatMeta=atomicData[i,0:4]
            dataFloatCoordinates=atomicData[i,4:8]
            dataString=[str(int(element)) for element in dataFloatMeta]
            dataString+=[f"{element:.5f}" for element in dataFloatCoordinates]
            fileObject.write(' '.join(dataString)+'\n')

    print('Wrote .lmp file:',fileName)
    print('Number of atoms:',N_atoms)
    fileObject.close()


def translateCoordinates(simulationDictionary,displacementVector,groupControl=None):
    """
    Given a configuration of atoms, edits the groups so that all* coordinates have been
    shift by a given vector. No other changes are performed.
    *certain group may be targeted by specifying groupControl
    ---Inputs---
    groupDictionary: a group of atoms, dictionary (one field of dictionary must be 'q')
    displacementVector: vector by which all coordinates of old group should be displaced, 1D numpy array
    ---Outputs---
    groupDictionaryTranlated: a new group with translated coordinates, dictionary
    """
    if (not groupControl):
        groupControl=[1]*len(simulationDictionary["groupDictionaries"]) #default to translating all groups

    simulationDictionaryTranslated=copy.deepcopy(simulationDictionary)
    for groupNumber,group in enumerate(simulationDictionary['groupDictionaries']):
        if groupControl[groupNumber]:
            q=group["qArray"]
            qCoordinates=q[:,4:8] #extract only coordinate part of data array
            displacementVectorTuple=tuple([displacementVector]*qCoordinates.shape[0])
            displacementArray=np.vstack(displacementVectorTuple)
            qprime=qCoordinates+displacementArray
            simulationDictionaryTranslated["groupDictionaries"][groupNumber]["qArray"][:,4:8]=qprime #overwrite with translated coordinates
    return simulationDictionaryTranslated


def returnToBox(qDictionary):
    """
    Moves atoms which are outside of the box back inside the proper region using
    the periodicity vectors.
    NOTE: This (probably) only works for a rectangular simulation domain which has all 90 degree angles.
    NOTE: This function is not recursive in that if an atom is more than one box length outside of the box, it will only be moved closer to the box by one box length rather than the necessary integer > 2
    ---Inputs---
    qDictionary: dictionary containing the list of coordinate arrays (one for
        each atom type), a list of periodicity vectors, and a (string) list of
        the unique atom types in the same order, dictionary
    ---Outputs---
    NONE, the input dictionary itself is automatically altered
    """
    tol=1e-3 #used to allow atoms very close to zero to remain there
    #this is where the orthrhombic assumption happens, only the diagonal elements of the boxVector "array" are taken
    boxSizeVector=np.zeros(3)
    for iVector,vector in enumerate(qDictionary["boxVectors"]):
        boxSizeVector[iVector]=vector[iVector]

    for iAtom,curCoordinates in enumerate(qDictionary["qs"]): #loop over coordinate arrays (one per atom type)
        for iDimension in range(curCoordinates.shape[1]):
            curCoordinatesCurDim=curCoordinates[:,iDimension] #x,y, or z coordinates for the current atom type
            tooSmallMask=curCoordinatesCurDim < 0-tol
            tooLargeMask=curCoordinatesCurDim >= boxSizeVector[iDimension]
            curCoordinates[:,iDimension]=curCoordinatesCurDim+boxSizeVector[iDimension]*(tooSmallMask*np.ones(curCoordinatesCurDim.shape)-tooLargeMask*np.ones(curCoordinatesCurDim.shape))#overwrite existing coordinates with inbound coordinates
        qDictionary["qs"][iAtom]=curCoordinates #overwrite full coordinate array with fully in bounds coordinate array
            

def computeAverageDisplacement(qDictionary1,qDictionary2):
    """
    Computes the average distance between corresponding atoms in two arrangements (which both must have the same number of atoms for every atom type).
    ---Inputs---
    qDictionary1/2: dictionaries containing the list of coordinate arrays (one for
        each atom type), a list of periodicity vectors, and a (string) list of
        the unique atom types in the same order, dictionary
    ---Outputs---
    meanDisplacement: 2 element list of the maximum and minimum atomic coordinates in any
        direction (meaning each element of list is scalar), list
    """
    coordinateList1=qDictionary1["qs"]
    coordinateList2=qDictionary2["qs"]
    numerator=0 #numerator of the average displacement
    nTotal=0 #accumulator for total number of atoms
    for atomType in range(len(coordinateList1)):
        curCoordinates1=coordinateList1[atomType]
        curCoordinates2=coordinateList2[atomType]
        nCur=curCoordinates1.shape[0] #number of atoms of current atom type
        curVectorDisplacement=curCoordinates2-curCoordinates1
        displacementVector=np.zeros(curVectorDisplacement.shape[0])
        for curDim in range(curVectorDisplacement.shape[1]):
            displacementVector+=np.power(curVectorDisplacement[:,curDim],2)
        displacementVector=np.power(displacementVector,1/2)
        atomTypeTotalDisplacement=np.sum(displacementVector)
        nTotal+=nCur
        numerator+=atomTypeTotalDisplacement
    meanDisplacement=numerator/nTotal
    return meanDisplacement
                          
    
def getCoordinateBounds(qDictionary):
    """
    Gets the extreme coordinates of the atomic assembly and saves as list for
    specifying range when plotting.
    ---Inputs---
    qDictionary: dictionary containing the list of coordinate arrays (one for
        each atom type), a list of periodicity vectors, and a (string) list of
        the unique atom types in the same order, dictionary
    ---Outputs---
    bounds: 2 element list of the maximum and minimum atomic coordinates in any
        direction (meaning each element of list is scalar), list
    """
    for i_q,q in enumerate(qDictionary["qs"]):
        qMin=np.ndarray.min(q)
        qMax=np.ndarray.max(q)
        if i_q==0:
            runningMin=qMin
            runningMax=qMax
        else:
            if qMin<runningMin:
                runningMin=qMin
            if qMax>runningMax:
                runningMax=qMax
    bounds=[runningMin,runningMax]
    return bounds

    
def makeSKF(outputFileName,parameterizationDictionary):
    """
    Writes a .skf format corresponding to the given parameterization dictionary
    ---Inputs---
    outputFileName: name of .skf file, string
    parameterizationDictionary: dictionary with all info about the parameterization
    ---Outputs---
    NONE: structured file of specified name is created
    """
    pD=parameterizationDictionary #for brevity
    fileObject=open(outputFileName,'w')
    dVec=[0]*10 #just nonsense values since ds are placeholders
    gridPointsVec=pD["gridDist"]*np.array(range(pD["nGridPoints"]))
    lineListList=[]

    #grid and atomic information
    lineListList.append([pD["gridDist"],pD["nGridPoints"]]) #line 1
    if (pD["type"]=="homonuclear"):
        lineListList.append(pD["EVec"]+[pD["SPE"]]+pD["UVec"]+pD["fVec"]) #homonuclear line 2
        lineListList.append([pD["mass"]]+pD["cVec"]+[pD["domainTB"][1]]+dVec) #homonuclear line 3
    elif (pD["type"]=="heteronuclear"):
        lineListList.append([12345]+pD["cVec"]+[pD["domainTB"][1]]+dVec) #heteronuclear line 2, mass (first entry) is placeholder so use obvious dummy value
    else:
        print("ERROR: parameterization type must be \"heteronuclear\"")
        print("       or \"homonuclear\"")

    #integral table
    for r in gridPointsVec:
        if (r < pD["domainTB"][0]): #write 1.0s for r < r_min (what LATTE expects)
            tempLine=[1.0]*20
        else:
            eD=pD["elementFunction"](r) #elementDict, for brevity
            tempLine=[eD["Hdd0"],eD["Hdd1"],eD["Hdd2"],eD["Hpd0"],eD["Hpd1"],
                    eD["Hpp0"],eD["Hpp1"],eD["Hsd0"],eD["Hsp0"],eD["Hss0"],
                    eD["Sdd0"],eD["Sdd1"],eD["Sdd2"],eD["Spd0"],eD["Spd1"],
                    eD["Spp0"],eD["Spp1"],eD["Ssd0"],eD["Ssp0"],eD["Sss0"]]
        lineListList.append(tempLine)

    #spline
    lineListList.append(['Spline'])
    lineListList.append([1, pD["domainTB"][1]]) #nInt cutoff
    lineListList.append([0, 0, -1]) #a1 a2 a3  (for exp(-a1*r+a2)+a3)
    lineListList.append([pD["domainTB"][0],pD["domainTB"][1],0,0,0,0,0,0]) #start end c0 c1 c2 c3 c4 c5
    #(for c0+c1(r-r0)+c2(r-r0)^2+c3(r-r0)^3+c4(r-r0)^4+c5(r-r0)^5

    #convert numbers to strings and write lines
    for lineList in lineListList:
        lineListString=[str(elem) for elem in lineList]
        fileObject.write(' '.join(lineListString)+'\n')
    fileObject.close()
    

def plotSKF(fileName,domain):
    """
    Plots the elements of Hamiltonian and overlap matrix against distance r
    ---Inputs---
    fileName: name of a .skf file, string
    domain: domain (r values) on which to plot elements, list [r_min, r_max]
    ---Outputs---
    NONE: makes and shows plots
    """

    with open(fileName,'r') as f:
        linesAsterisksCommas=f.readlines()

    linesAsterisks=[line.replace(',','') for line in linesAsterisksCommas] #clean lines of commas
    lines=[]*len(linesAsterisks)
    for line in linesAsterisks: #write asterisk exapanded lines to lines variable
        if '*' in line:
            lineSplit=line.split() #split line on spaces
            for i_entry,entry in enumerate(lineSplit):
                if '*' in entry: #split *-containing entry on *
                    entrySplit=entry.split('*')
                    num=float(entrySplit[1]) #number to be repeated
                    timesRep=int(float(entrySplit[0])) #times to repeat
                    expandedEntries=' '.join([str(num)]*timesRep)
                    lineSplit[i_entry]=expandedEntries
            lines.append(' '.join(lineSplit))

        else:
            lines.append(line)
                
    if '@' in lines[0]:
        gridDist=float(lines[1].split()[0]) #distance between gridpoints, on second line for extended format
        integralTableLineLength=40 #.skf is in extended format
        HIntegralLabels=['Hff0', 'Hff1', 'Hff2', 'Hff3', 'Hdf0',
                         'Hdf1', 'Hdf2', 'Hdd0', 'Hdd1', 'Hdd2',
                         'Hpf0', 'Hpf1', 'Hpd0', 'Hpd1', 'Hpp0',
                         'Hpp1', 'Hsf0', 'Hsd0', 'Hsp0', 'Hss0']
        SIntegralLabels=['Sff0', 'Sff1', 'Sff2', 'Sff3', 'Sdf0',
                         'Sdf1', 'Sdf2', 'Sdd0', 'Sdd1', 'Sdd2',
                         'Spf0', 'Spf1', 'Spd0', 'Spd1', 'Spp0',
                         'Spp1', 'Ssf0', 'Ssd0', 'Ssp0', 'Sss0']
    else:
        gridDist=float(lines[0].split()[0]) #distance between gridpoints, on first line for simple format
        integralTableLineLength=20 #.skf is in simple format
        HIntegralLabels=['Hdd0', 'Hdd1', 'Hdd2', 'Hpd0', 'Hpd1',
                         'Hpp0', 'Hpp1', 'Hsd0', 'Hsp0', 'Hss0']
        SIntegralLabels=['Sdd0', 'Sdd1', 'Sdd2', 'Spd0', 'Spd1',
                         'Spp0', 'Spp1', 'Ssd0', 'Ssp0', 'Sss0']

    linesSplit=[line.split() for line in lines]
    #find index of integral table's first line
    firstLineIndex=False
    foundFirstIntegralLine=False
    i_line=0
    while (not foundFirstIntegralLine):
        splitLine=linesSplit[i_line]
        if len(splitLine)==integralTableLineLength:
            foundFirstIntegralLine=True
            firstLineIndex=i_line
            if (integralTableLineLength==20):
                #in simple format line BEFORE integral table has 20 entries
                #correct for this
                firstLineIndex+=1 
        i_line+=1
        
    #find index of integral table's last line
    afterLineIndex=False
    for i_line,splitLine in enumerate(linesSplit):
        if ('Spline' in splitLine):
            afterLineIndex=i_line #'Spline' occurs on line after integral table

    #make plucked integral table into numpy arrays for H and S
    integralTableLines=linesSplit[firstLineIndex:afterLineIndex]
    integralTable=np.array([[float(entry) for entry in splitLine] for splitLine in integralTableLines])
    HTable=integralTable[:,0:int(integralTableLineLength/2)] #first half of columns are for H
    STable=integralTable[:,int(integralTableLineLength/2):] #second half of columns are for S

    numPoints=HTable.shape[0] #number of points at which integrals are given
    rValues=gridDist*np.arange(numPoints)

    #plot nonzero H (Hamiltonian) integrals
    for i_integral,integralValues in enumerate(np.transpose(HTable)):
        if (sum(abs(integralValues[int(numPoints/3):]))>0.0):
               plt.plot(rValues,integralValues,label=HIntegralLabels[i_integral])
    plt.xlim(domain)
    plt.legend()
    plt.show()

    #plot S (overlap) integrals
    for i_integral,integralValues in enumerate(np.transpose(STable)):
        if (sum(abs(integralValues[int(numPoints/3):]))>0.0):
               plt.plot(rValues,integralValues,label=SIntegralLabels[i_integral])
    plt.xlim(domain)
    plt.legend()
    plt.show()


def makeLAMMPSPairwiseTable(outputFileName,parameterizationDictionary):
    """
    Writes a pairwise potential as a LAMMPS pairwise potential table.
    All of parameterization dictionary should be in atomic units (Bohr radii,
    Hartrees, etc.). This function generates a table in metal units (eV, Angstroms)
    and does the conversion internally
    ---Inputs---
    outputFileName: name of .table file
    parameterizationDictionary: dictionary with all info about the parameterization
    ---Outputs---
    NONE: structured file of specified name is created
    """
    #define unit conversion constants
    ang_per_bohr=0.529177 # [Anstroms/Bohr radius]
    eV_per_hart=27.2114 # [eV/Hartree]

    pD=parameterizationDictionary #for brevity
    lineList=[] #list to which complete strings will be appended 1 per line
    r_min=pD["domainPair"][0] #[Bohr radii]
    r_max=pD["domainPair"][1] #[Bohr radii]
    rValues=np.linspace(r_min,r_max,pD["nGridPoints"]) #[Bohr radii]

    lineList.append('# DATE: ' + datetime.today().strftime('%Y-%m-%d') + ' UNITS: metal CONTRIBUTOR: ' + pD["contributor"] + '\n')
    lineList.append('# ' + pD["pairDescription"] + '\n')
    lineList.append('\n')
    lineList.append(pD["pairKeyword"] + '\n')
    lineList.append('N ' + str(pD["nGridPoints"]) + '\n')
    lineList.append('\n')

    for i_r,r in enumerate(rValues): #r [Bohr radii]
        energy,force=pD["pairFunction"](r) #energy [Hartrees], force [Hartrees/Bohr radius]
        r_ang=r*ang_per_bohr
        energy_eV=energy*eV_per_hart
        force_eV_ang=force*(eV_per_hart/ang_per_bohr)
        tempValues=[str(i_r+1),str(r_ang),str(energy_eV),str(force_eV_ang)]
        lineList.append(' '.join(tempValues)+'\n')

    with open(outputFileName,'w') as f:
        f.writelines(lineList)
