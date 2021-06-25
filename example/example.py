import numpy as np
import scipy as sp
from scipy import special
import matplotlib.pyplot as plt

import latte_lammps_functions as llf


def PorezagSKF(r):
    """
    Computes Hamiltonian and matrix overlap elements for building corresponding .skf file.
    Parameterization taken from  Porezag et. al.'s "Construction of tight-binding-like potentials
    on the basis of density functional theory: application to carbon".
    ---Inputs---
    r: scalar distance between atoms
    ---Outputs---
    elementDict: dictionary containing elements of Hamiltonian and overlap matrix by name
    """
    #initialize matrix elements
    H_sssigma=0
    H_spsigma=0
    H_ppsigma=0
    H_pppi=0
    S_sssigma=0
    S_spsigma=0
    S_ppsigma=0
    S_pppi=0

    #spatial cutoffs of parameterization
    aa=1 #[Bohr radii]
    b=7 #[Bohr radii]

    if (r>=aa and r<=b):
        T=np.zeros(10)
        order_chebyshevVec=range(len(T))
        y=(2*r-b-aa)/(b-aa)

        #Coefficients for Chebyshev polynomial terms
        #[Hartree energy]
        HC_sssigma=np.array([-0.4663805, 0.3528951, -0.1402985, 0.0050519,
                            0.0269723, -0.0158810, 0.0036716, 0.0010301,
                            -0.0015546, 0.0008601])
        HC_spsigma=np.array([0.3395418, -0.2250358, 0.0298224, 0.0653476,
                            -0.0605786, 0.0298962, -0.0099609, 0.0020609,
                            0.0001264, -0.0003381])
        HC_ppsigma=np.array([0.2422701, -0.1315258, -0.0372696, 0.0942352,
                            -0.0673216, 0.0316900, -0.0117293, 0.0033519,
                            -0.0004838, -0.0000906])
        HC_pppi=   np.array([-0.3793837, 0.3204470, -0.1956799, 0.0883986,
                            -0.0300733, 0.0074465, -0.0008563, -0.0004453,
                            0.0003842, -0.0001855])
        SC_sssigma=np.array([0.4728644, -0.3661623, 0.1594782, -0.0204934,
                            -0.0170732, 0.0096695, -0.0007135, -0.0013826,
                            0.0007849, -0.0002005])
        SC_spsigma=np.array([-0.3662838, 0.2490285, -0.0431248, -0.0584391,
                            0.0492775, -0.0150447, -0.0010758, 0.0027734,
                            -0.0011214, 0.0002303])
        """
            When compared to "Construction of tight binding like potentials ...
            Applications to carbon" paper by Porezag, the Sppsigma Spppi tables
            HAVE BEEN SWAPPED. This is because that paper INCORRECTLY LABELED
            (swapped) those elements in the table and the corresponding plot.
            For proof of this look at the "Transferable density functional
            tight binding for carbon ..." by Cawkwell.
        """
        SC_ppsigma=np.array([-0.1359608, 0.0226235, 0.1406440, -0.1573794,
                            0.0753818, -0.0108677, -0.0075444, 0.0051533,
                            -0.0013747, 0.0000751])
        SC_pppi=   np.array([0.3715732, -0.3070867, 0.1707304, -0.0581555,
                            0.0061645, 0.0051460, -0.0032776, 0.0009119,
                            -0.0001265, -0.000227])

        #compute Chebyshev polynomial part of f(r)
        H_sssigma+=np.polynomial.chebyshev.chebval(y,HC_sssigma)
        H_spsigma+=np.polynomial.chebyshev.chebval(y,HC_spsigma)
        H_ppsigma+=np.polynomial.chebyshev.chebval(y,HC_ppsigma)
        H_pppi+=np.polynomial.chebyshev.chebval(y,HC_pppi)
        S_sssigma+=np.polynomial.chebyshev.chebval(y,SC_sssigma)
        S_spsigma+=np.polynomial.chebyshev.chebval(y,SC_spsigma)
        S_ppsigma+=np.polynomial.chebyshev.chebval(y,SC_ppsigma)
        S_pppi+=np.polynomial.chebyshev.chebval(y,SC_pppi)

        #add final term of f(r)
        H_sssigma-=HC_sssigma[0]/2
        H_spsigma-=HC_spsigma[0]/2
        H_ppsigma-=HC_ppsigma[0]/2
        H_pppi-=HC_pppi[0]/2
        S_sssigma-=SC_sssigma[0]/2
        S_spsigma-=SC_spsigma[0]/2
        S_ppsigma-=SC_ppsigma[0]/2
        S_pppi-=SC_pppi[0]/2

    elementDict={
        #0:sigma, 1:pi, 2:delta
        #Hamiltonian elements
        "Hss0":H_sssigma,
        "Hsp0":H_spsigma,
        "Hsd0":0,
        "Hpp0":H_ppsigma,
        "Hpp1":H_pppi,
        "Hpd0":0,
        "Hpd1":0,
        "Hdd0":0,
        "Hdd1":0,
        "Hdd2":0,
        #overlap matrix elements
        "Sss0":S_sssigma,
        "Ssp0":S_spsigma,
        "Ssd0":0,
        "Spp0":S_ppsigma,
        "Spp1":S_pppi,
        "Spd0":0,
        "Spd1":0,
        "Sdd0":0,
        "Sdd1":0,
        "Sdd2":0
        }
    return elementDict


