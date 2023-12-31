from firedrake import *
import numpy as np
import math,sys
from time import sleep
from tqdm import tqdm
from Limiter.flux_limiter_well import *

formulation = 'Upwind'


T = 0.25
nx = int(sys.argv[1])
num_steps = ((nx)**2)/4
dt = T / num_steps # time step size
dtc = Constant(dt)
#=====================================;
#  Create mesh and identify boundary  ;
#=====================================;
mesh = UnitSquareMesh(nx,nx,diagonal='right')
#==========================;
#  Define function spaces ;
#=========================;
pSpace = FunctionSpace(mesh,"DG" , 1)
sSpace = FunctionSpace(mesh,"DG" , 1)
wSpace = MixedFunctionSpace([pSpace,sSpace])
u0 = Function(wSpace)
kSpace = FunctionSpace(mesh,"DG",0)
Vt = FunctionSpace(mesh, "HDiv Trace", 0)
w = TestFunction(Vt)
fluxes = Function(Vt)
with u0.dat.vec as solution_vec:
  DoF = solution_vec.getSize()
area_cell = Function(kSpace).interpolate(CellVolume(mesh)).vector().array()
#===================================;
#  Define trial and test functions  ;
#===================================;
(p_0,s_0) = TrialFunction(wSpace) # for linear solvers
(z,v) = TestFunction(wSpace)
#=====================;
#  Define parameters  ;
#=====================;
x, y = SpatialCoordinate(mesh)
K = Constant(1)

mu_w = Constant(1)
mu_l = Constant(1)

phi_0 = Constant(1)
rhow_0 = Constant(1)
rhol_0 = Constant(1)
g = Constant((0,0))


time = 0
x = SpatialCoordinate(mesh)

# working Old
s_an =  Function(sSpace).interpolate(0.2*(2.+2.*x[0]*x[1]+cos(time+x[0])))
p_an =  Function(pSpace).interpolate(2.+pow(x[0],2)*x[1]-pow(x[1],2)+pow(x[0],2)*sin(time+x[1])\
       -1./6. * ( 2*cos(time) -2*cos(time+1) + 11 ))

p0 = interpolate( p_an, pSpace)
s0 = interpolate( s_an, sSpace)



def lmbda_w(s):
    return  s*s*K/mu_w
def lmbda_l(s):
    return (1-s)*(1-s)*K/mu_l

# Old working
Cr = Constant(1e-10)
Cw = Constant(1e-10)
Cl = Constant(1e-10)
def phi(p):
    return phi_0*(1+Cr*p)

def rhow(p):
    return rhow_0*(1+Cw*p)

def rhol(p):
    return rhol_0*(1+Cl*p)
time_ = Constant(0)

#=================================;
#  Dirichlet boundary conditions  ;
#=================================;
bcs = []
#============================;
#   Define variational form  ;
#============================;
n = FacetNormal(mesh)
area = FacetArea(mesh)
# if triangular mesh is used
h = CellSize(mesh)
h_avg = (h('+')+h('-'))/2
# if quadrilateral mesh is used
# h_avg = Constant(1./float(nx))
# h = Constant(1./float(nx))
SIG = 1e2
sigma = Constant(SIG)
sigma_bnd = Constant(10*SIG)
#====================;
#  March over time   ;
#====================;
du = TrialFunction(wSpace)
# file_p = File("./Output/pres+FL+SL.pvd")
# file_s = File("./Output/sat+FL+SL.pvd")
# file_p_ex = File("./Output/pres_ex.pvd")
# file_s_ex = File("./Output/sat_ex.pvd")
# file_q_w = File("./Output/q_w.pvd")
# file_q_l = File("./Output/q_l.pvd")

a_s0 = s_0*v*dx
L_s0 = s_an * v * dx

a_p0 = p_0*z*dx
L_p0 = p_an * z * dx

a_init = a_p0 + a_s0
L_init = L_p0 + L_s0
params = {'ksp_type': 'preonly', 'pc_type':'lu',"pc_factor_mat_solver_type": "mumps" }
A = assemble(a_init, bcs=bcs, mat_type='aij')
b = assemble(L_init)
solve(A,u0,b,solver_parameters=params)
pSol,sSol = u0.split()
p0.assign(pSol)
s0.assign(sSol)
sAvg = Function(kSpace).interpolate(s0)

# p0.rename("Pressure","Pressure")
# file_p.write(p0,time=time)

p_ex = interpolate(p_an,pSpace)
# p_ex.rename("Pressure","Pressure")
# file_p_ex.write(p_ex,time=time)

# s0.rename("Saturation","Saturation")
# file_s.write(s0,time=time)

s_ex = interpolate(s_an,sSpace)
# s_ex.rename("Saturation","Saturation")
# file_s_ex.write(s_ex,time=time)


# non-linear problem
u = Function(wSpace)
u.assign(u0)
(p,s) = (u[0],u[1]) # for non-linear solvers


Slope_limiter = VertexBasedLimiter(sSpace)
Slope_limiter.apply(s0)


