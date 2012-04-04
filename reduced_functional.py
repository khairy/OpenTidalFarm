import numpy
import memoize
import shallow_water_model as sw_model
import initial_conditions
import helpers 
from functionals import DefaultFunctional
from dolfin import *
from turbines import *

class ReducedFunctional:

    def __init__(self, config, scaling_factor = 1.0, forward_model = sw_model.sw_solve, initial_condition = initial_conditions.SinusoidalInitialCondition):
        # Hide the configuration since changes would break the memoize algorithm. 
        self.__config__ = config
        self.scaling_factor = scaling_factor
        self.count = 0

        def j_and_dj(m, forward_only):
            ''' This function solves the forward and adjoint problem and returns the functional value and its gradient for the parameter choice m. 
                If forward_only = True then only the functional value is computed and the gradient will be None. '''
            adj_reset()
            self.count += 1

            # Change the control variables to the config parameters
            shift = 0
            if 'turbine_friction' in config.params['controls']: 
                shift = len(config.params["turbine_friction"])
                config.params["turbine_friction"] = m[:shift]
            if 'turbine_pos' in config.params['controls']: 
                mp = m[shift:]
                config.params["turbine_pos"] = numpy.reshape(mp, (-1, 2))

            debugging["record_all"] = not forward_only

            W = config.params['element_type'](config.mesh)

            # Get initial conditions
            state = Function(W, name="Current_state")
            state.interpolate(initial_condition(config)())

            # Set the control values
            U = W.split()[0].sub(0) # Extract the first component of the velocity function space 
            U = U.collapse() # Recompute the DOF map
            tf = Function(U, name = "friction") 
            tfd = Function(U, name = "friction_derivative") 

            # Set up the turbine field 
            tf.interpolate(Turbines(config.params))
            helpers.save_to_file_scalar(tf, "turbines_t=." + str(self.count) + ".x")

            # Solve the shallow water system
            functional = DefaultFunctional(W, config.params)
            j, djdm = forward_model(W, config, state, time_functional=functional, turbine_field = tf)

            # And the adjoint system to compute the gradient if it was asked for
            if forward_only:
                dj = None
            else:
                J = TimeFunctional(functional.Jt(state), static_variables = [functional.turbine_cache["turbine_field"]], dt = config.params["dt"])
                djdudm = compute_gradient(J, InitialConditionParameter("friction"))

                # Let J be the functional, m the parameter and u the solution of the PDE equation F(u) = 0.
                # Then we have 
                # dJ/dm = (\partial J)/(\partial u) * (d u) / d m + \partial J / \partial m
                #               = adj_state * \partial F / \partial u + \partial J / \partial m
                # In this particular case m = turbine_friction, J = \sum_t(ft) 
                dj = [] 
                if 'turbine_friction' in config.params["controls"]:
                    # Compute the derivatives with respect to the turbine friction
                    for n in range(len(config.params["turbine_friction"])):
                        tfd.interpolate(Turbines(config.params, derivative_index_selector=n, derivative_var_selector='turbine_friction'))
                        dj.append( djdudm.vector().inner(tfd.vector()) )

                if 'turbine_pos' in config.params["controls"]:
                    # Compute the derivatives with respect to the turbine position
                    for n in range(len(config.params["turbine_pos"])):
                        for var in ('turbine_pos_x', 'turbine_pos_y'):
                            tfd.interpolate(Turbines(config.params, derivative_index_selector=n, derivative_var_selector=var))
                            dj.append( djdudm.vector().inner(tfd.vector()) )
                dj = numpy.array(dj)  
                
                # Now add the \partial J / \partial m term
                dj += djdm

            return j, dj 

        self.j_and_dj_mem = memoize.MemoizeMutable(j_and_dj)

    def j(self, m, forward_only = False):
        ''' This memoised function returns the functional value for the parameter choice m. '''
        j = self.j_and_dj_mem(m, forward_only)[0] * self.scaling_factor
        info('Evaluating j(' + m.__repr__() + ') = ' + str(j))
        return j

    def dj(self, m):
        ''' This memoised function returns the gradient of the functional for the parameter choice m. '''
        dj = self.j_and_dj_mem(m, forward_only = False)[1] * self.scaling_factor
        info('Evaluating dj(' + m.__repr__() + ') = ' + str(dj))
        return dj

    def initial_control(self):
        ''' This function returns the control variable array that derives from the initial configuration. '''
        config = self.__config__ 
        res = []
        if 'turbine_friction' in config.params["controls"]:
            res += config.params['turbine_friction'].tolist()
        if 'turbine_pos' in config.params["controls"]:
            res += numpy.reshape(config.params['turbine_pos'], -1).tolist()
        return numpy.array(res)