def PorezagPair(r):
    """
    Computes the pairwise repulsive energy correction to the Porezag carbon
    tight binding parameterization.
    ---Inputs---
    r: distance between two atoms, float [Bohr radii]
    ---Outputs---
    energy: pairwise energy, float [Hartrees]
    force: force on atoms, float [Hartess/Bohr radius]
    """

    energy=0 #[Hartrees]
    force=0 #[Hartress/Bohr radius]

    #spatial cutoffs of parameterization
    aa=1 #[Bohr radii]
    b=4.1 #[Bohr radii]

    if ((r >= aa) and (r <= b)):
        y=(2*r-b-aa)/(b-aa) #r mapped onto [-1,1]

        VC_rep=np.array([2.2681036, -1.9157174, 1.1677745, -0.5171036,
                        0.1529242, -0.0219294, -0.0000002, -0.0000001,
                        -0.0000005, 0.0000009])
        
        energy=np.polynomial.chebyshev.chebval(y,VC_rep)-VC_rep[0]/2 #[Hartrees]

        #dy/dr, used in E=-dV/dr=(d/dr) Sum_{i=1}^{10} c_m T_{m-1}(y)
        #=Sum_{i=1}^{10} c_m (dT_{m-1}(y)/dy)(dy/dr), dy/dr=(d/dr)((2r-b-aa)/(b-aa))
        dy_by_dr=2/(b-aa) 

        for m in range(1,11): #m=1,2,...,10
            #the [m-1] is because Python is zero based indexed, the rest of the ms are according to formula
            force+=-VC_rep[m-1]*(m-1)*sp.special.eval_chebyu(m-2,y)*dy_by_dr #[Hartrees/Bohr radius]

        """
        #finite difference in y
        deltay=0.0001
        energyFDm_y=np.polynomial.chebyshev.chebval(y-deltay,VC_rep)-VC_rep[0]/2
        energyFDp_y=np.polynomial.chebyshev.chebval(y+deltay,VC_rep)-VC_rep[0]/2
        forceFD_y=-((energyFDp_y-energyFDm_y)/(2*deltay))*dy_by_dr

        #finite difference in r
        deltar=0.0001
        yFDm_r=(2*(r-deltar)-b-aa)/(b-aa) #r-deltar mapped onto [-1,1]
        yFDp_r=(2*(r+deltar)-b-aa)/(b-aa) #r+deltar mapped onto [-1,1]
        energyFDm_r=np.polynomial.chebyshev.chebval(yFDm_r,VC_rep)-VC_rep[0]/2
        energyFDp_r=np.polynomial.chebyshev.chebval(yFDp_r,VC_rep)-VC_rep[0]/2
        forceFD_r=-(energyFDp_r-energyFDm_r)/(2*deltar)

        print('force:',force)
        print('force (via finite difference in y):',forceFD_y)
        print('force (via finite difference in r):',forceFD_r)
        print('')
        """

    return energy, force
    




if (__name__=='__main__'):

    #create dictionary for carbon-carbon interaction
    PorezagDictionary={
        "mass":12.01,
        "gridDist":0.02, #[Bohr radii]
        "nGridPoints":500,
        "type":'homonuclear',
        "elementFunction":PorezagSKF,
        "domainTB":[1,7], #domain of viability, [r_min,r_cut] [Bohr radii]
        "EVec":[0,-0.19435511,-0.50489172], #taken from DFTB+ 3ob
        "SPE":-0.04547908, #taken from DFTB+ 3ob
        "UVec":[0.3647,0.3647,0.3647], #taken from DFTB+ 3ob
        "fVec":[0,2,2],
        "cVec":[0,0,0,0,0,0,0,0],
        "pairFunction": PorezagPair,
        "domainPair": [1.0,4.1], #[Bohr radii]
        "pairKeyword": "POREZAG_C",
        "pairDescription": 'pairwise repulsive potential of Porezag C-C tight binding parameterization',
        "contributor": 'G. H. Brown'
        }


    #make .skf and LAMMPS pairwise potential table
    llf.makeSKF('skf/C-C.skf',PorezagDictionary)
    llf.makeLAMMPSPairwiseTable('pairwise/porezag_c-c.table',PorezagDictionary)

    #plot TB element curves against a version provided with DFTB+
    llf.plotSKF('skf_dftbp/C-C.skf',[1,7])
    llf.plotSKF('skf/C-C.skf',[1,7])
    