sAvg0 = sAvg
counter = 1
print('Step \t solve \t FL(no_fluxcost)\t FL(all) \t SL \t convergedIter\n ')
for nIter in tqdm(range(int(num_steps))):
    # print ('Time_Step =%d'%counter)
    sAvg0.assign(sAvg)

    #Old Compressible everything is one + C factors 1e-10 + without gravity field [working]
    q_w = Function(sSpace).interpolate(\
-(((0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))**2*(x[0]**2 - 2*x[1] + x[0]**2*cos( time_ + x[1] ))**2)/10000000000) -\
((0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))**2*(2*x[0]*x[1] + 2*x[0]*sin( time_ + x[1] ))**2)/10000000000 -
0.8*x[0]*(0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))*(x[0]**2 - 2*x[1] + x[0]**2*cos( time_ + x[1] ))*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 +\
(1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) + \
((0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))*(x[0]**2*cos( time_ + x[1] ) + sin( time_ )/3 -\
(1/3)*sin( 1 + time_ ))*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/ \
10000000000))/5000000000 - (0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))**2*(2*x[1] + 2*sin( time_ + x[1] ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) -\
2*(0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))*(0.4*x[1] - 0.2*sin( time_ + x[0] ))*\
(2*x[0]*x[1] + 2*x[0]*sin( time_ + x[1] ))*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) - \
(0.4 + 0.4*x[0]*x[1] + 0.2*cos( time_ + x[0] ))**2*(-2 - x[0]**2*sin( time_ + x[1] ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) - \
0.2*sin( time_ + x[0] )*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000)**2\
    )

    q_l = Function(pSpace).interpolate(\
-(((0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))**2*(x[0]**2 - 2*x[1] + x[0]**2*cos( time_ + x[1] ))**2)/10000000000) - \
((0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))**2*(2*x[0]*x[1] + 2*x[0]*sin( time_ + x[1] ))**2)/10000000000 + \
0.8*x[0]*(0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))*(x[0]**2 - 2*x[1] + x[0]**2*cos( time_ + x[1] ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) + \
((0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))*(x[0]**2*cos( time_ + x[1] ) + sin( time_ )/3 - (1/3)*sin( 1 + time_ ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/\
10000000000))/5000000000 - (0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))**2*(2*x[1] + 2*sin( time_ + x[1] ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) -\
2*(0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))*(-0.4*x[1] + 0.2*sin( time_ + x[0] ))*\
(2*x[0]*x[1] + 2*x[0]*sin( time_ + x[1] ))*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) - \
(0.6 - 0.4*x[0]*x[1] - 0.2*cos( time_ + x[0] ))**2*(-2 - x[0]**2*sin( time_ + x[1] ))*\
(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000) + \
0.2*sin( time_ + x[0] )*(1 + (1/6 + x[0]**2*x[1] - x[1]**2 - cos( time_ )/3 + (1/3)*cos( 1 + time_ ) + x[0]**2*sin( time_ + x[1] ))/10000000000)**2\
    )

    # q_w.rename("q_w","q_w")
    # file_q_w.write(q_w)
    # q_l.rename("q_l","q_l")
    # file_q_l.write(q_l)
    #update time
    time += dt
    counter += 1
    time_.assign(time)

    # Old Compressible
    s_an =  Function(sSpace).interpolate(0.2*(2.+2.*x[0]*x[1]+cos(time_+x[0]))) 
    p_an =  Function(pSpace).interpolate(2.+pow(x[0],2)*x[1]-pow(x[1],2)+pow(x[0],2)*sin(time_+x[1])\
           -1./6. * ( 2*cos(time_) -2*cos(time_+1) + 11 ))

    p_ex = interpolate(p_an,pSpace)
    # p_ex.rename("Pressure","Pressure")
    s_ex = interpolate(s_an,sSpace)
    # s_ex.rename("Saturation","Saturation")
    # file_p_ex.write(p_ex,time=time)
    # file_s_ex.write(s_ex,time=time)

    solMin = s_ex.vector().array().min()
    solMax = s_ex.vector().array().max()


    # Mehtod 2: Upwinding
    a_p2 = (1./dt)*(phi(p) * rhol(p) * (1-s) * z) * dx +\
        rhol(p) * lmbda_l(s) * inner((grad(p)-rhol(p)*g) ,grad(z)) * dx -\
        conditional( gt(inner(avg(rhol(p0) *(grad(p0)-rhol(p0)*g)),n('+')),0) ,\
            inner(lmbda_l(s)('+') * avg(rhol(p) *(grad(p)-rhol(p)*g)) , jump(z,n)),\
            inner(lmbda_l(s)('-') * avg(rhol(p) *(grad(p)-rhol(p)*g)) , jump(z,n))\
                           ) * dS -\
        inner(rhol(p_an)*lmbda_l(s) * (grad(p)-rhol(p)*g), n) * z * ds +\
        sigma/h_avg * jump(p) * jump(z)  * dS +\
        sigma_bnd/h * p * z * ds

    L_p2 = (1./dt)*(phi(p0) * rhol(p0) * (1-s0) * z) * dx +\
        rhol(p0) * q_l * z * dx +\
        sigma_bnd/h * p_an * z * ds

    a_s = (1./dt) * phi(p)* rhow(p) * s * v * dx  + \
        rhow(p) * lmbda_w(s) * inner((grad(p)-rhow(p)*g)  , grad(v)) * dx -\
        conditional( gt(inner(avg(rhow(p0) *(grad(p0)-rhow(p0)*g)),n('+')),0) ,\
            inner(lmbda_w(s)('+') * avg(rhow(p) *(grad(p)-rhow(p)*g)) , jump(v,n)),\
            inner(lmbda_w(s)('-') * avg(rhow(p) *(grad(p)-rhow(p)*g)) , jump(v,n))\
                           ) * dS -\
        lmbda_w(s_an)*rhow(p) * inner((grad(p)-rhow(p)*g),n) * v * ds +\
        sigma/h_avg * jump(s) * jump(v)  * dS +\
        sigma_bnd/h * s * v * ds

    L_s = (1./dt) * phi(p0)* rhow(p0) * s0 * v * dx +\
        rhow(p0) * q_w * v * dx + \
        sigma_bnd/h * s_an * v * ds

    F =  a_p2 - L_p2 + a_s - L_s


    J = derivative(F, u, du)
    problem = NonlinearVariationalProblem(F,u,bcs,J)
    solver = NonlinearVariationalSolver(problem,solver_parameters=
                                            {
                                                #OUTER NEWTON SOLVER
                                            'snes_type': 'newtonls',
                                            'snes_rtol': 1e-6,
                                            'snes_max_it': 200,
                                            # "snes_linesearch_type": "basic",
                                            # 'snes_monitor': None,
                                            ## 'snes_view': None,
                                            # 'snes_converged_reason': None,
                                                # INNER LINEAR SOLVER
                                            'ksp_rtol': 1e-6,
                                            'ksp_max_it': 100,
                                            # Direct solver
                                            'ksp_type':'preonly',
                                            'mat_type': 'aij',
                                            'pc_type': 'lu',
                                            "pc_factor_mat_solver_type": "mumps",
                                            # Iterative solvers
                                            # 'pc_type': 'hypre',
                                            # 'hypre_type': 'boomeramg',
                                            # 'ksp_type' : 'fgmres',
                                            # 'ksp_gmres_restart': '100',
                                            # 'ksp_initial_guess_non_zero': True,
                                            # 'ksp_converged_reason': None,
                                            # 'ksp_monitor_true_residual': None,
                                            ## 'ksp_view':None,
                                            # 'ksp_monitor':None
                                            })
    solver.solve()

    pSol,sSol = u.split()

    sAvg = Function(kSpace).interpolate(sSol)
    wells_avg=Function(kSpace).interpolate(rhow(p0)*q_w)
    rPAvg_0 = Function(kSpace).interpolate(rhow(p0)*phi(p0))
    rPAvg = Function(kSpace).interpolate(rhow(pSol)*phi(pSol))
    # ---------------------;
    # flux-limiter applied ;
    # ---------------------;

    F_flux = fluxes('+')*w('+')*dS + fluxes*w*ds - (\
        area * -1. *conditional( gt(inner(avg(rhow(p0) *(grad(p0)-rhow(p0)*g)),n('+')),0.) ,\
        lmbda_w(sSol)('+') * inner(avg(rhow(pSol) *(grad(pSol)-rhow(pSol)*g)) ,n('+')) * w('+'),\
        lmbda_w(sSol)('-') * inner(avg(rhow(pSol) *(grad(pSol)-rhow(pSol)*g)) ,n('+')) * w('+')\
                       )* dS -\
    area * lmbda_w(s_an)*rhow(pSol) * inner((grad(pSol)-rhow(pSol)*g),n) * w * ds +\
    area * sigma/h_avg * jump(sSol) * w('+')  * dS +\
    area * sigma_bnd/h * sSol * w * ds -\
    area * sigma_bnd/h * s_an * w * ds
    )

    solve(F_flux == 0, fluxes)

    # Applied flux limiter
    sSol,convergedIter = flux_limiter(mesh,s0,sSol,rPAvg_0,rPAvg,wells_avg,fluxes,solMax,solMin,dt).apply()


    # Slope-limiter applied
    Slope_limiter.apply(sSol)

    p0.assign(pSol)
    s0.assign(sSol)

    # p0.rename("Pressure","Pressure")
    # s0.rename("Saturation","Saturation")
    # file_p.write(p0)
    # file_s.write(s0)
    sleep(0.1)

L2_error_s = errornorm(s_ex,s0,'L2')
L2_error_p = errornorm(p_ex,p0,'L2')
print("L2_error_of_s %e" % L2_error_s)
print("L2_error_of_p %e" % L2_error_p)
H1_error_s = errornorm(s_ex,s0,'H1')#this is \int (v, v) + (\nabla v, \nabla v) \mathrm{d}x`
H1_error_p = errornorm(p_ex,p0,'H1')
print("H1_error_of_s %e" % H1_error_s)
print("H1_error_of_p %e" % H1_error_p)

print('dofs', DoF)
