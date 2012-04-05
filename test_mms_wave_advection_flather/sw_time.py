import sys
import configuration 
import shallow_water_model as sw_model
import finite_elements
from initial_conditions import SinusoidalInitialCondition
from dolfin import *
from dolfin_adjoint import *
from math import log

set_log_level(30)
myid = MPI.process_number()

def error(config):
  state = Function(config.function_space)
  state.interpolate(SinusoidalInitialCondition(config)())
  u_exact = "eta0*sqrt(g*depth) * cos(k*x[0]-sqrt(g*depth)*k*t)" # The analytical veclocity of the shallow water equations has been multiplied by depth to account for the change of variable (\tilde u = depth u) in this code.
  du_exact = "(- eta0*sqrt(g*depth) * sin(k*x[0]-sqrt(g*depth)*k*t) * k)"
  eta_exact = "eta0*cos(k*x[0]-sqrt(g*depth)*k*t)"
  # The source term
  source = Expression(("1.0/depth" + "*" + u_exact + " * " + du_exact, # The 1/depth factor comes from the fact that we multiplied the momentum equation by "depth" and the change of variable for velocity (\tilde u = depth u). Hence we have a multiplication factor of depth/(depth*depth) = 1/depth \ 
                             "0.0"), \
                             eta0=config.params["eta0"], g=config.params["g"], \
                             depth=config.params["depth"], t=config.params["current_time"], k=config.params["k"])

  sw_model.sw_solve(config.function_space, config, state, annotate=False, u_source = source)

  analytic_sol = Expression((u_exact, \
                             "0", \
                             eta_exact), \
                             eta0=config.params["eta0"], g=config.params["g"], \
                             depth=config.params["depth"], t=config.params["current_time"], k=config.params["k"])
  exactstate = Function(config.function_space)
  exactstate.interpolate(analytic_sol)
  e = state - exactstate
  return sqrt(assemble(dot(e,e)*dx))

def test(refinement_level):
  config = configuration.DefaultConfiguration(nx=2**8, ny=2, finite_element = finite_elements.p1dgp2) 
  config.params["finish_time"] = pi/(sqrt(config.params["g"]*config.params["depth"])*config.params["k"])
  config.params["dt"] = config.params["finish_time"]/(2*2**refinement_level)
  config.params["theta"] = 0.5
  config.params["dump_period"] = 1
  config.params["include_advection"] = True
  config.params["newton_solver"] = True 

  return error(config)

errors = []
tests = 6
for refinement_level in range(1, tests):
  errors.append(test(refinement_level))
# Compute the order of convergence 
conv = [] 
for i in range(len(errors)-1):
  conv.append(abs(log(errors[i+1]/errors[i], 2)))

info("Temporal order of convergence (expecting 2.0): %s" % str(conv))
if min(conv)<1.8:
  info_red("Temporal convergence test failed for wave_flather")
  sys.exit(1)
else:
  info_green("Test passed")
