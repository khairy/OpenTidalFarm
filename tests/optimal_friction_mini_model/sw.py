''' Test description:
 - single turbine (with constant friction distribution) whose size exceeds the size of the domain
 - constant velocity profile with an initial x-velocity of 2.
 - control: turbine friction
 - the mini model will compute a x-velocity of 2/(f + 1) wher ef is the turbine friction.
 - the functional is \int C * f * ||u||**3 where C is a constant
 - hence we maximise C * f * ( 2/(f + 1) )**3, f > 0 which has the solution f = 0.5

 Note: The solution is known only because we use a constant turbine friction distribution. 
       However this turbine model is not differentiable at its boundary, and this is why
       the turbine size has to exceed the domain.
 '''

import sys
import configuration 
import numpy
import IPOptUtils
import finite_elements
from helpers import test_gradient_array
from mini_model import *
from reduced_functional import ReducedFunctional
from dolfin import *
from scipy.optimize import fmin_slsqp
set_log_level(PROGRESS)

def default_config():
  # We set the perturbation_direction with a constant seed, so that it is consistent in a parallel environment.
  numpy.random.seed(21) 
  config = configuration.DefaultConfiguration(nx=20, ny=10, finite_element = finite_elements.p1dgp2)
  config.params["verbose"] = 0

  # dt is used in the functional only, so we set it here to 1.0
  config.params["dt"] = 1.0
  # Turbine settings
  config.params["turbine_pos"] = [[500., 500.]]
  # The turbine friction is the control variable 
  config.params["turbine_friction"] = 12.0*numpy.random.rand(len(config.params["turbine_pos"]))
  config.params["turbine_x"] = 8000
  config.params["turbine_y"] = 8000

  return config

config = default_config()
model = ReducedFunctional(config, scaling_factor = -10**-3, forward_model = mini_model_solve)
m0 = model.initial_control()

p = numpy.random.rand(len(m0))
minconv = test_gradient_array(model.j, model.dj, m0, seed=0.001, perturbation_direction=p)
if minconv < 1.99:
  info_red("The gradient taylor remainder test failed.")
  sys.exit(1)

# If this option does not produce any ipopt outputs, delete the ipopt.opt file
g = lambda m: []
dg = lambda m: []

lb_f, ub_f = IPOptUtils.friction_constraints(config, lb = 0., ub = 100.)
bounds = [(lb_f[i], ub_f[i]) for i in range(len(lb_f))] + [(500, 500), (500, 500)] 

m = fmin_slsqp(model.j, m0, fprime = model.dj, bounds = bounds, iprint = 2)

if abs(m[0]-0.61216779034) > 10**-4: 
  info_red("The optimisation algorithm did not find the correct solution.")
  sys.exit(1) 
