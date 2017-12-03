# Z-Probe support
#
# Copyright (C) 2017  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math, logging
import pins, homing, delta


######################################################################
# Basic probe
######################################################################

class PrinterProbe:
    def __init__(self, printer, config):
        self.printer = printer
        self.speed = config.getfloat('speed', 5.0)
        self.z_distance = config.getfloat('max_distance', 20.0)
        self.mcu_probe = pins.setup_pin(printer, 'endstop', config.get('pin'))
        self.toolhead = printer.objects['toolhead']
        z_steppers = self.toolhead.get_kinematics().get_steppers("Z")
        for s in z_steppers:
            for mcu_endstop, name in s.get_endstops():
                for mcu_stepper in mcu_endstop.get_steppers():
                    self.mcu_probe.add_stepper(mcu_stepper)
        self.gcode = printer.objects['gcode']
        self.gcode.register_command(
            'PROBE', self.cmd_PROBE, desc=self.cmd_PROBE_help)
        self.gcode.register_command(
            'QUERY_PROBE', self.cmd_QUERY_PROBE, desc=self.cmd_QUERY_PROBE_help)
        if config.getsection('printer').get('kinematics') == 'delta':
            self.gcode.register_command(
                'DELTA_CALIBRATE', self.cmd_DELTA_CALIBRATE,
                desc=self.cmd_DELTA_CALIBRATE_help)
            self.gcode.register_command(
                'DELTA_MANUAL', self.cmd_DELTA_MANUAL,
                desc=self.cmd_DELTA_MANUAL_help)
    cmd_PROBE_help = "Probe Z-height at current XY position"
    def cmd_PROBE(self, params):
        homing_state = homing.Homing(self.toolhead)
        pos = self.toolhead.get_position()
        pos[2] = max(pos[2] - self.z_distance, 0.)
        try:
            homing_state.homing_move(
                pos, [(self.mcu_probe, "probe")], self.speed, probe_pos=True)
        except homing.EndstopError as e:
            raise self.gcode.error(str(e))
        self.gcode.reset_last_position()
    cmd_QUERY_PROBE_help = "Return the status of the z-probe"
    def cmd_QUERY_PROBE(self, params):
        print_time = self.toolhead.get_last_move_time()
        self.mcu_probe.query_endstop(print_time)
        res = self.mcu_probe.query_endstop_wait()
        self.gcode.respond_info(
            "probe: %s" % (["open", "TRIGGERED"][not not res],))
    cmd_DELTA_CALIBRATE_help = "Do probe based delta calibration"
    def cmd_DELTA_CALIBRATE(self, params):
        radius = self.gcode.get_float('RADIUS', params)
        speed = self.gcode.get_float('SPEED', params, 50.)
        self.gcode.cmd_G28({})
        calibrator = delta_probe_position(self.printer, radius, speed, 5.)
        while calibrator.busy:
            self.cmd_PROBE({})
            calibrator.cmd_NEXT({})
    cmd_DELTA_MANUAL_help = "Do manual delta calibration"
    def cmd_DELTA_MANUAL(self, params):
        radius = self.gcode.get_float('RADIUS', params)
        speed = self.gcode.get_float('SPEED', params, 50.)
        self.gcode.cmd_G28({})
        calibrator = delta_probe_position(self.printer, radius, speed, 5.)


######################################################################
# Delta probing positions
######################################################################

class delta_probe_position:
    def __init__(self, printer, radius, speed, start_height):
        self.printer = printer
        self.radius = radius
        self.speed = speed
        self.start_height = start_height
        self.toolhead = self.printer.objects['toolhead']
        self.gcode = printer.objects['gcode']
        self.gcode.register_command(
            'NEXT', self.cmd_NEXT, desc=self.cmd_NEXT_help)
        points = [(0., 0.)]
        scatter = [.95, .90, .85, .70, .75, .80]
        for i in range(6):
            r = math.radians(90. + 60. * i)
            dist = radius * scatter[i]
            points.append((math.cos(r) * dist, math.sin(r) * dist))
        self.probe_points = points
        self.results = []
        self.busy = True
        self.move_next()
    def move_next(self):
        x, y = self.probe_points[len(self.results)]
        curpos = self.toolhead.get_position()
        curpos[0] = x
        curpos[1] = y
        curpos[2] = self.start_height
        self.toolhead.move(curpos, self.speed)
        self.gcode.reset_last_position()
    cmd_NEXT_help = "Move to the next XY position for delta probe"
    def cmd_NEXT(self, params):
        # Record current position
        self.toolhead.wait_moves()
        kin = self.toolhead.get_kinematics()
        self.results.append(kin.get_stable_position())
        # Move to next position
        curpos = self.toolhead.get_position()
        curpos[2] = self.start_height
        self.toolhead.move(curpos, self.speed)
        if len(self.results) == len(self.probe_points):
            self.toolhead.get_last_move_time()
            self.finalize()
            return
        self.move_next()
    def finalize(self):
        self.busy = False
        self.gcode.reset_last_position()
        self.gcode.register_command('NEXT', None)
        kin = self.toolhead.get_kinematics()
        logging.debug("Got: %s", self.results)
        params = kin.get_calibrate_params()
        logging.debug("Params: %s", params)
        adj_params = ('endstop_a', 'endstop_b', 'endstop_c', 'radius',
                      'angle_a', 'angle_b')
        def delta_errorfunc(params):
            total_error = 0.
            for spos in self.results:
                x, y, z = delta.get_position_from_stable(spos, params)
                total_error += z**2
            return total_error
        new_params = coordinate_descent(adj_params, params, delta_errorfunc)
        logging.debug("Got2: %s", new_params)
        for spos in self.results:
            logging.debug("orig: %s new: %s",
                          delta.get_position_from_stable(spos, params),
                          delta.get_position_from_stable(spos, new_params))


######################################################################
# Coordinate descent
######################################################################

def coordinate_descent(adj_params, params, error_func):
    # Define potential changes
    params = dict(params)
    dp = {param_name: 1. for param_name in adj_params}
    # Calculate the error
    best_err = error_func(params)

    threshold = 0.00001
    rounds = 0

    while sum(dp.values()) > threshold and rounds < 10000:
        rounds += 1
        for param_name in adj_params:
            orig = params[param_name]
            params[param_name] = orig + dp[param_name]
            err = error_func(params)
            if err < best_err:
                # There was some improvement
                best_err = err
                dp[param_name] *= 1.1
                continue
            params[param_name] = orig - dp[param_name]
            err = error_func(params)
            if err < best_err:
                # There was some improvement
                best_err = err
                dp[param_name] *= 1.1
                continue
            params[param_name] = orig
            dp[param_name] *= 0.9
    logging.debug("best_err: %s  rounds: %d", best_err, rounds)
    return params


######################################################################
# Setup
######################################################################

def add_printer_objects(printer, config):
    if config.has_section('probe'):
        printer.add_object('probe', PrinterProbe(
            printer, config.getsection('probe')))
