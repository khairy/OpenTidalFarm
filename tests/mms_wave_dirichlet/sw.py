import sys
from opentidalfarm import *
from opentidalfarm.initial_conditions import SinusoidalInitialCondition
from dolfin import *
from dolfin_adjoint import *
from math import log

set_log_level(ERROR)
parameters["std_out_all_processes"] = False;

def error(config, eta0, k):
  state = Function(config.function_space)
  state.interpolate(SinusoidalInitialCondition(config, eta0, k, config.params["depth"]))

  adj_reset()
  shallow_water_model.sw_solve(config, state, annotate=False)

  analytic_sol = Expression(("eta0*sqrt(g/depth)*cos(k*x[0]-sqrt(g*depth)*k*t)", \
                             "0", \
                             "eta0*cos(k*x[0]-sqrt(g*depth)*k*t)"), \
                             eta0=eta0, g=config.params["g"], \
                             depth=config.params["depth"], t=config.params["current_time"], k=k)
  exactstate = Function(config.function_space)
  exactstate.interpolate(analytic_sol)
  e = state - exactstate
  return sqrt(assemble(dot(e,e)*dx))

def test(refinment_level):
  config = configuration.DefaultConfiguration(nx=2*2**refinment_level, ny=2, finite_element = finite_elements.p1dgp2) 
  eta0 = 2.0
  k = pi/config.domain.basin_x
  config.params["finish_time"] = pi/(sqrt(config.params["g"]*config.params["depth"])*k)/10
  config.params["dt"] = config.params["finish_time"]/100
  config.params["dump_period"] = 100000
  config.params["bctype"] = "dirichlet"

  return error(config, eta0, k)

errors = []
tests = 5
for refinment_level in range(1, tests):
  errors.append(test(refinment_level))
# Compute the order of convergence 
conv = [] 
for i in range(len(errors)-1):
  conv.append(abs(log(errors[i+1]/errors[i], 2)))

info_green("Absolute error values: %s" % str(errors))
info_green("Spatial order of convergence (expecting 2.0): %s" % str(conv))
if min(conv)<1.8:
  info_red("Spatial convergence test failed for wave_dirichlet")
  sys.exit(1)
else:
  info_green("Test passed")
